"""Der Ablauf: suchen, vorfiltern, bewerten, Anschreiben entwerfen, versenden."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import anthropic

from . import anschreiben as anschreiben_modul
from . import brief_pdf, matching
from .db import Ablage
from .klient import klient
from .konfig import Profil, Zugang
from .modelle import BEWERTET, ENTWURF, NEU, VERWORFEN, Stelle
from .quellen import JobsCh, bauen, entdoppeln
from .versand import VersandFehler, versenden

STANDARD_QUELLEN = ["jobs.ch", "manuell"]


def zeile_zu_stelle(zeile: sqlite3.Row) -> Stelle:
    """Baut aus einem Datenbankeintrag wieder ein Stellenobjekt."""
    return Stelle(
        titel=zeile["titel"] or "",
        firma=zeile["firma"] or "",
        ort=zeile["ort"] or "",
        url=zeile["url"] or "",
        quelle=zeile["quelle"] or "",
        extern_id=zeile["extern_id"] or "",
        pensum=zeile["pensum"] or "",
        beschreibung=zeile["beschreibung"] or "",
        kontakt_email=zeile["kontakt_email"] or "",
        kontakt_name=zeile["kontakt_name"] or "",
        veroeffentlicht=zeile["veroeffentlicht"] or "",
    )


# -- Schritt 1: suchen ------------------------------------------------------

def suchen(
    profil: Profil,
    ablage: Ablage,
    quellen_namen: list[str] | None = None,
    rohdaten_ablegen: bool = False,
) -> dict[str, int]:
    """Fragt die Quellen ab und legt neue, grundsaetzlich passende Stellen ab."""
    quellen = bauen(quellen_namen or STANDARD_QUELLEN, profil, rohdaten_ablegen=rohdaten_ablegen)

    roh: list[Stelle] = []
    for quelle in quellen:
        print(f"Suche auf {quelle.name} ...")
        roh.extend(quelle.suchen())

    stellen = entdoppeln(roh)
    zahlen = {"gefunden": len(stellen), "bekannt": 0, "aussortiert": 0, "neu": 0}

    detail_quelle = next((q for q in quellen if isinstance(q, JobsCh)), None)

    for stelle in stellen:
        if ablage.kennt(stelle.fingerabdruck):
            zahlen["bekannt"] += 1
            continue

        durch, grund = matching.grobfilter(stelle, profil)
        if not durch:
            zahlen["aussortiert"] += 1
            print(f"  uebersprungen: {stelle.kurz()} ({grund})")
            continue

        # Erst jetzt die Detailseite laden - das spart Abfragen auf der Plattform.
        if detail_quelle and stelle.quelle == detail_quelle.name:
            stelle = detail_quelle.details_nachladen(stelle)
            detail_quelle.warten()

        stelle_id, ist_neu = ablage.aufnehmen(stelle)
        if not ist_neu:
            zahlen["bekannt"] += 1
            continue

        durch, grund = matching.vorfilter(stelle, profil)
        if not durch:
            ablage.aktualisieren(stelle_id, status=VERWORFEN, begruendung=grund)
            ablage.ereignis(stelle_id, "verworfen", grund)
            zahlen["aussortiert"] += 1
        else:
            zahlen["neu"] += 1

    return zahlen


# -- Schritt 2: bewerten ----------------------------------------------------

def bewerten(
    profil: Profil,
    ablage: Ablage,
    client: anthropic.Anthropic | None = None,
    grenze: int | None = None,
) -> dict[str, int]:
    """Laesst das Modell alle neuen Stellen beurteilen."""
    client = client or klient()
    grenze = grenze or int(profil.bewertung.get("max_bewertungen_pro_lauf", 40))
    offene = ablage.nach_status(NEU)[:grenze]
    zahlen = {"bewertet": 0, "passend": 0, "verworfen": 0, "fehler": 0}

    for zeile in offene:
        stelle = zeile_zu_stelle(zeile)
        try:
            urteil = matching.bewerten(client, stelle, profil)
        except Exception as fehler:
            print(f"  Bewertung fehlgeschlagen ({stelle.kurz()}): {fehler}")
            zahlen["fehler"] += 1
            continue

        passt = urteil.passt(profil.schwelle)
        ablage.bewertung_speichern(zeile["id"], urteil, BEWERTET if passt else VERWORFEN)
        zahlen["bewertet"] += 1
        zahlen["passend" if passt else "verworfen"] += 1
        marke = "+" if passt else "-"
        print(f"  {marke} {urteil.punktzahl:3d}  {stelle.kurz()}")

    return zahlen


# -- Schritt 3: Anschreiben entwerfen --------------------------------------

def entwerfen(
    profil: Profil,
    ablage: Ablage,
    client: anthropic.Anthropic | None = None,
    grenze: int | None = None,
    stelle_id: int | None = None,
) -> dict[str, int]:
    """Verfasst fuer bewertete Stellen ein Anschreiben und legt es als PDF ab."""
    client = client or klient()
    if stelle_id is not None:
        zeile = ablage.holen(stelle_id)
        zeilen = [zeile] if zeile else []
    else:
        zeilen = ablage.nach_status(BEWERTET)
        if grenze:
            zeilen = zeilen[:grenze]

    zahlen = {"entworfen": 0, "fehler": 0}
    for zeile in zeilen:
        stelle = zeile_zu_stelle(zeile)
        try:
            brief = anschreiben_modul.verfassen(client, stelle, profil)
            pdf = brief_pdf.erzeugen(brief, stelle, profil)
            ablage.entwurf_speichern(
                zeile["id"],
                betreff=brief["betreff"],
                text=anschreiben_modul.als_text(brief, profil),
                pdf_pfad=str(pdf),
                empfaenger=stelle.kontakt_email or "",
            )
            zahlen["entworfen"] += 1
            print(f"  Entwurf: {stelle.kurz()} -> {pdf.name}")
        except Exception as fehler:
            print(f"  Entwurf fehlgeschlagen ({stelle.kurz()}): {fehler}")
            ablage.ereignis(zeile["id"], "fehler", f"Entwurf: {fehler}")
            zahlen["fehler"] += 1

    return zahlen


# -- Schritt 4: senden (nur nach Ihrer Freigabe) ---------------------------

def freigeben(
    profil: Profil,
    zugang: Zugang,
    ablage: Ablage,
    stelle_id: int,
) -> tuple[bool, str]:
    """Verschickt eine einzelne, von Ihnen freigegebene Bewerbung."""
    zeile = ablage.holen(stelle_id)
    if zeile is None:
        return False, f"Stelle {stelle_id} nicht gefunden."
    if zeile["status"] == "versendet":
        return False, "Diese Bewerbung wurde bereits versendet."

    tageslimit = int(profil.grenzen.get("max_bewerbungen_pro_tag", 5))
    if ablage.heute_versendet() >= tageslimit:
        return False, f"Tageslimit von {tageslimit} Bewerbungen erreicht."

    empfaenger = (zeile["empfaenger"] or zeile["kontakt_email"] or "").strip()
    if not empfaenger:
        return False, (
            "Fuer diese Stelle ist keine E-Mail-Adresse hinterlegt. "
            "Tragen Sie eine ein oder bewerben Sie sich ueber das Portal."
        )

    anhaenge = _anhaenge(profil, zeile)
    try:
        echt, meldung = versenden(
            profil, zugang, empfaenger,
            betreff=zeile["betreff"] or f"Bewerbung als {zeile['titel']}",
            brieftext=zeile["anschreiben"] or "",
            anhaenge=anhaenge,
        )
    except VersandFehler as fehler:
        ablage.fehler_vermerken(stelle_id, str(fehler))
        return False, str(fehler)

    ablage.versand_vermerken(stelle_id, empfaenger, trockenlauf=not echt)
    return True, meldung


def _anhaenge(profil: Profil, zeile: sqlite3.Row) -> list[Path]:
    anhaenge = list(profil.anhang_pfade())
    if zeile["anschreiben_pdf"]:
        anhaenge.insert(0, Path(zeile["anschreiben_pdf"]))
    return anhaenge


# -- alles zusammen ---------------------------------------------------------

def lauf(
    profil: Profil,
    ablage: Ablage,
    quellen_namen: list[str] | None = None,
    client: anthropic.Anthropic | None = None,
) -> dict[str, Any]:
    """Ein vollstaendiger Durchgang bis zum fertigen Entwurf - ohne Versand."""
    client = client or klient()
    ergebnis: dict[str, Any] = {}
    ergebnis["suche"] = suchen(profil, ablage, quellen_namen)
    print()
    ergebnis["bewertung"] = bewerten(profil, ablage, client)
    print()
    ergebnis["entwuerfe"] = entwerfen(profil, ablage, client)
    ergebnis["wartet_auf_freigabe"] = len(ablage.nach_status(ENTWURF))
    return ergebnis

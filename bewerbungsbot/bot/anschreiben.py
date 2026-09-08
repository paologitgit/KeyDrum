"""Erzeugt das Anschreiben zu einer konkreten Stelle."""

from __future__ import annotations

import re
from typing import Any

import anthropic

from .klient import antwort_json
from .konfig import Profil
from .modelle import Stelle

BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "betreff": {
            "type": "string",
            "description": "Betreffzeile, ohne das Wort 'Betreff', maximal 80 Zeichen.",
        },
        "anrede": {
            "type": "string",
            "description": "Anrede mit Komma am Ende, z. B. 'Sehr geehrte Frau Meier,'.",
        },
        "absaetze": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Drei bis vier Absaetze Fliesstext, ohne Anrede und ohne Gruss.",
        },
    },
    "required": ["betreff", "anrede", "absaetze"],
    "additionalProperties": False,
}

SYSTEM = """Sie verfassen Bewerbungsanschreiben fuer den Schweizer Arbeitsmarkt.

Anforderungen an den Text:
- Schweizer Hochdeutsch, kein Eszett.
- Sachlicher, erwachsener Ton. Die schreibende Person tritt als Fachperson auf,
  nicht als Bittstellerin.
- Kein Werbedeutsch, keine Superlative, keine Floskeln wie "mit grossem Interesse
  habe ich Ihre Stellenausschreibung gelesen" oder "ich bin teamfaehig und
  belastbar".
- Jede Aussage stuetzt sich auf eine Angabe aus dem Profil. Erfinden Sie keine
  Arbeitgeber, Abschluesse, Zahlen oder Projekte.
- Nehmen Sie auf zwei bis drei konkrete Anforderungen des Inserats Bezug und
  belegen Sie diese mit einem Beispiel aus dem Profil.
- Drei bis vier Absaetze, insgesamt 200 bis 300 Woerter.
- Der letzte Absatz benennt knapp das Interesse an einem Gespraech, ohne zu draengen.

Antworten Sie ausschliesslich im vorgegebenen JSON-Format."""


def verfassen(
    client: anthropic.Anthropic,
    stelle: Stelle,
    profil: Profil,
) -> dict[str, Any]:
    """Liefert {'betreff', 'anrede', 'absaetze'} fuer eine Stelle."""
    modell = profil.anschreiben.get("modell", "claude-opus-5")
    daten = antwort_json(
        client,
        modell=modell,
        system=SYSTEM,
        nachricht=_nachricht(stelle, profil),
        schema=BRIEF_SCHEMA,
        max_tokens=16000,
    )
    absaetze = [str(a).strip() for a in daten.get("absaetze", []) if str(a).strip()]
    if not absaetze:
        raise ValueError("Das Modell hat keinen Brieftext geliefert.")
    return {
        "betreff": _betreff(daten.get("betreff", ""), stelle, profil),
        "anrede": str(daten.get("anrede") or profil.anschreiben.get(
            "anrede_unbekannt", "Sehr geehrte Damen und Herren")).strip(),
        "absaetze": absaetze,
    }


def als_text(brief: dict[str, Any], profil: Profil) -> str:
    """Der Brief als Fliesstext - fuer die Anzeige im Dashboard und den Mailtext."""
    gruss = profil.anschreiben.get("gruss", "Freundliche Gruesse")
    teile = [brief["anrede"], "", "\n\n".join(brief["absaetze"]), "", gruss, profil.voller_name]
    return "\n".join(teile).strip()


def aus_text(text: str, profil: Profil) -> dict[str, Any]:
    """Zerlegt einen von Hand bearbeiteten Brief wieder in seine Bestandteile.

    Noetig, weil Sie den Text im Dashboard aendern koennen und das PDF danach
    dieselbe Struktur braucht.
    """
    gruss = profil.anschreiben.get("gruss", "Freundliche Gruesse")
    rumpf = text.strip()
    for schluss in (gruss, "Freundliche Gruesse", "Freundliche Grüsse", "Mit freundlichen"):
        stelle_im_text = rumpf.find(schluss)
        if stelle_im_text > 0:
            rumpf = rumpf[:stelle_im_text].strip()
            break

    bloecke = [b.strip() for b in re.split(r"\n\s*\n", rumpf) if b.strip()]
    if not bloecke:
        return {"anrede": profil.anschreiben.get("anrede_unbekannt", "Sehr geehrte Damen und Herren"),
                "absaetze": [text.strip()]}
    anrede, *absaetze = bloecke
    return {"anrede": anrede, "absaetze": absaetze or [""]}


def _betreff(vorschlag: str, stelle: Stelle, profil: Profil) -> str:
    vorschlag = (vorschlag or "").strip()
    if vorschlag:
        return vorschlag[:100]
    vorlage = profil.versand.get("betreff_vorlage", "Bewerbung als {titel}")
    return vorlage.format(titel=stelle.titel, firma=stelle.firma)[:100]


def _nachricht(stelle: Stelle, profil: Profil) -> str:
    konfig = profil.anschreiben
    tabu = konfig.get("tabu", [])
    stilbeispiel = (konfig.get("stilbeispiel") or "").strip()
    beschreibung = re.sub(r"\n{3,}", "\n\n", stelle.beschreibung or "")[:14000]

    teile = [
        "INSERAT",
        f"Titel: {stelle.titel}",
        f"Firma: {stelle.firma}",
        f"Ort: {stelle.ort or 'nicht angegeben'}",
        f"Pensum: {stelle.pensum or 'nicht angegeben'}",
        "",
        beschreibung,
        "",
        "PROFIL DER BEWERBERIN ODER DES BEWERBERS",
        f"Name: {profil.voller_name}",
        (konfig.get("profil_text") or "").strip(),
    ]
    if stilbeispiel:
        teile += [
            "",
            "STILBEISPIEL (nur der Ton ist gemeint, nicht der Inhalt)",
            stilbeispiel,
        ]
    if tabu:
        teile += ["", "DIESE THEMEN NICHT ERWAEHNEN: " + ", ".join(tabu)]
    if stelle.kontakt_name:
        teile += ["", f"Ansprechperson im Inserat: {stelle.kontakt_name}"]
    else:
        teile += [
            "",
            "Im Inserat ist keine Ansprechperson genannt. Verwenden Sie die Anrede "
            f"'{konfig.get('anrede_unbekannt', 'Sehr geehrte Damen und Herren')},'.",
        ]
    return "\n".join(teile)

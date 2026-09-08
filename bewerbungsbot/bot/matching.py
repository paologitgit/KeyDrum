"""Zweistufige Auswahl: erst ein kostenloser Vorfilter, dann das Urteil des Modells."""

from __future__ import annotations

import re
from typing import Any

import anthropic

from .klient import antwort_json
from .konfig import Profil
from .modelle import Bewertung, Stelle

REMOTE_HINWEISE = (
    "remote", "homeoffice", "home office", "home-office", "telearbeit",
    "ortsunabhängig", "ortsunabhaengig", "wfh", "work from home",
)

BEWERTUNGS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "punktzahl": {
            "type": "integer",
            "description": "0 bis 100. Wie gut passt das Inserat zum Profil?",
        },
        "begruendung": {
            "type": "string",
            "description": "Zwei bis drei Saetze, sachlich, auf Deutsch.",
        },
        "staerken": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Anforderungen des Inserats, die das Profil klar erfuellt.",
        },
        "luecken": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Anforderungen, die das Profil nicht oder nur teilweise erfuellt.",
        },
    },
    "required": ["punktzahl", "begruendung", "staerken", "luecken"],
    "additionalProperties": False,
}

SYSTEM = """Sie beurteilen Stelleninserate fuer eine erwachsene Fachperson, die sich
bewirbt. Sie sind streng und nuechtern: Eine hohe Punktzahl vergeben Sie nur, wenn
das Inserat tatsaechlich zum Profil passt, nicht schon dann, wenn ein Modewort
vorkommt.

Massstab fuer die Punktzahl:
90-100  Das Inserat sucht genau dieses Profil.
75-89   Deutliche Uebereinstimmung, einzelne Anforderungen fehlen.
60-74   Teilweise passend, ein Wechsel waere ein Sprung.
0-59    Passt nicht, andere Fachrichtung oder falsche Stufe.

Antworten Sie ausschliesslich im vorgegebenen JSON-Format, auf Deutsch."""


def _text(stelle: Stelle) -> str:
    return f"{stelle.titel}\n{stelle.beschreibung}".lower()


def ist_remote(stelle: Stelle) -> bool:
    text = _text(stelle)
    return any(hinweis in text for hinweis in REMOTE_HINWEISE)


def ort_passt(stelle: Stelle, profil: Profil) -> bool:
    """Regionale Naehe oder ausdrueckliche Remote-Moeglichkeit."""
    suche = profil.suche
    if suche.get("nur_remote"):
        return ist_remote(stelle)

    erlaubt = [o.lower() for o in suche.get("erlaubte_orte", []) if o]
    if not erlaubt:
        return True  # keine Ortsliste hinterlegt: nicht filtern

    ort = (stelle.ort or "").lower()
    if any(e in ort for e in erlaubt):
        return True
    return bool(suche.get("remote_ok")) and ist_remote(stelle)


def grobfilter(stelle: Stelle, profil: Profil) -> tuple[bool, str]:
    """Prueft, was schon aus der Trefferliste hervorgeht: Titel und Ort.

    Laeuft vor dem Nachladen der Detailseite und spart so Abfragen.
    """
    if not stelle.titel or not stelle.firma:
        return False, "Unvollstaendiges Inserat"

    titel = stelle.titel.lower()
    for wort in profil.suche.get("ausschluss_stichworte", []):
        if wort and wort.lower() in titel:
            return False, f"Ausschlussbegriff im Titel: {wort}"

    # Der Ort wird nur geprueft, wenn er in der Trefferliste ueberhaupt steht.
    if stelle.ort and not ort_passt(stelle, profil):
        return False, f"Ort ausserhalb des Suchgebiets: {stelle.ort}"

    return True, ""


def vorfilter(stelle: Stelle, profil: Profil) -> tuple[bool, str]:
    """Entscheidet ohne Modellaufruf, ob sich eine Bewertung lohnt.

    Rueckgabe: (durchgelassen, Begruendung bei Ablehnung).
    """
    if not stelle.titel or not stelle.firma:
        return False, "Unvollstaendiges Inserat"

    titel = stelle.titel.lower()
    for wort in profil.suche.get("ausschluss_stichworte", []):
        if wort and wort.lower() in titel:
            return False, f"Ausschlussbegriff im Titel: {wort}"

    if not ort_passt(stelle, profil):
        return False, f"Ort ausserhalb des Suchgebiets: {stelle.ort or 'unbekannt'}"

    muss = [w.lower() for w in profil.bewertung.get("muss_stichworte", []) if w]
    if muss:
        volltext = _text(stelle)
        if not any(w in volltext for w in muss):
            return False, "Kein fachlicher Bezug im Inseratstext"

    return True, ""


def bewerten(
    client: anthropic.Anthropic,
    stelle: Stelle,
    profil: Profil,
) -> Bewertung:
    """Laesst das Modell die Passung beurteilen."""
    modell = profil.bewertung.get("modell", "claude-opus-5")
    nachricht = _nachricht(stelle, profil)
    daten = antwort_json(
        client,
        modell=modell,
        system=SYSTEM,
        nachricht=nachricht,
        schema=BEWERTUNGS_SCHEMA,
        max_tokens=4000,
        aufwand="low",  # ein Urteil in dieser Groesse braucht keine hohe Denkleistung
    )
    return Bewertung(
        punktzahl=max(0, min(100, int(daten.get("punktzahl", 0)))),
        begruendung=str(daten.get("begruendung", "")).strip(),
        staerken=[str(s) for s in daten.get("staerken", [])],
        luecken=[str(s) for s in daten.get("luecken", [])],
    )


def _nachricht(stelle: Stelle, profil: Profil) -> str:
    beschreibung = re.sub(r"\n{3,}", "\n\n", stelle.beschreibung or "")[:12000]
    return f"""PROFIL DER BEWERBERIN ODER DES BEWERBERS
{profil.anschreiben.get('profil_text', '').strip()}

Gesuchte Anstellung: {', '.join(profil.suche.get('anstellung', [])) or 'nicht eingegrenzt'}

INSERAT
Titel: {stelle.titel}
Firma: {stelle.firma}
Ort: {stelle.ort or 'nicht angegeben'}
Pensum: {stelle.pensum or 'nicht angegeben'}

{beschreibung}"""

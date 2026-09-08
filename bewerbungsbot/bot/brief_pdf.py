"""Setzt das Anschreiben als PDF im Format eines Schweizer Geschaeftsbriefs."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from .konfig import WURZEL, Profil
from .modelle import Stelle

MONATE = [
    "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

_KOPF = ParagraphStyle(
    "Kopf", fontName="Helvetica", fontSize=9.5, leading=13, spaceAfter=0,
)
_ADRESSE = ParagraphStyle(
    "Adresse", fontName="Helvetica", fontSize=10.5, leading=15,
)
_BETREFF = ParagraphStyle(
    "Betreff", fontName="Helvetica-Bold", fontSize=10.5, leading=15, spaceAfter=6,
)
_TEXT = ParagraphStyle(
    "Text", fontName="Helvetica", fontSize=10.5, leading=15.5,
    alignment=TA_JUSTIFY, spaceAfter=10,
)


def datum_schweiz(tag: date | None = None) -> str:
    tag = tag or date.today()
    return f"{tag.day}. {MONATE[tag.month - 1]} {tag.year}"


def _schuetzen(text: str) -> str:
    """Maskiert Zeichen, die reportlab sonst als Auszeichnung liest."""
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def erzeugen(
    brief: dict[str, Any],
    stelle: Stelle,
    profil: Profil,
    ziel: Path | None = None,
) -> Path:
    """Schreibt das Anschreiben als PDF und gibt den Pfad zurueck."""
    ziel = Path(ziel) if ziel else _standardziel(stelle)
    ziel.parent.mkdir(parents=True, exist_ok=True)

    dokument = SimpleDocTemplate(
        str(ziel), pagesize=A4,
        leftMargin=25 * mm, rightMargin=20 * mm,
        topMargin=25 * mm, bottomMargin=20 * mm,
        title=brief.get("betreff", "Bewerbung"),
        author=profil.voller_name,
    )

    person = profil.person
    absender = [
        profil.voller_name,
        person.get("strasse", ""),
        f"{person.get('plz', '')} {person.get('ort', '')}".strip(),
        person.get("telefon", ""),
        person.get("email", ""),
    ]
    if person.get("linkedin"):
        absender.append(person["linkedin"])

    empfaenger = [stelle.firma]
    if stelle.kontakt_name:
        empfaenger.append(stelle.kontakt_name)
    if stelle.ort:
        empfaenger.append(stelle.ort)

    inhalt = [
        Paragraph(_schuetzen("\n".join(z for z in absender if z)), _KOPF),
        Spacer(1, 16 * mm),
        Paragraph(_schuetzen("\n".join(z for z in empfaenger if z)), _ADRESSE),
        Spacer(1, 14 * mm),
        Paragraph(
            _schuetzen(f"{person.get('ort', '')}, {datum_schweiz()}".lstrip(", ")),
            _KOPF,
        ),
        Spacer(1, 10 * mm),
        Paragraph(_schuetzen(brief.get("betreff", "")), _BETREFF),
        Spacer(1, 4 * mm),
        Paragraph(_schuetzen(brief.get("anrede", "")), _TEXT),
    ]
    for absatz in brief.get("absaetze", []):
        inhalt.append(Paragraph(_schuetzen(absatz), _TEXT))

    inhalt += [
        Spacer(1, 6 * mm),
        Paragraph(_schuetzen(profil.anschreiben.get("gruss", "Freundliche Gruesse")), _TEXT),
        Spacer(1, 12 * mm),
        Paragraph(_schuetzen(profil.voller_name), _TEXT),
    ]
    anhaenge = [p.name for p in profil.anhang_pfade()]
    if anhaenge:
        inhalt += [
            Spacer(1, 6 * mm),
            Paragraph(_schuetzen("Beilagen: " + ", ".join(anhaenge)), _KOPF),
        ]

    dokument.build(inhalt)
    return ziel


def _standardziel(stelle: Stelle) -> Path:
    def sauber(text: str) -> str:
        erlaubt = "".join(z if z.isalnum() or z in " -_" else "" for z in text)
        return "_".join(erlaubt.split())[:40] or "Stelle"

    name = f"Anschreiben_{sauber(stelle.firma)}_{sauber(stelle.titel)}.pdf"
    return WURZEL / "ausgabe" / "anschreiben" / name

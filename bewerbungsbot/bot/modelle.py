"""Datenklassen fuer Stellen und Bewertungen sowie die Statuswerte des Ablaufs."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Der Lebenslauf einer Stelle im Tool.
NEU = "neu"                  # gefunden, noch nicht bewertet
VERWORFEN = "verworfen"      # Vorfilter oder Bewertung unter der Schwelle
BEWERTET = "bewertet"        # ueber der Schwelle, noch kein Anschreiben
ENTWURF = "entwurf"          # Anschreiben liegt vor, wartet auf Ihre Freigabe
VERSENDET = "versendet"
FEHLER = "fehler"            # Versand fehlgeschlagen
ANTWORT = "antwort"          # Rueckmeldung des Arbeitgebers erfasst

STATUS_REIHENFOLGE = [ENTWURF, BEWERTET, NEU, VERSENDET, ANTWORT, FEHLER, VERWORFEN]

STATUS_BESCHRIFTUNG = {
    NEU: "Neu",
    VERWORFEN: "Verworfen",
    BEWERTET: "Bewertet",
    ENTWURF: "Wartet auf Freigabe",
    VERSENDET: "Versendet",
    FEHLER: "Fehler",
    ANTWORT: "Antwort erhalten",
}

_MEHRFACH_LEERRAUM = re.compile(r"\s+")


def jetzt() -> str:
    """Zeitstempel in ISO-Form, immer in UTC, damit Sortierungen stimmen."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalisieren(text: str) -> str:
    """Kleinschreibung ohne Mehrfachleerzeichen - Grundlage der Dublettenerkennung."""
    return _MEHRFACH_LEERRAUM.sub(" ", (text or "").strip().lower())


@dataclass
class Stelle:
    """Ein Inserat, unabhaengig von der Plattform, auf der es gefunden wurde."""

    titel: str
    firma: str
    ort: str = ""
    url: str = ""
    quelle: str = ""
    extern_id: str = ""
    pensum: str = ""
    beschreibung: str = ""
    kontakt_email: str = ""
    kontakt_name: str = ""
    veroeffentlicht: str = ""
    sprache: str = ""
    roh: dict[str, Any] = field(default_factory=dict)

    @property
    def fingerabdruck(self) -> str:
        """Erkennt dieselbe Stelle wieder, auch wenn sie auf zwei Portalen steht."""
        basis = "|".join(
            _normalisieren(t) for t in (self.firma, self.titel, self.ort)
        )
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()

    @property
    def bewerbungsweg(self) -> str:
        """E-Mail, wenn eine Adresse im Inserat steht, sonst Portal."""
        return "email" if self.kontakt_email else "portal"

    def kurz(self) -> str:
        teile = [self.titel, self.firma]
        if self.ort:
            teile.append(self.ort)
        return " - ".join(t for t in teile if t)


@dataclass
class Bewertung:
    """Das Urteil des Modells ueber eine Stelle."""

    punktzahl: int
    begruendung: str
    staerken: list[str] = field(default_factory=list)
    luecken: list[str] = field(default_factory=list)

    def passt(self, schwelle: int) -> bool:
        return self.punktzahl >= schwelle

"""Gemeinsame Grundlage aller Stellenquellen: HTTP-Sitzung, Textwerkzeuge, Schnittstelle."""

from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup

from ..konfig import Profil
from ..modelle import Stelle

# Ein Browser-Kennzeichen ist noetig, weil die Portale generische Klienten abweisen.
KENNUNG = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Adressen, die zwar im Seitentext stehen, aber nie der Bewerbungsweg sind.
_EMAIL_UNBRAUCHBAR = re.compile(
    r"(noreply|no-reply|donotreply|webmaster|datenschutz|privacy|abuse|support@jobs|@sentry|@example)",
    re.IGNORECASE,
)
_PENSUM = re.compile(r"(\d{2,3})\s*(?:-|bis|–)\s*(\d{2,3})\s*%|(\d{2,3})\s*%")


class Quelle(ABC):
    """Schnittstelle, die jede Stellenboerse erfuellen muss."""

    name: str = "unbekannt"

    def __init__(self, profil: Profil, pause: float = 4.0) -> None:
        self.profil = profil
        self.pause = pause
        self.sitzung = requests.Session()
        self.sitzung.headers.update({
            "User-Agent": KENNUNG,
            "Accept-Language": "de-CH,de;q=0.9,en;q=0.6",
        })

    @abstractmethod
    def suchen(self) -> list[Stelle]:
        """Liefert die gefundenen Inserate, ohne sie zu bewerten."""

    # -- Hilfen fuer die Adapter -------------------------------------------

    def warten(self) -> None:
        """Hoeflichkeitspause zwischen zwei Abfragen derselben Plattform."""
        time.sleep(self.pause)

    def holen(self, url: str, **kwargs: Any) -> requests.Response:
        antwort = self.sitzung.get(url, timeout=25, **kwargs)
        antwort.raise_for_status()
        return antwort


def erstes_feld(daten: dict[str, Any], *namen: str, standard: str = "") -> str:
    """Nimmt den ersten belegten Schluessel.

    Die Portale benennen ihre JSON-Felder gelegentlich um. Statt an einem Namen
    zu haengen, probiert der Adapter mehrere Kandidaten durch.
    """
    for name in namen:
        wert = daten
        for teil in name.split("."):
            if isinstance(wert, dict):
                wert = wert.get(teil)
            else:
                wert = None
                break
        if isinstance(wert, (str, int, float)) and str(wert).strip():
            return str(wert).strip()
        if isinstance(wert, list) and wert:
            erstes = wert[0]
            if isinstance(erstes, str) and erstes.strip():
                return erstes.strip()
            if isinstance(erstes, dict):
                for schluessel in ("name", "title", "city", "label", "text"):
                    if isinstance(erstes.get(schluessel), str) and erstes[schluessel].strip():
                        return erstes[schluessel].strip()
    return standard


def html_zu_text(html: str) -> str:
    """Macht aus einer Inseratsseite lesbaren Fliesstext."""
    suppe = BeautifulSoup(html or "", "html.parser")
    for stoerend in suppe(["script", "style", "noscript", "nav", "footer", "header"]):
        stoerend.decompose()
    text = suppe.get_text("\n")
    zeilen = [z.strip() for z in text.splitlines()]
    return "\n".join(z for z in zeilen if z)


def email_finden(*texte: str) -> str:
    """Sucht die plausibelste Bewerbungsadresse in Text oder HTML."""
    kandidaten: list[str] = []
    for text in texte:
        if not text:
            continue
        kandidaten.extend(_EMAIL.findall(text))
    for adresse in kandidaten:
        if not _EMAIL_UNBRAUCHBAR.search(adresse):
            return adresse.strip(".,;:")
    return ""


def pensum_finden(text: str) -> str:
    """Zieht eine Pensumangabe wie '80-100%' aus dem Inseratstext."""
    treffer = _PENSUM.search(text or "")
    if not treffer:
        return ""
    if treffer.group(1) and treffer.group(2):
        return f"{treffer.group(1)}-{treffer.group(2)}%"
    return f"{treffer.group(3)}%"


def entdoppeln(stellen: Iterable[Stelle]) -> list[Stelle]:
    """Entfernt Mehrfachtreffer innerhalb eines Laufs."""
    gesehen: set[str] = set()
    ergebnis: list[Stelle] = []
    for stelle in stellen:
        if stelle.fingerabdruck in gesehen:
            continue
        gesehen.add(stelle.fingerabdruck)
        ergebnis.append(stelle)
    return ergebnis

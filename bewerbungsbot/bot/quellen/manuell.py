"""Notausgang: Inserate, die Sie selbst als Link hinterlegen.

Gedacht fuer zwei Faelle - eine Plattform sperrt den automatischen Zugriff,
oder Sie stossen selbst auf ein Inserat, das die Suche nicht gefunden hat.
Die Datei config/manuelle_stellen.yaml enthaelt dann schlicht eine Liste von URLs.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import yaml

from ..konfig import WURZEL
from ..modelle import Stelle
from .basis import Quelle, email_finden, html_zu_text, pensum_finden

LISTE = WURZEL / "config" / "manuelle_stellen.yaml"


class Manuell(Quelle):
    name = "manuell"

    def __init__(self, *args, liste: Path | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.liste = Path(liste) if liste else LISTE

    def suchen(self) -> list[Stelle]:
        if not self.liste.exists():
            return []
        eintraege = yaml.safe_load(self.liste.read_text(encoding="utf-8")) or []
        stellen: list[Stelle] = []
        for eintrag in eintraege:
            stelle = self._eintrag_lesen(eintrag)
            if stelle:
                stellen.append(stelle)
            self.warten()
        print(f"  [manuell] {len(stellen)} Inserate aus {self.liste.name}")
        return stellen

    def _eintrag_lesen(self, eintrag) -> Stelle | None:
        # Erlaubt sind eine blosse URL oder ein Eintrag mit zusaetzlichen Angaben.
        if isinstance(eintrag, str):
            eintrag = {"url": eintrag}
        if not isinstance(eintrag, dict) or not eintrag.get("url"):
            return None

        url = eintrag["url"]
        text = ""
        try:
            antwort = self.holen(url)
            text = html_zu_text(antwort.text)
            gefundene_adresse = email_finden(antwort.text, text)
        except Exception as fehler:
            print(f"  [manuell] {url} nicht erreichbar: {fehler}")
            gefundene_adresse = ""

        return Stelle(
            titel=eintrag.get("titel") or self._titel_raten(text, url),
            firma=eintrag.get("firma") or urlparse(url).netloc.replace("www.", ""),
            ort=eintrag.get("ort", ""),
            url=url,
            quelle=self.name,
            pensum=eintrag.get("pensum") or pensum_finden(text),
            beschreibung=text,
            kontakt_email=eintrag.get("email") or gefundene_adresse,
            sprache="de",
        )

    @staticmethod
    def _titel_raten(text: str, url: str) -> str:
        """Erste brauchbare Zeile der Seite, sonst der letzte Pfadabschnitt."""
        for zeile in text.splitlines():
            if 8 <= len(zeile) <= 90:
                return zeile
        pfad = urlparse(url).path.rstrip("/").split("/")
        return pfad[-1].replace("-", " ").title() if pfad and pfad[-1] else "Unbekannte Stelle"

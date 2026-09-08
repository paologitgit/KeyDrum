"""Adapter fuer jobs.ch.

Die Suche laeuft ueber die oeffentliche Schnittstelle, die auch die Website
selbst benutzt. Deren Feldnamen sind nicht vertraglich zugesichert und koennen
sich aendern. Der Adapter liest deshalb tolerant (mehrere Namenskandidaten pro
Feld) und kann die Rohantwort mitschreiben, damit eine Anpassung an einer
einzigen Stelle genuegt: in FELDER weiter unten.

Rechtlicher Hinweis: Die Nutzungsbedingungen von jobs.ch untersagen
automatisiertes Auslesen. Der Adapter fragt daher mit Pausen ab und ist auf
den privaten Eigenbedarf ausgelegt. Wer die Schnittstelle haerter beansprucht,
riskiert eine Sperre der eigenen IP-Adresse.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..konfig import WURZEL
from ..modelle import Stelle
from .basis import Quelle, email_finden, erstes_feld, html_zu_text, pensum_finden

BASIS = "https://www.jobs.ch"
SUCH_URL = f"{BASIS}/api/v1/public/search"

# Namenskandidaten je Feld. Der erste belegte gewinnt.
FELDER = {
    "id": ("job_id", "id", "slug"),
    "titel": ("title", "job_title", "name"),
    "firma": ("company_name", "company.name", "company", "employer_name"),
    "ort": ("place", "city", "location", "work_locations", "locations"),
    "url": ("url", "link", "public_url", "slug"),
    "text": ("template_text", "description", "preview", "text", "body"),
    "datum": ("publication_date", "published", "created_at", "date"),
    "pensum": ("employment_position_ids", "workload", "employment_grade"),
}


class JobsCh(Quelle):
    name = "jobs.ch"

    def __init__(self, *args: Any, rohdaten_ablegen: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.rohdaten_ablegen = rohdaten_ablegen
        self.zeilen_pro_seite = 20

    # -- oeffentlich --------------------------------------------------------

    def suchen(self) -> list[Stelle]:
        stichworte = self.profil.suche.get("stichworte", [])
        umkreis = int(self.profil.suche.get("umkreis_km", 0) or 0)
        # Bei reiner Remote-Suche ist der Ort bedeutungslos, eine Abfrage genuegt.
        orte = [""] if self.profil.suche.get("nur_remote") else (
            self.profil.suche.get("orte") or [""]
        )

        gefunden: list[Stelle] = []
        for stichwort in stichworte:
            for ort in orte:
                try:
                    gefunden.extend(self._abfrage(stichwort, ort, umkreis))
                except Exception as fehler:  # eine kaputte Abfrage darf den Lauf nicht beenden
                    print(f"  [jobs.ch] '{stichwort}' / '{ort}' fehlgeschlagen: {fehler}")
                self.warten()
        return gefunden

    def details_nachladen(self, stelle: Stelle) -> Stelle:
        """Holt den vollen Inseratstext und sucht darin eine Bewerbungsadresse."""
        if not stelle.url:
            return stelle
        try:
            antwort = self.holen(stelle.url)
        except Exception as fehler:
            print(f"  [jobs.ch] Detailseite nicht erreichbar ({stelle.url}): {fehler}")
            return stelle

        text = html_zu_text(antwort.text)
        if len(text) > len(stelle.beschreibung):
            stelle.beschreibung = text
        if not stelle.kontakt_email:
            stelle.kontakt_email = email_finden(antwort.text, text)
        if not stelle.pensum:
            stelle.pensum = pensum_finden(text)
        return stelle

    # -- intern -------------------------------------------------------------

    def _abfrage(self, stichwort: str, ort: str, umkreis: int) -> list[Stelle]:
        parameter: dict[str, Any] = {
            "query": stichwort,
            "rows": self.zeilen_pro_seite,
            "page": 1,
        }
        if ort:
            parameter["location"] = ort
            if umkreis:
                parameter["radius"] = umkreis
        if self.profil.suche.get("nur_remote"):
            parameter["home_office"] = "true"

        antwort = self.holen(SUCH_URL, params=parameter)
        daten = antwort.json()
        if self.rohdaten_ablegen:
            self._rohdaten_schreiben(stichwort, ort, daten)

        eintraege = self._eintraege(daten)
        stellen = [self._zu_stelle(e) for e in eintraege]
        brauchbar = [s for s in stellen if s.titel and s.firma]
        ortsteil = f" / {ort}" if ort else ""
        print(f"  [jobs.ch] '{stichwort}'{ortsteil}: {len(brauchbar)} Treffer")
        return brauchbar

    @staticmethod
    def _eintraege(daten: Any) -> list[dict[str, Any]]:
        """Findet die Trefferliste, egal unter welchem Schluessel sie steckt."""
        if isinstance(daten, list):
            return [e for e in daten if isinstance(e, dict)]
        if not isinstance(daten, dict):
            return []
        for schluessel in ("documents", "results", "jobs", "items", "data", "hits"):
            wert = daten.get(schluessel)
            if isinstance(wert, list):
                return [e for e in wert if isinstance(e, dict)]
            if isinstance(wert, dict):  # etwa {"hits": {"hits": [...]}}
                for innen in ("documents", "results", "items", "hits"):
                    if isinstance(wert.get(innen), list):
                        return [e for e in wert[innen] if isinstance(e, dict)]
        return []

    def _zu_stelle(self, eintrag: dict[str, Any]) -> Stelle:
        text_roh = erstes_feld(eintrag, *FELDER["text"])
        text = html_zu_text(text_roh) if "<" in text_roh else text_roh
        titel = erstes_feld(eintrag, *FELDER["titel"])
        # Das Pensum steht auf jobs.ch meist im Titel ("... 80-100%"), nicht im Text.
        return Stelle(
            titel=titel,
            firma=erstes_feld(eintrag, *FELDER["firma"]),
            ort=erstes_feld(eintrag, *FELDER["ort"]),
            url=self._url_bauen(eintrag),
            quelle=self.name,
            extern_id=erstes_feld(eintrag, *FELDER["id"]),
            pensum=erstes_feld(eintrag, *FELDER["pensum"]) or pensum_finden(f"{titel}\n{text}"),
            beschreibung=text,
            kontakt_email=email_finden(text_roh, text),
            veroeffentlicht=erstes_feld(eintrag, *FELDER["datum"]),
            sprache="de",
            roh=eintrag,
        )

    @staticmethod
    def _url_bauen(eintrag: dict[str, Any]) -> str:
        roh = erstes_feld(eintrag, *FELDER["url"])
        if roh.startswith("http"):
            return roh
        if roh.startswith("/"):
            return f"{BASIS}{roh}"
        kennung = erstes_feld(eintrag, *FELDER["id"])
        return f"{BASIS}/de/vacancies/detail/{kennung}/" if kennung else ""

    @staticmethod
    def _rohdaten_schreiben(stichwort: str, ort: str, daten: Any) -> None:
        """Legt die unveraenderte Antwort ab - Grundlage fuer die Feldzuordnung."""
        ordner = WURZEL / "ausgabe" / "rohdaten"
        ordner.mkdir(parents=True, exist_ok=True)
        name = "".join(z if z.isalnum() else "_" for z in f"jobs_ch_{stichwort}_{ort}")
        ziel = Path(ordner) / f"{name}.json"
        ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [jobs.ch] Rohantwort abgelegt: {ziel}")

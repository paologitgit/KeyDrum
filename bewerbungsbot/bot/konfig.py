"""Laedt Profil (YAML) und Zugangsdaten (.env) und stellt beides typisiert bereit."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

WURZEL = Path(__file__).resolve().parent.parent


class KonfigFehler(RuntimeError):
    """Die Konfiguration ist unvollstaendig oder widerspruechlich."""


@dataclass
class Zugang:
    """Zugangsdaten aus der .env-Datei."""

    anthropic_key: str | None
    smtp_host: str | None
    smtp_port: int
    smtp_benutzer: str | None
    smtp_passwort: str | None
    smtp_absender: str | None
    trockenlauf: bool

    @classmethod
    def laden(cls, env_datei: Path | None = None) -> "Zugang":
        load_dotenv(env_datei or WURZEL / ".env")
        return cls(
            anthropic_key=os.getenv("ANTHROPIC_API_KEY") or None,
            smtp_host=os.getenv("SMTP_HOST") or None,
            smtp_port=int(os.getenv("SMTP_PORT") or 587),
            smtp_benutzer=os.getenv("SMTP_BENUTZER") or None,
            smtp_passwort=os.getenv("SMTP_PASSWORT") or None,
            smtp_absender=os.getenv("SMTP_ABSENDER") or os.getenv("SMTP_BENUTZER") or None,
            # Nur ein ausdrueckliches "0" schaltet den Versand scharf.
            trockenlauf=(os.getenv("TROCKENLAUF", "1").strip() not in {"0", "false", "False"}),
        )

    def smtp_bereit(self) -> bool:
        return all([self.smtp_host, self.smtp_benutzer, self.smtp_passwort, self.smtp_absender])


@dataclass
class Profil:
    """Das Bewerberprofil samt Such- und Versandregeln."""

    person: dict[str, Any]
    suche: dict[str, Any]
    bewertung: dict[str, Any]
    anschreiben: dict[str, Any]
    dokumente: dict[str, Any]
    versand: dict[str, Any]
    grenzen: dict[str, Any]
    pfad: Path = field(default=WURZEL / "config" / "profil.yaml")

    @classmethod
    def laden(cls, pfad: Path | None = None) -> "Profil":
        pfad = Path(pfad) if pfad else WURZEL / "config" / "profil.yaml"
        if not pfad.exists():
            raise KonfigFehler(
                f"Profil nicht gefunden: {pfad}\n"
                "Kopieren Sie config/profil.beispiel.yaml nach config/profil.yaml "
                "und tragen Sie Ihre Daten ein."
            )
        daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
        fehlend = [s for s in ("person", "suche", "anschreiben") if s not in daten]
        if fehlend:
            raise KonfigFehler(f"Im Profil fehlen die Abschnitte: {', '.join(fehlend)}")
        return cls(
            person=daten.get("person", {}),
            suche=daten.get("suche", {}),
            bewertung=daten.get("bewertung", {}),
            anschreiben=daten.get("anschreiben", {}),
            dokumente=daten.get("dokumente", {}),
            versand=daten.get("versand", {}),
            grenzen=daten.get("grenzen", {}),
            pfad=pfad,
        )

    # -- bequeme Zugriffe ---------------------------------------------------

    @property
    def voller_name(self) -> str:
        return f"{self.person.get('vorname', '')} {self.person.get('nachname', '')}".strip()

    @property
    def schwelle(self) -> int:
        return int(self.bewertung.get("schwelle", 70))

    @property
    def dokument_ordner(self) -> Path:
        ordner = Path(self.dokumente.get("ordner", "dokumente"))
        return ordner if ordner.is_absolute() else WURZEL / ordner

    def anhang_pfade(self) -> list[Path]:
        """Die dauerhaften Anhaenge (Lebenslauf, Zeugnisse) als Pfade."""
        return [self.dokument_ordner / name for name in self.dokumente.get("anhaenge", [])]

    def fehlende_anhaenge(self) -> list[Path]:
        return [p for p in self.anhang_pfade() if not p.exists()]

    def signatur(self) -> str:
        vorlage = self.versand.get("signatur", "{vorname} {nachname}\n{telefon} | {email}")
        return vorlage.format(**{k: (v or "") for k, v in self.person.items()})

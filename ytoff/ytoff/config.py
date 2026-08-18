"""Konfiguration: Abo-Liste als YAML lesen, schreiben, validieren."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(os.environ.get("YTOFF_CONFIG_DIR", "~/.config/ytoff")).expanduser()
CONFIG_PATH = CONFIG_DIR / "config.yaml"

#: Liegt in der Bibliothek selbst, nicht neben der Konfiguration: wer die
#: Bibliothek loescht, loescht den Zustand mit -- der naechste Sync fuellt
#: sie dann sauber wieder auf, statt alles als "schon geladen" zu ueberspringen.
ARCHIVE_NAME = ".ytoff-archive.txt"

DEFAULT_TARGET = "~/Movies/YT-Offline"
DEFAULT_HEIGHT = 1080

VALID_SPONSOR_CATEGORIES = {
    "sponsor", "selfpromo", "interaction", "intro", "outro",
    "preview", "filler", "music_offtopic",
}


class ConfigError(Exception):
    """Die Konfigurationsdatei ist unbrauchbar -- mit Klartext fuer den Nutzer."""


@dataclass
class Extras:
    untertitel: list[str] = field(default_factory=lambda: ["de", "en"])
    kapitel: bool = True
    thumbnail: bool = True
    metadaten: bool = True
    sponsor_entfernen: list[str] = field(default_factory=list)


@dataclass
class Tempo:
    """Drosselung. Absichtlich konservativ voreingestellt: zu schnelles
    Herunterladen fuehrt zu temporaeren Sperren durch YouTube."""

    pause_zwischen_anfragen: float = 0.75
    parallele_fragmente: int = 4


@dataclass
class Subscription:
    url: str
    name: str = ""
    limit_neueste: int = 20
    ab_datum: str = ""
    nur_audio: bool = False
    max_hoehe: int = 0  # 0 = globale Vorgabe verwenden

    def label(self) -> str:
        return self.name or self.url


@dataclass
class Config:
    ziel: Path = Path(DEFAULT_TARGET).expanduser()
    max_hoehe: int = DEFAULT_HEIGHT
    tempo: Tempo = field(default_factory=Tempo)
    extras: Extras = field(default_factory=Extras)
    kanaele: list[Subscription] = field(default_factory=list)

    @property
    def archive_path(self) -> Path:
        return self.ziel / ARCHIVE_NAME

    def height_for(self, sub: Subscription) -> int:
        return sub.max_hoehe or self.max_hoehe


def _as_list(value: Any, key: str) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return value
    raise ConfigError(f"'{key}' muss eine Liste sein, ist aber {type(value).__name__}.")


def parse(raw: dict[str, Any]) -> Config:
    """Baut eine Config aus rohem YAML. Unbekannte Schluessel sind ein Fehler --
    ein vertippter Schluessel soll auffallen und nicht still ignoriert werden."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("Die Konfiguration muss ein YAML-Objekt sein.")

    unknown = set(raw) - {"ziel", "max_hoehe", "tempo", "extras", "kanaele"}
    if unknown:
        raise ConfigError(f"Unbekannte Schluessel: {', '.join(sorted(unknown))}")

    cfg = Config()
    if "ziel" in raw:
        cfg.ziel = Path(str(raw["ziel"])).expanduser()
    if "max_hoehe" in raw:
        cfg.max_hoehe = int(raw["max_hoehe"])

    tempo = raw.get("tempo") or {}
    if tempo:
        cfg.tempo = Tempo(
            pause_zwischen_anfragen=float(
                tempo.get("pause_zwischen_anfragen", Tempo.pause_zwischen_anfragen)
            ),
            parallele_fragmente=int(
                tempo.get("parallele_fragmente", Tempo.parallele_fragmente)
            ),
        )

    extras = raw.get("extras") or {}
    if extras:
        sponsor = [str(c) for c in _as_list(extras.get("sponsor_entfernen"), "sponsor_entfernen")]
        bad = set(sponsor) - VALID_SPONSOR_CATEGORIES
        if bad:
            raise ConfigError(
                f"Unbekannte SponsorBlock-Kategorien: {', '.join(sorted(bad))}. "
                f"Erlaubt: {', '.join(sorted(VALID_SPONSOR_CATEGORIES))}"
            )
        cfg.extras = Extras(
            untertitel=[str(s) for s in _as_list(extras.get("untertitel", ["de", "en"]), "untertitel")],
            kapitel=bool(extras.get("kapitel", True)),
            thumbnail=bool(extras.get("thumbnail", True)),
            metadaten=bool(extras.get("metadaten", True)),
            sponsor_entfernen=sponsor,
        )

    for i, entry in enumerate(_as_list(raw.get("kanaele"), "kanaele"), start=1):
        if isinstance(entry, str):
            entry = {"url": entry}
        if not isinstance(entry, dict) or not entry.get("url"):
            raise ConfigError(f"Eintrag {i} unter 'kanaele' hat keine 'url'.")
        unknown = set(entry) - {"url", "name", "limit_neueste", "ab_datum", "nur_audio", "max_hoehe"}
        if unknown:
            raise ConfigError(
                f"Eintrag {i} ({entry['url']}): unbekannte Schluessel: {', '.join(sorted(unknown))}"
            )
        ab_datum = str(entry.get("ab_datum", "") or "")
        if ab_datum and not (len(ab_datum) == 8 and ab_datum.isdigit()):
            raise ConfigError(
                f"Eintrag {i}: 'ab_datum' muss das Format JJJJMMTT haben, ist '{ab_datum}'."
            )
        cfg.kanaele.append(
            Subscription(
                url=str(entry["url"]),
                name=str(entry.get("name", "") or ""),
                limit_neueste=int(entry.get("limit_neueste", 20)),
                ab_datum=ab_datum,
                nur_audio=bool(entry.get("nur_audio", False)),
                max_hoehe=int(entry.get("max_hoehe", 0) or 0),
            )
        )
    return cfg


def to_dict(cfg: Config) -> dict[str, Any]:
    data: dict[str, Any] = {
        "ziel": str(cfg.ziel),
        "max_hoehe": cfg.max_hoehe,
        "tempo": {
            "pause_zwischen_anfragen": cfg.tempo.pause_zwischen_anfragen,
            "parallele_fragmente": cfg.tempo.parallele_fragmente,
        },
        "extras": {
            "untertitel": cfg.extras.untertitel,
            "kapitel": cfg.extras.kapitel,
            "thumbnail": cfg.extras.thumbnail,
            "metadaten": cfg.extras.metadaten,
            "sponsor_entfernen": cfg.extras.sponsor_entfernen,
        },
        "kanaele": [],
    }
    for sub in cfg.kanaele:
        entry: dict[str, Any] = {"url": sub.url, "limit_neueste": sub.limit_neueste}
        if sub.name:
            entry["name"] = sub.name
        if sub.ab_datum:
            entry["ab_datum"] = sub.ab_datum
        if sub.nur_audio:
            entry["nur_audio"] = True
        if sub.max_hoehe:
            entry["max_hoehe"] = sub.max_hoehe
        data["kanaele"].append(entry)
    return data


def load(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        raise ConfigError(
            f"Keine Konfiguration unter {path}. Erst 'ytoff init' ausfuehren."
        )
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} ist kein gueltiges YAML: {exc}") from exc
    return parse(raw)


def save(cfg: Config, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(to_dict(cfg), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

"""Gemeinsame Testvorgaben."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.konfig import Profil, Zugang  # noqa: E402
from bot.modelle import Stelle  # noqa: E402


@pytest.fixture
def profil(tmp_path: Path) -> Profil:
    return Profil(
        person={
            "vorname": "Anna", "nachname": "Beispiel", "strasse": "Musterweg 2",
            "plz": "8000", "ort": "Zuerich", "email": "anna@example.ch",
            "telefon": "+41 79 111 22 33",
        },
        suche={
            "stichworte": ["KI"],
            "orte": ["Zuerich"],
            "umkreis_km": 30,
            "erlaubte_orte": ["Zuerich", "Winterthur", "Zug"],
            "remote_ok": True,
            "nur_remote": False,
            "ausschluss_stichworte": ["Praktikum", "Lehrstelle"],
        },
        bewertung={"schwelle": 70, "muss_stichworte": ["KI", "Automatisierung"]},
        anschreiben={
            "profil_text": "Erwachsenenbildung und KI-gestuetzte Ablaeufe.",
            "gruss": "Freundliche Gruesse",
            "anrede_unbekannt": "Sehr geehrte Damen und Herren",
        },
        dokumente={"ordner": str(tmp_path / "dokumente"), "anhaenge": ["Lebenslauf.pdf"]},
        versand={"signatur": "{vorname} {nachname}\n{email}", "kopie_an_mich": True},
        grenzen={"max_bewerbungen_pro_tag": 5, "pause_sekunden": 0},
        pfad=tmp_path / "profil.yaml",
    )


@pytest.fixture
def zugang() -> Zugang:
    return Zugang(
        anthropic_key="test", smtp_host="smtp.example.ch", smtp_port=587,
        smtp_benutzer="anna@example.ch", smtp_passwort="geheim",
        smtp_absender="anna@example.ch", trockenlauf=True,
    )


@pytest.fixture
def stelle() -> Stelle:
    return Stelle(
        titel="KI-Spezialist Prozessautomatisierung",
        firma="Muster AG",
        ort="Zuerich",
        url="https://www.jobs.ch/de/vacancies/detail/123/",
        quelle="jobs.ch",
        beschreibung=(
            "Wir suchen eine Person, die KI-Werkzeuge einfuehrt und Ablaeufe "
            "automatisiert. Bewerbungen an bewerbung@muster.ch."
        ),
        kontakt_email="bewerbung@muster.ch",
    )

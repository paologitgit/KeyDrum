"""Anschreiben, PDF und Mailversand - ohne Modell- oder Netzzugriff."""

from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

from bot import anschreiben, brief_pdf
from bot.versand import VersandFehler, nachricht_bauen, versenden

BRIEF = {
    "betreff": "Bewerbung als KI-Spezialist",
    "anrede": "Sehr geehrte Frau Meier,",
    "absaetze": [
        "Ihre Ausschreibung nennt die Einfuehrung von KI-Werkzeugen.",
        "In der Erwachsenenbildung entwickle ich seit Jahren Lehrmittel.",
        "Ueber ein Gespraech wuerde ich mich freuen.",
    ],
}


def test_pdf_wird_erzeugt(tmp_path, profil, stelle):
    ziel = tmp_path / "brief.pdf"
    ergebnis = brief_pdf.erzeugen(BRIEF, stelle, profil, ziel=ziel)
    assert ergebnis == ziel and ziel.exists()
    inhalt = ziel.read_bytes()
    assert inhalt.startswith(b"%PDF") and len(inhalt) > 1000


def test_pdf_vertraegt_sonderzeichen(tmp_path, profil, stelle):
    brief = dict(BRIEF, absaetze=["Forschung & Entwicklung <intern>"])
    ziel = brief_pdf.erzeugen(brief, stelle, profil, ziel=tmp_path / "s.pdf")
    assert ziel.exists()


def test_text_und_rueckweg(profil):
    text = anschreiben.als_text(BRIEF, profil)
    assert text.startswith("Sehr geehrte Frau Meier,")
    assert text.rstrip().endswith(profil.voller_name)

    zurueck = anschreiben.aus_text(text, profil)
    assert zurueck["anrede"] == BRIEF["anrede"]
    assert zurueck["absaetze"] == BRIEF["absaetze"]


def test_mail_traegt_anhaenge_und_blindkopie(tmp_path, profil, zugang):
    anhang = tmp_path / "Lebenslauf.pdf"
    anhang.write_bytes(b"%PDF-1.4 Testinhalt")

    nachricht = nachricht_bauen(
        profil, zugang, "bewerbung@muster.ch", "Bewerbung als KI-Spezialist",
        "Sehr geehrte Damen und Herren\n\nText.", [anhang],
    )
    assert isinstance(nachricht, EmailMessage)
    assert nachricht["To"] == "bewerbung@muster.ch"
    assert nachricht["Bcc"] == profil.person["email"]
    namen = [t.get_filename() for t in nachricht.iter_attachments()]
    assert namen == ["Lebenslauf.pdf"]
    assert profil.person["email"] in nachricht.get_body(("plain",)).get_content()


def test_probelauf_verschickt_nichts(tmp_path, profil, zugang, monkeypatch):
    monkeypatch.setattr("bot.versand.email_versand.POSTAUSGANG", tmp_path / "postausgang")
    anhang = tmp_path / "Lebenslauf.pdf"
    anhang.write_bytes(b"%PDF-1.4")

    echt, meldung = versenden(
        profil, zugang, "bewerbung@muster.ch", "Bewerbung", "Text", [anhang]
    )
    assert echt is False
    assert "Probelauf" in meldung
    abgelegt = list((tmp_path / "postausgang").glob("*.eml"))
    assert len(abgelegt) == 1
    assert b"bewerbung@muster.ch" in abgelegt[0].read_bytes()


def test_fehlender_anhang_bricht_ab(profil, zugang):
    with pytest.raises(VersandFehler, match="fehlen"):
        versenden(profil, zugang, "a@b.ch", "Betreff", "Text", [Path("/gibt/es/nicht.pdf")])


def test_unbrauchbare_adresse_bricht_ab(profil, zugang):
    with pytest.raises(VersandFehler, match="Empfaengeradresse"):
        versenden(profil, zugang, "keine-adresse", "Betreff", "Text", [])

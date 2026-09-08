"""Das Dashboard - laeuft es an, zeigt es die Daten, greifen die Aktionen?"""

from __future__ import annotations

import pytest

pytest.importorskip("httpx", reason="Fuer den Test des Dashboards wird httpx gebraucht.")
from fastapi.testclient import TestClient  # noqa: E402

from bot.db import Ablage  # noqa: E402
from bot.modelle import BEWERTET, ENTWURF, VERWORFEN, Bewertung  # noqa: E402
from bot.web.app import anwendung  # noqa: E402


@pytest.fixture(autouse=True)
def nur_im_testordner(tmp_path, monkeypatch):
    """Erzeugte PDFs und Mails landen im Testordner, nicht im Projekt."""
    monkeypatch.setattr("bot.brief_pdf.WURZEL", tmp_path)
    monkeypatch.setattr("bot.versand.email_versand.POSTAUSGANG", tmp_path / "postausgang")


@pytest.fixture
def klient_mit_stelle(tmp_path, profil, zugang, stelle):
    ablage = Ablage(tmp_path / "web.sqlite")
    stelle_id, _ = ablage.aufnehmen(stelle)
    ablage.bewertung_speichern(
        stelle_id, Bewertung(84, "Passt.", ["KI-Einfuehrung"], ["Fuehrungserfahrung"]), BEWERTET
    )
    ablage.entwurf_speichern(
        stelle_id, "Bewerbung als KI-Spezialist",
        "Sehr geehrte Damen und Herren,\n\nText.\n\nFreundliche Gruesse\nAnna Beispiel",
        empfaenger="bewerbung@muster.ch",
    )
    with TestClient(anwendung(profil, zugang, ablage)) as klient:
        yield klient, ablage, stelle_id
    ablage.schliessen()


def test_uebersicht_zeigt_die_stelle(klient_mit_stelle):
    klient, _, _ = klient_mit_stelle
    antwort = klient.get("/")
    assert antwort.status_code == 200
    assert "KI-Spezialist" in antwort.text
    assert "84" in antwort.text


def test_detailseite_zeigt_einschaetzung(klient_mit_stelle):
    klient, _, stelle_id = klient_mit_stelle
    antwort = klient.get(f"/stelle/{stelle_id}")
    assert antwort.status_code == 200
    assert "KI-Einfuehrung" in antwort.text
    assert "Fuehrungserfahrung" in antwort.text
    assert "bewerbung@muster.ch" in antwort.text


def test_speichern_setzt_pdf_neu(klient_mit_stelle, tmp_path):
    klient, ablage, stelle_id = klient_mit_stelle
    antwort = klient.post(
        f"/stelle/{stelle_id}/speichern",
        data={
            "betreff": "Bewerbung als KI-Fachperson",
            "anschreiben": "Sehr geehrte Damen und Herren,\n\nNeuer Text.\n\nFreundliche Gruesse\nAnna",
            "empfaenger": "jobs@muster.ch",
            "notiz": "Nachfassen am 20.",
        },
        follow_redirects=True,
    )
    assert antwort.status_code == 200
    zeile = ablage.holen(stelle_id)
    assert zeile["betreff"] == "Bewerbung als KI-Fachperson"
    assert zeile["empfaenger"] == "jobs@muster.ch"
    assert zeile["notiz"] == "Nachfassen am 20."
    assert zeile["anschreiben_pdf"] and zeile["anschreiben_pdf"].endswith(".pdf")


def test_verwerfen_aendert_den_status(klient_mit_stelle):
    klient, ablage, stelle_id = klient_mit_stelle
    klient.post(f"/stelle/{stelle_id}/verwerfen", follow_redirects=True)
    assert ablage.holen(stelle_id)["status"] == VERWORFEN


def test_senden_im_probelauf_verschickt_nichts(klient_mit_stelle, tmp_path, monkeypatch, profil):
    """Ohne Lebenslauf im Ordner bricht der Versand sauber ab, statt halb zu senden."""
    klient, ablage, stelle_id = klient_mit_stelle
    antwort = klient.post(f"/stelle/{stelle_id}/senden", follow_redirects=True)
    assert antwort.status_code == 200
    assert ablage.holen(stelle_id)["status"] != "versendet"
    assert "fehlen" in (ablage.holen(stelle_id)["fehler"] or "")


def test_versand_im_probelauf_mit_vorhandenem_anhang(klient_mit_stelle, profil, tmp_path):
    klient, ablage, stelle_id = klient_mit_stelle
    profil.dokument_ordner.mkdir(parents=True, exist_ok=True)
    (profil.dokument_ordner / "Lebenslauf.pdf").write_bytes(b"%PDF-1.4")

    klient.post(f"/stelle/{stelle_id}/senden", follow_redirects=True)
    zeile = ablage.holen(stelle_id)
    assert zeile["status"] == "versendet"
    assert zeile["versendet_am"]
    # Der Probelauf haelt fest, dass nichts wirklich hinausging.
    assert any("Probelauf" in (e["text"] or "") for e in ablage.ereignisse(stelle_id))


def test_status_liste_gefiltert(klient_mit_stelle):
    klient, _, _ = klient_mit_stelle
    assert "KI-Spezialist" in klient.get(f"/?status={ENTWURF}").text
    assert "KI-Spezialist" not in klient.get(f"/?status={VERWORFEN}").text


def test_startseite_zeigt_den_ersten_gefuellten_reiter(tmp_path, profil, zugang, stelle):
    """Wer nur gesucht hat, soll die neuen Stellen sehen, nicht eine leere Freigabe."""
    ablage = Ablage(tmp_path / "neu.sqlite")
    ablage.aufnehmen(stelle)  # Status 'neu', kein Entwurf vorhanden
    with TestClient(anwendung(profil, zugang, ablage)) as klient:
        antwort = klient.get("/")
        assert antwort.status_code == 200
        assert "KI-Spezialist" in antwort.text
    ablage.schliessen()


def test_ausdruecklich_gewaehlter_reiter_bleibt_leer(tmp_path, profil, zugang, stelle):
    ablage = Ablage(tmp_path / "neu2.sqlite")
    ablage.aufnehmen(stelle)
    with TestClient(anwendung(profil, zugang, ablage)) as klient:
        assert "KI-Spezialist" not in klient.get(f"/?status={ENTWURF}").text
    ablage.schliessen()

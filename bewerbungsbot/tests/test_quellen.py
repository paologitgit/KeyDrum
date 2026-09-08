"""Auswertung der Plattformantwort - gegen eine gespeicherte Beispielantwort."""

from __future__ import annotations

import json
from pathlib import Path

from bot.quellen.basis import email_finden, entdoppeln, erstes_feld, html_zu_text, pensum_finden
from bot.quellen.jobs_ch import JobsCh
from bot.modelle import Stelle

BEISPIEL = json.loads(
    (Path(__file__).parent / "fixtures" / "jobs_ch_suche.json").read_text(encoding="utf-8")
)


def test_trefferliste_wird_gefunden():
    assert len(JobsCh._eintraege(BEISPIEL)) == 3


def test_trefferliste_unter_anderem_schluessel():
    """Benennt die Plattform das Feld um, greift der naechste Kandidat."""
    assert len(JobsCh._eintraege({"results": BEISPIEL["documents"]})) == 3
    assert JobsCh._eintraege({"unbekannt": 1}) == []


def test_eintrag_wird_zu_stelle(profil):
    quelle = JobsCh(profil, pause=0)
    stelle = quelle._zu_stelle(BEISPIEL["documents"][0])
    assert stelle.titel.startswith("KI-Spezialist")
    assert stelle.firma == "Muster AG"
    assert stelle.ort == "Zürich"
    assert stelle.url == "https://www.jobs.ch/de/vacancies/detail/abc123/"
    assert stelle.kontakt_email == "jobs@muster.ch"
    assert stelle.pensum == "80-100%"
    assert "<p>" not in stelle.beschreibung


def test_absolute_url_bleibt_erhalten():
    assert JobsCh._url_bauen(BEISPIEL["documents"][1]).startswith("https://www.jobs.ch")


def test_url_aus_kennung_wenn_kein_link():
    assert JobsCh._url_bauen(BEISPIEL["documents"][2]).endswith("/ghi789/")


def test_erstes_feld_geht_durch_die_kandidaten():
    assert erstes_feld({"b": "zweiter"}, "a", "b") == "zweiter"
    assert erstes_feld({"company": {"name": "Muster AG"}}, "company.name") == "Muster AG"
    assert erstes_feld({"locations": [{"city": "Zug"}]}, "locations") == "Zug"
    assert erstes_feld({}, "a", standard="-") == "-"


def test_html_wird_zu_text():
    text = html_zu_text("<script>x=1</script><p>Erste Zeile</p><p>Zweite Zeile</p>")
    assert text == "Erste Zeile\nZweite Zeile"


def test_email_ueberspringt_unbrauchbare_adressen():
    assert email_finden("noreply@jobs.ch und bewerbung@muster.ch") == "bewerbung@muster.ch"
    assert email_finden("kein Kontakt angegeben") == ""


def test_pensum_erkennung():
    assert pensum_finden("Pensum 80-100%") == "80-100%"
    assert pensum_finden("100 % Anstellung") == "100%"
    assert pensum_finden("keine Angabe") == ""


def test_entdoppeln_innerhalb_eines_laufs():
    a = Stelle(titel="KI", firma="Muster AG", ort="Zuerich", quelle="jobs.ch")
    b = Stelle(titel="ki", firma="muster ag", ort="ZUERICH", quelle="manuell")
    assert len(entdoppeln([a, b])) == 1

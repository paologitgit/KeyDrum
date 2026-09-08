"""Datenmodell und Ablage."""

from __future__ import annotations

from bot.db import Ablage
from bot.modelle import BEWERTET, ENTWURF, NEU, Bewertung, Stelle


def test_fingerabdruck_ignoriert_schreibweise():
    a = Stelle(titel="KI-Spezialist", firma="Muster AG", ort="Zuerich")
    b = Stelle(titel="  ki-spezialist ", firma="MUSTER AG", ort="zuerich")
    assert a.fingerabdruck == b.fingerabdruck


def test_fingerabdruck_unterscheidet_firmen():
    a = Stelle(titel="KI-Spezialist", firma="Muster AG")
    b = Stelle(titel="KI-Spezialist", firma="Andere AG")
    assert a.fingerabdruck != b.fingerabdruck


def test_bewerbungsweg():
    assert Stelle(titel="x", firma="y", kontakt_email="a@b.ch").bewerbungsweg == "email"
    assert Stelle(titel="x", firma="y").bewerbungsweg == "portal"


def test_dieselbe_stelle_wird_nur_einmal_angelegt(tmp_path, stelle):
    with Ablage(tmp_path / "test.sqlite") as ablage:
        erste_id, neu = ablage.aufnehmen(stelle)
        assert neu is True
        zweite_id, nochmal_neu = ablage.aufnehmen(stelle)
        assert nochmal_neu is False
        assert erste_id == zweite_id
        assert len(ablage.alle()) == 1


def test_bewertung_setzt_status_und_verlauf(tmp_path, stelle):
    with Ablage(tmp_path / "test.sqlite") as ablage:
        stelle_id, _ = ablage.aufnehmen(stelle)
        ablage.bewertung_speichern(
            stelle_id, Bewertung(82, "Passt gut.", ["KI"], ["Fuehrung"]), BEWERTET
        )
        zeile = ablage.holen(stelle_id)
        assert zeile["status"] == BEWERTET
        assert zeile["punktzahl"] == 82
        assert "KI" in zeile["staerken"]
        assert [e["art"] for e in ablage.ereignisse(stelle_id)] == ["gefunden", "bewertet"]


def test_entwurf_und_versand(tmp_path, stelle):
    with Ablage(tmp_path / "test.sqlite") as ablage:
        stelle_id, _ = ablage.aufnehmen(stelle)
        ablage.entwurf_speichern(stelle_id, "Bewerbung als KI-Spezialist", "Sehr geehrte ...")
        assert ablage.holen(stelle_id)["status"] == ENTWURF
        assert ablage.heute_versendet() == 0

        ablage.versand_vermerken(stelle_id, "bewerbung@muster.ch", trockenlauf=False)
        assert ablage.holen(stelle_id)["status"] == "versendet"
        assert ablage.heute_versendet() == 1


def test_unbekanntes_feld_wird_abgewiesen(tmp_path, stelle):
    with Ablage(tmp_path / "test.sqlite") as ablage:
        stelle_id, _ = ablage.aufnehmen(stelle)
        try:
            ablage.aktualisieren(stelle_id, gibtsnicht="x")
        except ValueError as fehler:
            assert "gibtsnicht" in str(fehler)
        else:
            raise AssertionError("Es haette ein ValueError kommen muessen.")


def test_zaehlung(tmp_path, stelle):
    with Ablage(tmp_path / "test.sqlite") as ablage:
        ablage.aufnehmen(stelle)
        ablage.aufnehmen(Stelle(titel="Andere", firma="Zweite AG"))
        assert ablage.zaehlung() == {NEU: 2}

"""Vorfilter - die Stufe, die ohne Modellaufruf entscheidet."""

from __future__ import annotations

from bot.matching import grobfilter, ist_remote, ort_passt, vorfilter
from bot.modelle import Stelle


def test_passende_stelle_kommt_durch(profil, stelle):
    durch, grund = vorfilter(stelle, profil)
    assert durch is True and grund == ""


def test_ausschlussbegriff_im_titel(profil):
    stelle = Stelle(titel="Praktikum KI", firma="Muster AG", ort="Zuerich",
                    beschreibung="KI und Automatisierung")
    durch, grund = vorfilter(stelle, profil)
    assert durch is False and "Praktikum" in grund


def test_ort_ausserhalb_wird_aussortiert(profil):
    stelle = Stelle(titel="KI-Spezialist", firma="Muster AG", ort="Genf",
                    beschreibung="KI und Automatisierung")
    durch, grund = vorfilter(stelle, profil)
    assert durch is False and "Suchgebiet" in grund


def test_remote_gleicht_entfernten_ort_aus(profil):
    stelle = Stelle(titel="KI-Spezialist", firma="Muster AG", ort="Genf",
                    beschreibung="KI und Automatisierung, Homeoffice moeglich")
    assert ist_remote(stelle) is True
    assert ort_passt(stelle, profil) is True
    assert vorfilter(stelle, profil)[0] is True


def test_nur_remote_verlangt_remote(profil):
    profil.suche["nur_remote"] = True
    vor_ort = Stelle(titel="KI-Spezialist", firma="Muster AG", ort="Zuerich",
                     beschreibung="KI und Automatisierung vor Ort")
    assert vorfilter(vor_ort, profil)[0] is False


def test_ohne_fachlichen_bezug_kein_modellaufruf(profil):
    stelle = Stelle(titel="Sachbearbeiter Buchhaltung", firma="Muster AG", ort="Zuerich",
                    beschreibung="Debitoren und Kreditoren.")
    durch, grund = vorfilter(stelle, profil)
    assert durch is False and "fachlicher Bezug" in grund


def test_grobfilter_laesst_stellen_ohne_ortsangabe_durch(profil):
    """Ohne Ort in der Trefferliste entscheidet erst die Detailseite."""
    stelle = Stelle(titel="KI-Spezialist", firma="Muster AG", ort="")
    assert grobfilter(stelle, profil)[0] is True


def test_grobfilter_greift_vor_dem_nachladen(profil):
    stelle = Stelle(titel="Lehrstelle Informatik", firma="Muster AG", ort="Zuerich")
    assert grobfilter(stelle, profil)[0] is False


def test_umlaut_und_umschrift_gelten_als_gleich(profil):
    """Das Profil schreibt 'Zuerich', die Plattform liefert 'Zürich'."""
    stelle = Stelle(titel="KI-Spezialist", firma="Muster AG", ort="Zürich",
                    beschreibung="KI und Automatisierung")
    assert ort_passt(stelle, profil) is True
    assert vorfilter(stelle, profil)[0] is True


def test_umschrift_im_profil_trifft_umlaut_im_titel(profil):
    profil.suche["ausschluss_stichworte"] = ["Temporaer"]
    stelle = Stelle(titel="KI-Spezialist temporär", firma="Muster AG", ort="Zürich",
                    beschreibung="KI und Automatisierung")
    durch, grund = vorfilter(stelle, profil)
    assert durch is False and "Temporaer" in grund


def test_umlaut_im_profil_trifft_umschrift_der_plattform(profil):
    profil.suche["erlaubte_orte"] = ["Zürich"]
    stelle = Stelle(titel="KI-Spezialist", firma="Muster AG", ort="Zuerich",
                    beschreibung="KI und Automatisierung")
    assert ort_passt(stelle, profil) is True


def test_muss_stichwort_mit_umlaut(profil):
    profil.bewertung["muss_stichworte"] = ["Kuenstliche"]
    stelle = Stelle(titel="Fachperson Daten", firma="Muster AG", ort="Zürich",
                    beschreibung="Wir arbeiten mit Künstlicher Intelligenz.")
    assert vorfilter(stelle, profil)[0] is True


def test_remote_mit_umlaut(profil):
    stelle = Stelle(titel="KI-Spezialist", firma="Muster AG", ort="Genf",
                    beschreibung="KI und Automatisierung, ortsunabhängig moeglich")
    assert ist_remote(stelle) is True

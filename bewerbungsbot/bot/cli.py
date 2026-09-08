"""Kommandozeile des Bewerbungsbots.

    python -m bot.cli pruefen     Konfiguration und Zugaenge kontrollieren
    python -m bot.cli suchen      Stellen suchen und ablegen
    python -m bot.cli bewerten    neue Stellen vom Modell beurteilen lassen
    python -m bot.cli entwerfen   Anschreiben fuer passende Stellen verfassen
    python -m bot.cli lauf        alle drei Schritte nacheinander
    python -m bot.cli web         Dashboard starten
    python -m bot.cli stand       Kurzuebersicht auf der Konsole
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .db import Ablage
from .klient import klient
from .konfig import KonfigFehler, Profil, Zugang
from .modelle import STATUS_BESCHRIFTUNG
from .quellen import VERFUEGBAR


def _laden(argumente: argparse.Namespace) -> tuple[Profil, Zugang, Ablage]:
    profil = Profil.laden(argumente.profil)
    zugang = Zugang.laden()
    ablage = Ablage(argumente.db)
    return profil, zugang, ablage


def befehl_pruefen(argumente: argparse.Namespace) -> int:
    """Sagt vor dem ersten Lauf, was noch fehlt."""
    profil, zugang, ablage = _laden(argumente)
    zeilen = [f"Profil:            {profil.pfad}", f"Datenbank:         {ablage.pfad}",
              f"Name:              {profil.voller_name or 'FEHLT'}",
              f"Adresse:           {profil.person.get('email') or 'FEHLT'}",
              f"Schwelle:          {profil.schwelle} Punkte",
              f"Quellen:           {', '.join(VERFUEGBAR)}"]

    probleme: list[str] = []
    if not profil.voller_name:
        probleme.append("Im Profil fehlt der Name.")
    if not profil.person.get("email"):
        probleme.append("Im Profil fehlt Ihre E-Mail-Adresse.")
    if not zugang.anthropic_key:
        probleme.append("ANTHROPIC_API_KEY ist nicht gesetzt - Bewertung und Anschreiben gehen nicht.")
    fehlend = profil.fehlende_anhaenge()
    if fehlend:
        probleme.append("Diese Anhaenge fehlen: " + ", ".join(p.name for p in fehlend))
    if zugang.trockenlauf:
        zeilen.append("Versand:           Probelauf (es geht nichts hinaus)")
    elif not zugang.smtp_bereit():
        probleme.append("Der Probelauf ist aus, aber die SMTP-Zugangsdaten sind unvollstaendig.")
    else:
        zeilen.append(f"Versand:           scharf ueber {zugang.smtp_host}")

    print("\n".join(zeilen))
    if probleme:
        print("\nOffen:")
        for problem in probleme:
            print(f"  - {problem}")
        return 1
    print("\nAlles bereit.")
    return 0


def befehl_suchen(argumente: argparse.Namespace) -> int:
    from . import pipeline
    profil, _, ablage = _laden(argumente)
    zahlen = pipeline.suchen(
        profil, ablage,
        quellen_namen=argumente.quellen,
        rohdaten_ablegen=argumente.rohdaten,
    )
    print(
        f"\n{zahlen['gefunden']} Inserate gesichtet, {zahlen['bekannt']} bereits bekannt, "
        f"{zahlen['aussortiert']} aussortiert, {zahlen['neu']} neu zur Bewertung."
    )
    return 0


def befehl_bewerten(argumente: argparse.Namespace) -> int:
    from . import pipeline
    profil, zugang, ablage = _laden(argumente)
    zahlen = pipeline.bewerten(profil, ablage, klient(zugang.anthropic_key), argumente.grenze)
    print(f"\n{zahlen['bewertet']} bewertet, davon {zahlen['passend']} ueber der Schwelle.")
    return 0


def befehl_entwerfen(argumente: argparse.Namespace) -> int:
    from . import pipeline
    profil, zugang, ablage = _laden(argumente)
    zahlen = pipeline.entwerfen(profil, ablage, klient(zugang.anthropic_key), argumente.grenze)
    print(f"\n{zahlen['entworfen']} Anschreiben verfasst, {zahlen['fehler']} fehlgeschlagen.")
    return 0


def befehl_lauf(argumente: argparse.Namespace) -> int:
    from . import pipeline
    profil, zugang, ablage = _laden(argumente)
    ergebnis = pipeline.lauf(profil, ablage, argumente.quellen, klient(zugang.anthropic_key))
    print(
        f"\nFertig. {ergebnis['wartet_auf_freigabe']} Bewerbungen warten auf Ihre Freigabe."
        "\nOeffnen Sie das Dashboard mit: python -m bot.cli web"
    )
    return 0


def befehl_stand(argumente: argparse.Namespace) -> int:
    _, _, ablage = _laden(argumente)
    zaehlung = ablage.zaehlung()
    if not zaehlung:
        print("Noch keine Stellen erfasst.")
        return 0
    for status, beschriftung in STATUS_BESCHRIFTUNG.items():
        print(f"{beschriftung:22s} {zaehlung.get(status, 0):4d}")
    print(f"\nHeute versendet: {ablage.heute_versendet()}")
    return 0


def befehl_web(argumente: argparse.Namespace) -> int:
    import uvicorn
    from .web.app import anwendung

    profil, zugang, ablage = _laden(argumente)
    print(f"Dashboard: http://{argumente.host}:{argumente.port}")
    if zugang.trockenlauf:
        print("Hinweis: Probelauf aktiv, es wird nichts wirklich versendet.")
    uvicorn.run(anwendung(profil, zugang, ablage), host=argumente.host, port=argumente.port)
    return 0


def parser_bauen() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bewerbungsbot",
        description="Sucht Stellen, bewertet sie, verfasst Anschreiben und versendet nach Freigabe.",
    )
    parser.add_argument("--profil", type=Path, default=None, help="Pfad zu profil.yaml")
    parser.add_argument("--db", type=Path, default=None, help="Pfad zur SQLite-Datei")
    unter = parser.add_subparsers(dest="befehl", required=True)

    unter.add_parser("pruefen", help="Konfiguration kontrollieren").set_defaults(funktion=befehl_pruefen)

    p_suchen = unter.add_parser("suchen", help="Stellen suchen")
    p_suchen.add_argument("--quellen", nargs="+", default=None, choices=list(VERFUEGBAR))
    p_suchen.add_argument("--rohdaten", action="store_true",
                          help="Antworten der Plattform mitschreiben (zur Fehlersuche)")
    p_suchen.set_defaults(funktion=befehl_suchen)

    p_bewerten = unter.add_parser("bewerten", help="Neue Stellen bewerten lassen")
    p_bewerten.add_argument("--grenze", type=int, default=None)
    p_bewerten.set_defaults(funktion=befehl_bewerten)

    p_entwerfen = unter.add_parser("entwerfen", help="Anschreiben verfassen")
    p_entwerfen.add_argument("--grenze", type=int, default=None)
    p_entwerfen.set_defaults(funktion=befehl_entwerfen)

    p_lauf = unter.add_parser("lauf", help="Suchen, bewerten und entwerfen in einem Zug")
    p_lauf.add_argument("--quellen", nargs="+", default=None, choices=list(VERFUEGBAR))
    p_lauf.set_defaults(funktion=befehl_lauf)

    unter.add_parser("stand", help="Kurzuebersicht").set_defaults(funktion=befehl_stand)

    p_web = unter.add_parser("web", help="Dashboard starten")
    p_web.add_argument("--host", default="127.0.0.1")
    p_web.add_argument("--port", type=int, default=8000)
    p_web.set_defaults(funktion=befehl_web)

    return parser


def main(argv: list[str] | None = None) -> int:
    argumente = parser_bauen().parse_args(argv)
    try:
        return int(argumente.funktion(argumente))
    except KonfigFehler as fehler:
        print(f"Konfigurationsfehler: {fehler}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

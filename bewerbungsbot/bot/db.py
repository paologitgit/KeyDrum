"""SQLite-Ablage fuer gefundene Stellen, Bewertungen, Anschreiben und Versandprotokoll."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .konfig import WURZEL
from .modelle import ANTWORT, ENTWURF, NEU, VERSENDET, Bewertung, Stelle, jetzt

STANDARD_DB = WURZEL / "bewerbungen.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS stellen (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerabdruck   TEXT NOT NULL UNIQUE,
    quelle          TEXT,
    extern_id       TEXT,
    titel           TEXT NOT NULL,
    firma           TEXT,
    ort             TEXT,
    pensum          TEXT,
    url             TEXT,
    beschreibung    TEXT,
    kontakt_email   TEXT,
    kontakt_name    TEXT,
    bewerbungsweg   TEXT,
    veroeffentlicht TEXT,
    gefunden_am     TEXT,
    status          TEXT NOT NULL DEFAULT 'neu',
    punktzahl       INTEGER,
    begruendung     TEXT,
    staerken        TEXT,
    luecken         TEXT,
    betreff         TEXT,
    anschreiben     TEXT,
    anschreiben_pdf TEXT,
    empfaenger      TEXT,
    versendet_am    TEXT,
    fehler          TEXT,
    notiz           TEXT
);

CREATE TABLE IF NOT EXISTS ereignisse (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    stelle_id INTEGER NOT NULL REFERENCES stellen(id) ON DELETE CASCADE,
    zeit      TEXT NOT NULL,
    art       TEXT NOT NULL,
    text      TEXT
);

CREATE INDEX IF NOT EXISTS idx_stellen_status ON stellen(status);
CREATE INDEX IF NOT EXISTS idx_ereignisse_stelle ON ereignisse(stelle_id);
"""


class Ablage:
    """Duenne Schicht ueber SQLite. Bewusst ohne ORM - das Schema ist klein."""

    def __init__(self, pfad: Path | str | None = None) -> None:
        self.pfad = Path(pfad) if pfad else STANDARD_DB
        self.verbindung = sqlite3.connect(self.pfad, check_same_thread=False)
        self.verbindung.row_factory = sqlite3.Row
        self.verbindung.execute("PRAGMA foreign_keys = ON")
        self.verbindung.executescript(SCHEMA)
        self.verbindung.commit()

    def schliessen(self) -> None:
        self.verbindung.close()

    def __enter__(self) -> "Ablage":
        return self

    def __exit__(self, *_: object) -> None:
        self.schliessen()

    # -- Schreiben ----------------------------------------------------------

    def aufnehmen(self, stelle: Stelle) -> tuple[int, bool]:
        """Legt eine Stelle an. Rueckgabe: (id, neu_angelegt).

        Ist der Fingerabdruck bereits vorhanden, bleibt der bestehende Eintrag
        unveraendert - eine bereits versendete Bewerbung darf nicht durch einen
        erneuten Fund zurueckgesetzt werden.
        """
        vorhanden = self.verbindung.execute(
            "SELECT id FROM stellen WHERE fingerabdruck = ?", (stelle.fingerabdruck,)
        ).fetchone()
        if vorhanden:
            return int(vorhanden["id"]), False

        cursor = self.verbindung.execute(
            """
            INSERT INTO stellen (fingerabdruck, quelle, extern_id, titel, firma, ort,
                                 pensum, url, beschreibung, kontakt_email, kontakt_name,
                                 bewerbungsweg, veroeffentlicht, gefunden_am, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                stelle.fingerabdruck, stelle.quelle, stelle.extern_id, stelle.titel,
                stelle.firma, stelle.ort, stelle.pensum, stelle.url, stelle.beschreibung,
                stelle.kontakt_email, stelle.kontakt_name, stelle.bewerbungsweg,
                stelle.veroeffentlicht, jetzt(), NEU,
            ),
        )
        self.verbindung.commit()
        stelle_id = int(cursor.lastrowid)
        self.ereignis(stelle_id, "gefunden", f"{stelle.quelle}: {stelle.kurz()}")
        return stelle_id, True

    def bewertung_speichern(self, stelle_id: int, bewertung: Bewertung, status: str) -> None:
        self.verbindung.execute(
            """
            UPDATE stellen
               SET punktzahl = ?, begruendung = ?, staerken = ?, luecken = ?, status = ?
             WHERE id = ?
            """,
            (
                bewertung.punktzahl, bewertung.begruendung,
                json.dumps(bewertung.staerken, ensure_ascii=False),
                json.dumps(bewertung.luecken, ensure_ascii=False),
                status, stelle_id,
            ),
        )
        self.verbindung.commit()
        self.ereignis(stelle_id, "bewertet", f"{bewertung.punktzahl} Punkte: {bewertung.begruendung}")

    def entwurf_speichern(
        self, stelle_id: int, betreff: str, text: str,
        pdf_pfad: str | None = None, empfaenger: str | None = None,
    ) -> None:
        felder = {"betreff": betreff, "anschreiben": text, "status": ENTWURF}
        if pdf_pfad is not None:
            felder["anschreiben_pdf"] = pdf_pfad
        if empfaenger is not None:
            felder["empfaenger"] = empfaenger
        self.aktualisieren(stelle_id, **felder)
        self.ereignis(stelle_id, "entwurf", betreff)

    def versand_vermerken(self, stelle_id: int, empfaenger: str, trockenlauf: bool) -> None:
        self.aktualisieren(
            stelle_id, status=VERSENDET, versendet_am=jetzt(),
            empfaenger=empfaenger, fehler=None,
        )
        vermerk = "Probelauf (nicht wirklich versendet)" if trockenlauf else "versendet"
        self.ereignis(stelle_id, "versand", f"{vermerk} an {empfaenger}")

    def fehler_vermerken(self, stelle_id: int, meldung: str) -> None:
        self.aktualisieren(stelle_id, status="fehler", fehler=meldung)
        self.ereignis(stelle_id, "fehler", meldung)

    def aktualisieren(self, stelle_id: int, **felder: Any) -> None:
        if not felder:
            return
        erlaubt = {
            "titel", "firma", "ort", "pensum", "url", "beschreibung", "kontakt_email",
            "kontakt_name", "bewerbungsweg", "status", "punktzahl", "begruendung",
            "betreff", "anschreiben", "anschreiben_pdf", "empfaenger", "versendet_am",
            "fehler", "notiz", "staerken", "luecken",
        }
        unbekannt = set(felder) - erlaubt
        if unbekannt:
            raise ValueError(f"Unbekannte Felder: {', '.join(sorted(unbekannt))}")
        satz = ", ".join(f"{k} = ?" for k in felder)
        self.verbindung.execute(
            f"UPDATE stellen SET {satz} WHERE id = ?", (*felder.values(), stelle_id)
        )
        self.verbindung.commit()

    def ereignis(self, stelle_id: int, art: str, text: str = "") -> None:
        self.verbindung.execute(
            "INSERT INTO ereignisse (stelle_id, zeit, art, text) VALUES (?,?,?,?)",
            (stelle_id, jetzt(), art, text),
        )
        self.verbindung.commit()

    # -- Lesen --------------------------------------------------------------

    def holen(self, stelle_id: int) -> sqlite3.Row | None:
        return self.verbindung.execute(
            "SELECT * FROM stellen WHERE id = ?", (stelle_id,)
        ).fetchone()

    def nach_status(self, status: str | Iterable[str]) -> list[sqlite3.Row]:
        werte = [status] if isinstance(status, str) else list(status)
        platzhalter = ",".join("?" for _ in werte)
        return self.verbindung.execute(
            f"""SELECT * FROM stellen WHERE status IN ({platzhalter})
                ORDER BY COALESCE(punktzahl, -1) DESC, id DESC""",
            werte,
        ).fetchall()

    def alle(self, grenze: int = 500) -> list[sqlite3.Row]:
        return self.verbindung.execute(
            """SELECT * FROM stellen
               ORDER BY COALESCE(punktzahl, -1) DESC, id DESC LIMIT ?""",
            (grenze,),
        ).fetchall()

    def ereignisse(self, stelle_id: int) -> list[sqlite3.Row]:
        return self.verbindung.execute(
            "SELECT * FROM ereignisse WHERE stelle_id = ? ORDER BY id",
            (stelle_id,),
        ).fetchall()

    def zaehlung(self) -> dict[str, int]:
        zeilen = self.verbindung.execute(
            "SELECT status, COUNT(*) AS anzahl FROM stellen GROUP BY status"
        ).fetchall()
        return {z["status"]: z["anzahl"] for z in zeilen}

    def heute_versendet(self) -> int:
        """Zaehlt die heute versendeten Bewerbungen fuer das Tageslimit."""
        heute = jetzt()[:10]
        zeile = self.verbindung.execute(
            "SELECT COUNT(*) AS anzahl FROM stellen WHERE status IN (?,?) AND versendet_am LIKE ?",
            (VERSENDET, ANTWORT, f"{heute}%"),
        ).fetchone()
        return int(zeile["anzahl"])

    def kennt(self, fingerabdruck: str) -> bool:
        return self.verbindung.execute(
            "SELECT 1 FROM stellen WHERE fingerabdruck = ?", (fingerabdruck,)
        ).fetchone() is not None

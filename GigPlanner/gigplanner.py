# -*- coding: utf-8 -*-
"""
GigPlanner - ein kleines Kommandozeilen-Tool, um Gigs zu organisieren.

Benoetigt nur die Python-Standardbibliothek (Python 3.7+).

Beispiele:
    python gigplanner.py add "Stadtfest" --datum 2026-08-15 --ort "Marktplatz, Ulm" --zeit 20:00 --gage 400
    python gigplanner.py list
    python gigplanner.py list --status bestaetigt
    python gigplanner.py next
    python gigplanner.py show 1
    python gigplanner.py status 1 bestaetigt
    python gigplanner.py edit 1 --gage 500 --notizen "PA vorhanden, 2x45 min"
    python gigplanner.py delete 1
    python gigplanner.py export gigs.ics
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

DATEIPFAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gigs.json")

STATUS_WERTE = ["angefragt", "bestaetigt", "gespielt", "abgesagt"]

STATUS_SYMBOL = {
    "angefragt": "?",
    "bestaetigt": "+",
    "gespielt": "x",
    "abgesagt": "-",
}


# ---------------------------------------------------------------- Daten I/O

def lade_gigs(pfad):
    if not os.path.exists(pfad):
        return []
    with open(pfad, "r", encoding="utf-8") as f:
        return json.load(f)


def speichere_gigs(pfad, gigs):
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(gigs, f, ensure_ascii=False, indent=2)
        f.write("\n")


def neue_id(gigs):
    return max((g["id"] for g in gigs), default=0) + 1


def finde_gig(gigs, gig_id):
    for g in gigs:
        if g["id"] == gig_id:
            return g
    sys.exit("Fehler: Kein Gig mit ID %d gefunden. 'list' zeigt alle Gigs." % gig_id)


# ------------------------------------------------------------- Hilfsformate

def pruefe_datum(text):
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        sys.exit("Fehler: Datum '%s' ist ungueltig, bitte als JJJJ-MM-TT angeben (z.B. 2026-08-15)." % text)
    return text


def pruefe_zeit(text):
    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        sys.exit("Fehler: Uhrzeit '%s' ist ungueltig, bitte als HH:MM angeben (z.B. 20:00)." % text)
    return text


def gig_datetime(gig):
    zeit = gig.get("zeit") or "00:00"
    return datetime.strptime(gig["datum"] + " " + zeit, "%Y-%m-%d %H:%M")


def sortiert_nach_datum(gigs):
    return sorted(gigs, key=gig_datetime)


def datum_schoen(gig):
    dt = gig_datetime(gig)
    wochentage = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    text = "%s %s" % (wochentage[dt.weekday()], dt.strftime("%d.%m.%Y"))
    if gig.get("zeit"):
        text += " " + gig["zeit"]
    return text


# ------------------------------------------------------------------ Ausgabe

def zeile(gig):
    teile = [
        "[%s]" % STATUS_SYMBOL[gig["status"]],
        "#%d" % gig["id"],
        datum_schoen(gig),
        "-",
        gig["titel"],
    ]
    if gig.get("ort"):
        teile.append("@ " + gig["ort"])
    if gig.get("gage"):
        teile.append("(%s EUR)" % gig["gage"])
    return "  ".join(teile)


def drucke_liste(gigs, ueberschrift):
    print(ueberschrift)
    print("-" * len(ueberschrift))
    if not gigs:
        print("(keine Gigs)")
        return
    for g in sortiert_nach_datum(gigs):
        print(zeile(g))
    print()
    print("Legende: [?] angefragt  [+] bestaetigt  [x] gespielt  [-] abgesagt")


# ------------------------------------------------------------------ Befehle

def cmd_add(args, gigs, pfad):
    gig = {
        "id": neue_id(gigs),
        "titel": args.titel,
        "datum": pruefe_datum(args.datum),
        "zeit": pruefe_zeit(args.zeit) if args.zeit else "",
        "ort": args.ort or "",
        "gage": args.gage or "",
        "kontakt": args.kontakt or "",
        "setlist": args.setlist or "",
        "notizen": args.notizen or "",
        "status": args.status,
    }
    gigs.append(gig)
    speichere_gigs(pfad, gigs)
    print("Gig #%d angelegt:" % gig["id"])
    print(zeile(gig))


def cmd_list(args, gigs, pfad):
    auswahl = gigs
    titel = "Alle Gigs"
    if args.status:
        auswahl = [g for g in auswahl if g["status"] == args.status]
        titel = "Gigs mit Status '%s'" % args.status
    if args.kommend:
        jetzt = datetime.now()
        auswahl = [g for g in auswahl if gig_datetime(g) >= jetzt]
        titel += " (nur kommende)"
    drucke_liste(auswahl, titel)


def cmd_next(args, gigs, pfad):
    jetzt = datetime.now()
    kommende = [
        g for g in sortiert_nach_datum(gigs)
        if gig_datetime(g) >= jetzt and g["status"] in ("angefragt", "bestaetigt")
    ]
    if not kommende:
        print("Kein kommender Gig eingetragen.")
        return
    g = kommende[0]
    tage = (gig_datetime(g).date() - jetzt.date()).days
    print("Naechster Gig (in %d Tag%s):" % (tage, "" if tage == 1 else "en"))
    zeige_details(g)


def zeige_details(gig):
    felder = [
        ("Titel", gig["titel"]),
        ("Termin", datum_schoen(gig)),
        ("Ort", gig.get("ort") or "-"),
        ("Status", gig["status"]),
        ("Gage", (gig.get("gage") + " EUR") if gig.get("gage") else "-"),
        ("Kontakt", gig.get("kontakt") or "-"),
        ("Setlist", gig.get("setlist") or "-"),
        ("Notizen", gig.get("notizen") or "-"),
    ]
    print("Gig #%d" % gig["id"])
    for name, wert in felder:
        print("  %-8s %s" % (name + ":", wert))


def cmd_show(args, gigs, pfad):
    zeige_details(finde_gig(gigs, args.id))


def cmd_status(args, gigs, pfad):
    gig = finde_gig(gigs, args.id)
    gig["status"] = args.status
    speichere_gigs(pfad, gigs)
    print("Gig #%d ist jetzt '%s'." % (gig["id"], gig["status"]))


def cmd_edit(args, gigs, pfad):
    gig = finde_gig(gigs, args.id)
    geaendert = []
    if args.titel is not None:
        gig["titel"] = args.titel
        geaendert.append("titel")
    if args.datum is not None:
        gig["datum"] = pruefe_datum(args.datum)
        geaendert.append("datum")
    if args.zeit is not None:
        gig["zeit"] = pruefe_zeit(args.zeit) if args.zeit else ""
        geaendert.append("zeit")
    if args.ort is not None:
        gig["ort"] = args.ort
        geaendert.append("ort")
    if args.gage is not None:
        gig["gage"] = args.gage
        geaendert.append("gage")
    if args.kontakt is not None:
        gig["kontakt"] = args.kontakt
        geaendert.append("kontakt")
    if args.setlist is not None:
        gig["setlist"] = args.setlist
        geaendert.append("setlist")
    if args.notizen is not None:
        gig["notizen"] = args.notizen
        geaendert.append("notizen")
    if not geaendert:
        print("Nichts geaendert - bitte mindestens ein Feld angeben (siehe 'edit --help').")
        return
    speichere_gigs(pfad, gigs)
    print("Gig #%d aktualisiert (%s)." % (gig["id"], ", ".join(geaendert)))
    zeige_details(gig)


def cmd_delete(args, gigs, pfad):
    gig = finde_gig(gigs, args.id)
    gigs.remove(gig)
    speichere_gigs(pfad, gigs)
    print("Gig #%d ('%s') geloescht." % (gig["id"], gig["titel"]))


def cmd_export(args, gigs, pfad):
    """Exportiert alle nicht abgesagten Gigs als iCalendar-Datei (.ics)."""
    def ics_escape(text):
        return (
            text.replace("\\", "\\\\")
            .replace(";", "\\;")
            .replace(",", "\\,")
            .replace("\n", "\\n")
        )

    zeilen = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//KeyDrum//GigPlanner//DE",
    ]
    stempel = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    anzahl = 0
    for g in sortiert_nach_datum(gigs):
        if g["status"] == "abgesagt":
            continue
        anzahl += 1
        zeilen.append("BEGIN:VEVENT")
        zeilen.append("UID:gig-%d@keydrum-gigplanner" % g["id"])
        zeilen.append("DTSTAMP:" + stempel)
        if g.get("zeit"):
            start = gig_datetime(g)
            ende = start + timedelta(hours=2)
            zeilen.append("DTSTART:" + start.strftime("%Y%m%dT%H%M%S"))
            zeilen.append("DTEND:" + ende.strftime("%Y%m%dT%H%M%S"))
        else:
            zeilen.append("DTSTART;VALUE=DATE:" + g["datum"].replace("-", ""))
        zeilen.append("SUMMARY:" + ics_escape(g["titel"]))
        if g.get("ort"):
            zeilen.append("LOCATION:" + ics_escape(g["ort"]))
        beschreibung = []
        if g.get("gage"):
            beschreibung.append("Gage: %s EUR" % g["gage"])
        if g.get("kontakt"):
            beschreibung.append("Kontakt: " + g["kontakt"])
        if g.get("notizen"):
            beschreibung.append(g["notizen"])
        if beschreibung:
            zeilen.append("DESCRIPTION:" + ics_escape("\n".join(beschreibung)))
        zeilen.append("END:VEVENT")
    zeilen.append("END:VCALENDAR")

    with open(args.datei, "w", encoding="utf-8") as f:
        f.write("\r\n".join(zeilen) + "\r\n")
    print("%d Gig(s) nach '%s' exportiert." % (anzahl, args.datei))


# --------------------------------------------------------------------- Main

def main():
    parser = argparse.ArgumentParser(
        prog="gigplanner",
        description="Gigs organisieren: anlegen, auflisten, bearbeiten, exportieren.",
    )
    parser.add_argument(
        "--file",
        default=DATEIPFAD,
        help="Pfad zur Datendatei (Standard: gigs.json neben dem Skript)",
    )
    sub = parser.add_subparsers(dest="befehl")

    p = sub.add_parser("add", help="Neuen Gig anlegen")
    p.add_argument("titel", help="Name des Gigs, z.B. 'Stadtfest'")
    p.add_argument("--datum", required=True, help="Datum als JJJJ-MM-TT")
    p.add_argument("--zeit", help="Uhrzeit als HH:MM")
    p.add_argument("--ort", help="Location / Adresse")
    p.add_argument("--gage", help="Gage in EUR")
    p.add_argument("--kontakt", help="Ansprechpartner (Name, Telefon, E-Mail)")
    p.add_argument("--setlist", help="Setlist oder Verweis darauf")
    p.add_argument("--notizen", help="Freitext-Notizen (Technik, Anfahrt, ...)")
    p.add_argument("--status", choices=STATUS_WERTE, default="angefragt",
                   help="Startstatus (Standard: angefragt)")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="Gigs auflisten")
    p.add_argument("--status", choices=STATUS_WERTE, help="Nur Gigs mit diesem Status")
    p.add_argument("--kommend", action="store_true", help="Nur Gigs ab heute")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("next", help="Naechsten anstehenden Gig anzeigen")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("show", help="Alle Details eines Gigs anzeigen")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("status", help="Status eines Gigs aendern")
    p.add_argument("id", type=int)
    p.add_argument("status", choices=STATUS_WERTE)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("edit", help="Felder eines Gigs aendern")
    p.add_argument("id", type=int)
    p.add_argument("--titel")
    p.add_argument("--datum", help="Datum als JJJJ-MM-TT")
    p.add_argument("--zeit", help="Uhrzeit als HH:MM ('' zum Loeschen)")
    p.add_argument("--ort")
    p.add_argument("--gage")
    p.add_argument("--kontakt")
    p.add_argument("--setlist")
    p.add_argument("--notizen")
    p.set_defaults(func=cmd_edit)

    p = sub.add_parser("delete", help="Gig loeschen")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("export", help="Gigs als Kalenderdatei (.ics) exportieren")
    p.add_argument("datei", nargs="?", default="gigs.ics", help="Zieldatei (Standard: gigs.ics)")
    p.set_defaults(func=cmd_export)

    args = parser.parse_args()
    if not args.befehl:
        parser.print_help()
        return

    gigs = lade_gigs(args.file)
    args.func(args, gigs, args.file)


if __name__ == "__main__":
    main()

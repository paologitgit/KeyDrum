GigPlanner - Gigs organisieren auf der Kommandozeile
====================================================

Ein kleines Tool, um Auftritte (Gigs) zu verwalten: Termine, Orte, Gagen,
Kontakte, Setlists und Status. Braucht nur Python 3 (Standardbibliothek,
kein pygame, keine Installation).

Die Daten werden in gigs.json neben dem Skript gespeichert
(anderer Ort: --file pfad/zu/datei.json vor dem Befehl angeben).


Schnellstart
------------

  # Gig anlegen (Status ist zunaechst "angefragt")
  python gigplanner.py add "Stadtfest" --datum 2026-08-15 --zeit 20:00 --ort "Marktplatz, Ulm" --gage 400

  # Alle Gigs anzeigen
  python gigplanner.py list

  # Nur kommende bzw. nur bestaetigte Gigs
  python gigplanner.py list --kommend
  python gigplanner.py list --status bestaetigt

  # Naechster anstehender Gig
  python gigplanner.py next

  # Details, Status aendern, bearbeiten, loeschen
  python gigplanner.py show 1
  python gigplanner.py status 1 bestaetigt
  python gigplanner.py edit 1 --gage 500 --notizen "PA vorhanden, 2x45 min"
  python gigplanner.py delete 1

  # Alle (nicht abgesagten) Gigs als Kalenderdatei exportieren
  python gigplanner.py export gigs.ics


Status-Werte
------------

  angefragt   - Anfrage laeuft, noch nicht fix     [?]
  bestaetigt  - Gig ist fix zugesagt               [+]
  gespielt    - Gig ist vorbei                     [x]
  abgesagt    - Gig findet nicht statt             [-]


Felder pro Gig
--------------

  titel    Name des Gigs (Pflicht)
  datum    JJJJ-MM-TT (Pflicht)
  zeit     HH:MM (optional)
  ort      Location / Adresse
  gage     Gage in EUR
  kontakt  Ansprechpartner (Name, Telefon, E-Mail)
  setlist  Setlist oder Verweis darauf
  notizen  Freitext (Technik, Anfahrt, Backline, ...)

Die Datei gigs.ics laesst sich in Google Kalender, Apple Kalender,
Outlook usw. importieren.

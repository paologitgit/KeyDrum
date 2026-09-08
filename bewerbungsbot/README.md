# Bewerbungsbot

Sucht Stellen auf jobs.ch, beurteilt sie, verfasst zu jeder passenden Stelle ein
eigenes Anschreiben und verschickt die Bewerbung – **erst nachdem Sie sie
freigegeben haben**.

Zielgruppe des Profils: Fachpersonen, die KI-Werkzeuge einführen, Abläufe
vereinfachen und Inhalte von der Anleitung bis zum Lehrmittel erstellen.

## Vor dem Start: drei Dinge, die Sie wissen sollten

1. **Die Portale untersagen automatisiertes Auslesen.** jobs.ch und Indeed
   schliessen das in ihren Nutzungsbedingungen aus. Das Tool fragt deshalb
   langsam und in kleinem Umfang ab und ist auf den privaten Eigenbedarf
   ausgelegt. Ein Anspruch auf Zugang entsteht daraus nicht: Die Plattform kann
   den Zugriff jederzeit sperren. Der Adapter `manuell` bleibt als Notausgang.
2. **Nichts geht ohne Ihre Freigabe hinaus.** Ab Werk läuft das Tool im
   Probelauf; die fertige Mail landet als Datei in `ausgabe/postausgang/`. Erst
   `TROCKENLAUF=0` in der `.env` schaltet den Versand scharf.
3. **Lesen Sie die ersten zehn Anschreiben Wort für Wort.** Das Modell hält sich
   an Ihr Profil, aber der Ton muss zu Ihnen passen. Erst wenn er stimmt, lohnt
   sich zügiges Freigeben.

## Einrichtung

```bash
cd bewerbungsbot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp config/profil.beispiel.yaml config/profil.yaml   # Ihre Daten eintragen
cp .env.beispiel .env                               # Schlüssel und Postausgang
cp ~/Dokumente/Lebenslauf.pdf dokumente/            # Anhänge ablegen

python -m bot.cli pruefen        # sagt Ihnen, was noch fehlt
```

`pruefen` endet mit Rückgabewert 1, solange etwas offen ist – so eignet es sich
auch als Vorstufe in einem geplanten Lauf.

## Täglicher Ablauf

```bash
python -m bot.cli lauf     # sucht, bewertet, verfasst Anschreiben
python -m bot.cli web      # Dashboard unter http://127.0.0.1:8000
```

Im Dashboard sehen Sie die Treffer nach Punktzahl sortiert, dazu die Begründung
des Modells. Auf der Detailseite können Sie Betreff, Empfänger und Anschreiben
bearbeiten; beim Speichern wird das PDF mit Ihrem Text neu gesetzt. Ein Klick auf
**Freigeben und senden** verschickt die Bewerbung mit Anschreiben und Anhängen.

Einzelne Schritte lassen sich auch getrennt aufrufen:

```bash
python -m bot.cli suchen --quellen jobs.ch
python -m bot.cli bewerten --grenze 20
python -m bot.cli entwerfen
python -m bot.cli stand
```

## Der erste echte Lauf gegen jobs.ch

Die Suchschnittstelle von jobs.ch ist nicht öffentlich dokumentiert; ihre
Feldnamen können sich ändern. Beim ersten Lauf prüfen Sie deshalb einmal, ob die
Zuordnung stimmt:

```bash
python -m bot.cli suchen --quellen jobs.ch --rohdaten
```

Die unveränderte Antwort der Plattform liegt danach unter
`ausgabe/rohdaten/`. Stimmen Titel, Firma und Ort in der Ausgabe nicht, passen
Sie die Namenskandidaten in `bot/quellen/jobs_ch.py` in der Tabelle `FELDER` an –
das ist die einzige Stelle, die dafür zuständig ist.

Findet die Suche nichts, benutzen Sie `config/manuelle_stellen.yaml`:

```yaml
- https://www.jobs.ch/de/vacancies/detail/12345/
- url: https://karriere.firma.ch/stelle/42
  firma: Firma AG
  email: bewerbung@firma.ch
```

## Aufbau

| Datei | Aufgabe |
|---|---|
| `config/profil.yaml` | Ihre Daten, Suchbegriffe, Region, Ton, Grenzen |
| `bot/quellen/` | ein Adapter pro Plattform, einheitliche Ausgabe |
| `bot/matching.py` | Vorfilter ohne Kosten, danach Bewertung durch das Modell |
| `bot/anschreiben.py` | verfasst den Brief zur konkreten Stelle |
| `bot/brief_pdf.py` | setzt ihn als Schweizer Geschäftsbrief |
| `bot/versand/` | E-Mail-Versand, im Probelauf nur als Datei |
| `bot/web/` | das Dashboard zur Freigabe |
| `bot/pipeline.py` | verbindet die Schritte |
| `bewerbungen.sqlite` | Stellen, Bewertungen, Anschreiben, Verlauf |

Der Ablauf spart bewusst Abfragen und Kosten: Aus der Trefferliste fliegt zuerst
alles raus, was schon am Titel oder Ort scheitert. Erst danach wird die
Detailseite geladen, erst danach bewertet das Modell, und ein Anschreiben
entsteht nur für Stellen über Ihrer Schwelle.

## Kosten

Pro Stelle fallen eine Bewertung (kurz, geringer Aufwand) und – nur bei
passenden Stellen – ein Anschreiben an. Bei 40 gesichteten und 5 passenden
Stellen pro Tag liegt das im Bereich weniger Franken pro Monat. Die Modelle
stellen Sie im Profil unter `bewertung.modell` und `anschreiben.modell` ein.

## Tests

```bash
python -m pytest tests -q
```

Die Tests laufen ohne Netz und ohne Modellzugriff: Die Auswertung der
Plattformantwort prüft eine gespeicherte Beispieldatei, der Versand läuft im
Probelauf, das Dashboard wird über einen Testklienten bedient.

## Was noch nicht drin ist

- **ch.indeed.com** – als zweiter Adapter vorgesehen; Indeed wehrt sich
  technisch stärker gegen automatisierte Zugriffe, das braucht Browser-Steuerung.
- **Bewerbung über das jobs.ch-Konto** – Formulare im eingeloggten Bereich
  ausfüllen. Bequem, aber mit dem höchsten Risiko für Ihr Konto; deshalb
  bewusst nicht im ersten Schritt.
- **Antworten verfolgen** – Postfachabgleich, der Zu- und Absagen automatisch
  dem richtigen Eintrag zuordnet.
- **Nachfassen** – Erinnerung, wenn zwei Wochen ohne Antwort vergangen sind.

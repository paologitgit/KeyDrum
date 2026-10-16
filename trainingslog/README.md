# Trainingslog

Ein Trainingstagebuch für das Smartphone: Pro Training werden Übungen, Sätze und Gewichte erfasst. Beim Erfassen sehen Sie jeweils, was Sie beim letzten Mal gemacht haben.

## Funktionen

- **Neues Training:** Datum wählen (vorausgefüllt mit heute) und „Starten“ tippen. Bei heutigen Trainings wird die Startzeit automatisch gesetzt.
- **Trainingsdauer:** Unten im Training „Training beendet“ tippen. Start und Ende lassen sich oben im Training korrigieren; die Dauer erscheint auch in der Trainingsliste.
- **Länger nicht gemacht:** Übungen, die in keinem der letzten 5 Trainings vorkamen, erhalten einen roten Balken mit dem Datum der letzten Ausführung. Oben im Training stehen sie zusätzlich als Liste (antippen springt zur Übung). Die Startseite zeigt die letzten 5 Trainings als Raster.
- **Übungen:** Die Liste ist zu Beginn mit diesen Übungen gefüllt: Deadlift, Latzug, Sitting Row, Pull-up, Bankdrücken, Bizeps, Schulter seitlich, Rücken, Butterfly reverse.
- **Sätze erfassen:** Gewicht (Komma oder Punkt), Wiederholungen optional, dann „+ Satz“. Das Gewicht vom letzten Satz ist bereits eingetragen.
- **Letztes Training:** Jede Übung zeigt die Sätze aus dem letzten Training, in dem sie vorkam. Mit „Sätze übernehmen“ wird alles auf einmal kopiert.
- **Neue Übungen** lassen sich während des Trainings unten auf der Seite hinzufügen. Dabei wählen Sie, ob die Übung mit **Gewicht** (kg × Wiederholungen) oder mit **Zeit** (Minuten und Sekunden, z. B. Plank) erfasst wird.
- **Übungen verwalten** (Startseite): umbenennen, zwischen Gewicht und Zeit wechseln, Reihenfolge mit ↑/↓ ändern, ausblenden und wieder einblenden. Ausgeblendete Übungen behalten ihren Verlauf.
- **Notiz und Datum** pro Training lassen sich oben im Training bearbeiten. Die Notiz erscheint auch in der Trainingsliste.
- **Bestwerte:** Ein Satz, der schwerer (bei Zeit-Übungen: länger) ist als alles bisher Erfasste, wird mit ★ markiert. Ihr bisheriger Bestwert wird angezeigt.
- **Verlauf** (in jeder Übung über „Verlauf ›“): Bestwert, Anzahl Trainings, Diagramm des Höchstgewichts bzw. der längsten Zeit pro Training (Punkt antippen zeigt die Werte) und eine Liste aller Trainings.
- **Ohne Server:** Ohne erreichbare `api.php` arbeitet die App im lokalen Modus (Speicherung im Browser), damit sie sich sofort ausprobieren lässt.

### Weitere Funktionen

- **Pausentimer:** Nach jedem Satz läuft unten eine Pause (Standard 90 s, einstellbar). Am Ende vibriert das Smartphone (Android) und es ertönt ein Ton.
- **Fortschrittsvorschlag:** Wurden beim letzten Mal alle Sätze mit gleichem Gewicht und gleichen Wiederholungen geschafft, schlägt die App mehr vor (Standard +2,5 kg, bei Zeit-Übungen +5 s) und trägt den Wert gleich ein.
- **Trainingspläne:** Unter „Pläne“ Übungsauswahlen anlegen (z. B. „Tag A“). Beim Start wählen; im Training lassen sich alle Übungen einblenden.
- **Statistik:** Trainings, Trainingszeit und Volumen pro Woche (12 Wochen), Tagesform pro Training und nach Wochentag, Körpergewicht.
- **Tagesform und Körpergewicht:** unter „Nach dem Training“.
- **Export:** Unter „Einstellungen“ als CSV (Semikolon, für Excel/Numbers).
- **Offline-Modus:** Alle Eingaben werden zuerst auf dem Gerät gespeichert und übertragen, sobald der Server erreichbar ist. Ein schwarzer Balken oben zeigt an, wie viele Einträge noch warten. `sw.js` hält die App-Dateien bereit, damit sich die App auch ohne Netz öffnen lässt (nur über HTTPS).

## Dateien

| Datei | Zweck |
|---|---|
| `index.html` | Oberfläche (HTML/CSS/JS, Schriften von Google Fonts) |
| `sw.js` | Service Worker für den Offline-Betrieb (neben `index.html` ablegen) |
| `api.php` | JSON-Schnittstelle zu MySQL (PDO mit vorbereiteten Abfragen) |
| `schema.sql` | Tabellen und Grundübungen |
| `config.sample.php` | Vorlage für die Zugangsdaten → als `config.php` kopieren |
| `migrate.sql` | Nur nötig, falls `api.php` eine bestehende Datenbank nicht selbst erweitern darf |
| `check.php` | Prüfseite für die Einrichtung (zeigt keine Passwörter); kann danach gelöscht werden |

## Datenmodell

```
exercises (id, name UNIQUE, mode 'weight'|'time', sort_order, active)
workouts  (id, workout_date, start_time NULL, end_time NULL, note, rpe NULL, body_weight NULL, plan_id NULL)
plans     (id, name)
plan_exercises (plan_id → plans, exercise_id → exercises)
sets      (id, workout_id → workouts, exercise_id → exercises, set_no, weight_kg NULL, reps NULL, duration_s NULL)
```

- Ein Training (`workouts`) hat beliebig viele Sätze (`sets`).
- Jeder Satz gehört zu einer Übung und hat eine Nummer und – je nach Übung – ein Gewicht mit optionalen Wiederholungen oder eine Dauer in Sekunden.
- Bestehende Datenbanken erweitert `api.php` beim ersten Aufruf automatisch (Zeit-Übungen, Start-/Endzeit).
- „Letztes Mal“ = das jüngste frühere Training, das diese Übung enthält. Lässt man eine Übung einmal aus, erscheint trotzdem der letzte tatsächliche Wert.
- Wenn ein Training gelöscht wird, werden seine Sätze mitgelöscht. Übungen werden nie gelöscht, sondern nur deaktiviert (`active = 0`); so bleibt der Verlauf erhalten.

## Installation (Webhosting mit PHP und MySQL)

1. In der Hosting-Verwaltung eine Datenbank und einen Benutzer anlegen.
2. `schema.sql` importieren (phpMyAdmin → Importieren, oder `mysql -u USER -p DB < schema.sql`).
3. `config.sample.php` als `config.php` kopieren, Zugangsdaten und einen eigenen `app_token` eintragen.
4. `index.html`, `sw.js`, `api.php` und `config.php` in denselben Ordner hochladen (unbedingt über HTTPS).
5. Die Seite auf dem Smartphone öffnen, den Zugangscode (`app_token`) einmal eingeben und
   über „Zum Home-Bildschirm“ als App-Symbol ablegen.

Voraussetzungen: PHP 7.4 oder neuer mit `pdo_mysql`, MySQL 5.7+ oder MariaDB 10.3+.

## Fehlersuche

Zuerst `check.php` im Browser öffnen (z. B. `https://ihre-domain/training/check.php`). Die Seite prüft PHP-Version, `config.php`, Zugangscode, Datenbankverbindung, Tabellen und die Weitergabe des Codes und zeigt bei jedem Punkt, was zu tun ist.

- **Login klappt nicht:** Der Code muss genau dem Wert von `app_token` in `config.php` entsprechen (Groß-/Kleinschreibung). Mit „Code anzeigen“ lässt sich die Eingabe kontrollieren. Filtert der Server den Code heraus, weicht die App automatisch auf einen Ersatzweg aus.

- **„Datenbankverbindung fehlgeschlagen“:** Zugangsdaten in `config.php` prüfen (Host, Datenbankname, Benutzer, Passwort). Bei manchen Hostern lautet der Host nicht `localhost`, sondern z. B. `127.0.0.1` oder ein eigener Servername.
- **„Datenbanktabellen fehlen“:** `schema.sql` wurde noch nicht in die Datenbank importiert, die in `config.php` steht.
- **„Datenbankfehler“:** In `config.php` vorübergehend `'debug' => true` setzen. Dann zeigt die App die genaue Meldung der Datenbank. Danach wieder auf `false` stellen.
- Die App zeigt Fehler direkt auf der Seite und wechselt bei Datenbankproblemen nicht in den lokalen Modus. So gehen keine Einträge unbemerkt verloren.

## API

| Aktion | Methode | Daten |
|---|---|---|
| `ping` | GET | – |
| `exercises` | GET | `&all=1` gibt auch ausgeblendete Übungen zurück |
| `exercise_add` | POST | `{name, mode?: "weight"\|"time"}` |
| `exercise_update` | POST | `{id, name?, active?, mode?}` |
| `exercise_reorder` | POST | `{ids: [..]}` in gewünschter Reihenfolge |
| `history&exercise_id=` | GET | alle Trainings mit Sätzen dieser Übung |
| `workouts` | GET | – |
| `workout_create` | POST | `{date: "YYYY-MM-DD", start_time?: "HH:MM"}` |
| `workout&id=` | GET | Training mit Sätzen, `previous` (letzte Werte je Übung) und `best` (bisheriger Bestwert je Übung) |
| `workout_update` | POST | `{id, note?, date?, start_time?, end_time?, rpe?, body_weight?, plan_id?}` |
| `snapshot` | GET | alle Daten auf einmal (Grundlage für den Offline-Modus) |
| `plan_create` / `plan_update` / `plan_delete` | POST | `{name, exercises}` / `{id, name?, exercises?}` / `{id}` |
| `overview` | GET | letzte 5 Trainings mit ihren Übungen und letztes Datum je Übung |
| `workout_delete` | POST | `{id}` |
| `set_add` | POST | `{workout_id, exercise_id, weight?, reps?, duration?}` (Gewicht oder Dauer in Sekunden) |
| `set_delete` | POST | `{id}` |

Bei jeder Anfrage wird der Header `X-Token` mitgeschickt (aus `config.php`).

## Ausbauplan

1. **Phase 1 (umgesetzt):** Trainings, Sätze, Gewichte, Anzeige des letzten Trainings, Übungen direkt in der App ergänzen, MySQL-Anbindung, lokaler Modus.
2. **Phase 2 (umgesetzt):** Übungen umbenennen, sortieren und ausblenden; Notiz und Datum pro Training bearbeiten.
3. **Phase 3 (umgesetzt):** Verlauf pro Übung mit Diagramm (Höchstgewicht pro Training) und Markierung neuer Bestwerte.
4. **Phase 4 (umgesetzt):** Offline-Modus mit Abgleich, CSV-Export, Pausentimer, Fortschrittsvorschlag, Pläne, Wochenstatistik, Tagesform, Körpergewicht.
5. **Optional:** Mehrere Personen (Tabelle `users`, Spalte `user_id` in `workouts`) mit richtigem Login statt Token.

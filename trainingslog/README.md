# Trainingslog

Ein Trainingstagebuch für das Smartphone: Pro Training werden Übungen, Sätze und Gewichte erfasst. Beim Erfassen sehen Sie jeweils, was Sie beim letzten Mal gemacht haben.

## Funktionen

- **Neues Training:** Datum wählen (vorausgefüllt mit heute) und „Starten“ tippen.
- **Übungen:** Die Liste ist zu Beginn mit diesen Übungen gefüllt: Deadlift, Latzug, Sitting Row, Pull-up, Bankdrücken, Bizeps, Schulter seitlich, Rücken, Butterfly reverse.
- **Sätze erfassen:** Gewicht (Komma oder Punkt), Wiederholungen optional, dann „+ Satz“. Das Gewicht vom letzten Satz ist bereits eingetragen.
- **Letztes Training:** Jede Übung zeigt die Sätze aus dem letzten Training, in dem sie vorkam. Mit „Sätze übernehmen“ wird alles auf einmal kopiert.
- **Neue Übungen** lassen sich während des Trainings unten auf der Seite hinzufügen.
- **Ohne Server:** Ohne erreichbare `api.php` arbeitet die App im lokalen Modus (Speicherung im Browser), damit sie sich sofort ausprobieren lässt.

## Dateien

| Datei | Zweck |
|---|---|
| `index.html` | Oberfläche (HTML/CSS/JS, keine externen Abhängigkeiten) |
| `api.php` | JSON-Schnittstelle zu MySQL (PDO mit vorbereiteten Abfragen) |
| `schema.sql` | Tabellen und Grundübungen |
| `config.sample.php` | Vorlage für die Zugangsdaten → als `config.php` kopieren |

## Datenmodell

```
exercises (id, name UNIQUE, sort_order, active)
workouts  (id, workout_date, note)
sets      (id, workout_id → workouts, exercise_id → exercises, set_no, weight_kg, reps NULL)
```

- Ein Training (`workouts`) hat beliebig viele Sätze (`sets`).
- Jeder Satz gehört zu einer Übung und hat eine Nummer, ein Gewicht und optional Wiederholungen.
- „Letztes Mal“ = das jüngste frühere Training, das diese Übung enthält. Lässt man eine Übung einmal aus, erscheint trotzdem der letzte tatsächliche Wert.
- Wenn ein Training gelöscht wird, werden seine Sätze mitgelöscht. Übungen werden nie gelöscht, sondern nur deaktiviert (`active = 0`); so bleibt der Verlauf erhalten.

## Installation (Webhosting mit PHP und MySQL)

1. In der Hosting-Verwaltung eine Datenbank und einen Benutzer anlegen.
2. `schema.sql` importieren (phpMyAdmin → Importieren, oder `mysql -u USER -p DB < schema.sql`).
3. `config.sample.php` als `config.php` kopieren, Zugangsdaten und einen eigenen `app_token` eintragen.
4. `index.html`, `api.php` und `config.php` in denselben Ordner hochladen (unbedingt über HTTPS).
5. Die Seite auf dem Smartphone öffnen, den Zugangscode (`app_token`) einmal eingeben und
   über „Zum Home-Bildschirm“ als App-Symbol ablegen.

Voraussetzungen: PHP 7.4 oder neuer mit `pdo_mysql`, MySQL 5.7+ oder MariaDB 10.3+.

## API

| Aktion | Methode | Daten |
|---|---|---|
| `ping` | GET | – |
| `exercises` | GET | – |
| `exercise_add` | POST | `{name}` |
| `workouts` | GET | – |
| `workout_create` | POST | `{date: "YYYY-MM-DD"}` |
| `workout&id=` | GET | Training mit Sätzen und `previous` (letzte Werte je Übung) |
| `workout_delete` | POST | `{id}` |
| `set_add` | POST | `{workout_id, exercise_id, weight, reps?}` |
| `set_delete` | POST | `{id}` |

Bei jeder Anfrage wird der Header `X-Token` mitgeschickt (aus `config.php`).

## Ausbauplan

1. **Phase 1 (umgesetzt):** Trainings, Sätze, Gewichte, Anzeige des letzten Trainings, Übungen direkt in der App ergänzen, MySQL-Anbindung, lokaler Modus.
2. **Phase 2:** Übungen umbenennen, sortieren und ausblenden; Notiz pro Training (die Spalte `note` gibt es bereits).
3. **Phase 3:** Verlauf pro Übung mit Diagramm (Höchstgewicht und Volumen pro Training) und Markierung neuer Bestwerte.
4. **Phase 4:** Offline-fähige App (Service Worker): Erfassen ohne Netz im Studio, später Abgleich mit dem Server. CSV-Export.
5. **Optional:** Mehrere Personen (Tabelle `users`, Spalte `user_id` in `workouts`) mit richtigem Login statt Token.

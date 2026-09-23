# Mathematik 1. Sek – Lerntool

Ein Lerntool für Mathematik auf Niveau 1. Sekundarstufe (7. Schuljahr) nach Lehrplan 21. Es läuft vollständig im Browser, ohne Server und ohne Datenbank.

## Starten

**Am einfachsten:** Öffnen Sie `Mathe-1-Sek.html` per Doppelklick. Diese Datei enthält alles und funktioniert auch allein, z. B. als E-Mail-Anhang oder auf einem USB-Stick.

Alternativ öffnen Sie `index.html`. Dann müssen die Ordner `css` und `js` daneben liegen. Eine ZIP-Datei muss deshalb zuerst vollständig entpackt werden.

Eine Internetverbindung ist in beiden Fällen nicht nötig.

Nach Änderungen an den Quelldateien erzeugt `python3 werkzeuge/einzeldatei.py` die Datei `Mathe-1-Sek.html` neu.

Zum Veröffentlichen genügt ein einfacher Webspace oder GitHub Pages. Dafür wird einfach der ganze Ordner `mathe-tool` hochgeladen.

## Inhalt

| Thema | Lehrplan 21 | Stand |
|---|---|---|
| Ganze Zahlen | MA.1 Zahl und Variable | umgesetzt |
| Proportionalität und Dreisatz | MA.3 Grössen, Funktionen, Daten und Zufall | geplant |
| Winkel an Geraden und im Dreieck | MA.2 Form und Raum | geplant |

Jedes Thema besteht aus einer Einführung und drei Übungsstufen:

1. **Grundlagen** – einfache Aufgaben mit einem Rechenschritt
2. **Anwenden** – Aufgaben mit mehreren Schritten
3. **Vertiefen** – Textaufgaben, Umkehraufgaben und das Beurteilen von Aussagen

Die Aufgaben werden per Zufall erzeugt. Dadurch gibt es beliebig viele Aufgaben, und jeder Durchgang sieht anders aus.

Nach einer falschen Antwort erscheint zuerst ein Hinweis. Nach dem zweiten Fehlversuch wird der vollständige Lösungsweg angezeigt.

Eine Stufe gilt als abgeschlossen, wenn von den letzten 10 Aufgaben mindestens 8 im ersten Versuch richtig gelöst wurden. Danach wird die nächste Stufe freigeschaltet. Gesperrte Stufen lassen sich auf Wunsch auch vorher öffnen.

## Fortschritt

Der Fortschritt wird im `localStorage` des Browsers gespeichert. Er gilt deshalb nur für das jeweilige Gerät und den jeweiligen Browser.

Auf der Startseite lässt sich der Stand als JSON-Datei exportieren und wieder importieren. So kann er auf ein anderes Gerät übertragen oder an die Lehrperson geschickt werden.

## Aufbau

```
index.html
css/style.css
js/hilfen.js            Zufallszahlen, Zahlformat, Zahlengerade (SVG)
js/speicher.js          Speichern, Export, Import
js/themen/*.js          ein Thema pro Datei
js/app.js               Navigation und Ablauf der Übungen
```

Ein neues Thema entsteht als eigene Datei in `js/themen/` nach dem Muster von `ganze-zahlen.js`:

- Einführung als Liste von Abschnitten, optional mit interaktivem Element (`widget`)
- pro Stufe eine Liste von Aufgaben-Generatoren

Jeder Generator gibt ein Objekt zurück, das die Aufgabe beschreibt:

```js
{
  typ: 'zahl',          // oder 'auswahl' (dann mit optionen: [{ wert, text }])
  frage: '…',           // HTML
  bild: '…',            // optional, z. B. eine Zahlengerade
  einheit: '°C',        // optional
  antwort: -6,
  hinweis: '…',         // wird nach dem ersten Fehlversuch angezeigt
  loesung: '…'          // Lösungsweg (HTML)
}
```

Die neue Datei wird anschliessend in `index.html` eingebunden.

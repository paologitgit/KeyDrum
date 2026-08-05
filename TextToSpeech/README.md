# Vorleser – Text to Speech

Ein Werkzeug, das Text mit einer deutlichen deutschen Stimme vorliest. Die
Geschwindigkeit ist stufenlos einstellbar.

Es gibt zwei Varianten – beide nutzen die Stimmen, die schon auf dem Rechner
installiert sind. Nichts wird ins Internet geschickt.

| | `index.html` (Browser) | `tts.py` (Kommandozeile) |
|---|---|---|
| Installation | keine | ggf. `espeak-ng` unter Linux |
| Bedienung | Oberfläche mit Reglern | Befehle, gut für Skripte |
| Geschwindigkeit | 0,5× – 3× per Schieberegler | `--speed 0.3` bis `3.0` |
| Mitlesen | ja, aktuelles Wort wird markiert | – |
| Als WAV speichern | nein | ja, `--out datei.wav` |

## Variante 1: Browser (empfohlen)

`index.html` per Doppelklick öffnen – fertig. Am besten in **Chrome** oder
**Edge**, dort stehen die natürlich klingenden Online-Stimmen zur Verfügung
(im Auswahlfeld mit ★ markiert). Safari und Firefox funktionieren ebenfalls.

Funktionen:

* **Stimme** – standardmäßig werden nur deutsche Stimmen angezeigt, die
  hochwertigen zuerst. Das Häkchen entfernen zeigt alle Sprachen.
* **Geschwindigkeit** – Schieberegler von 0,5× bis 3×, dazu Schnellwahl
  (0,75× · 1× · 1,25× · 1,5× · 2×). Änderungen gelten ab dem nächsten Start.
* **Tonhöhe** und **Lautstärke** – für die Verständlichkeit hilft es oft, die
  Tonhöhe leicht abzusenken und langsamer zu lesen.
* **Vorlesen / Pause / Weiter / Stopp**, Tastatur: `Strg`+`Enter` startet,
  `Esc` stoppt.
* **Stimme testen** – spricht einen kurzen Beispielsatz mit den aktuellen
  Einstellungen, ohne den ganzen Text vorzulesen.
* **Mitlesen** – während der Ausgabe wird das gerade gesprochene Wort
  hervorgehoben, der Text scrollt automatisch mit.
* Text und Einstellungen bleiben im Browser gespeichert; `.txt`-Dateien lassen
  sich direkt laden.

Lange Texte werden intern satzweise vorgelesen. Das umgeht einen Fehler in
Chrome, der die Ausgabe nach etwa 15 Sekunden abbricht, und lässt Pause und
Stopp sofort reagieren.

### Wenn keine deutsche Stimme angeboten wird

* **Windows:** Einstellungen → Zeit & Sprache → Sprache & Region → Deutsch
  hinzufügen → Sprachpaket mit *Sprachausgabe* installieren.
  Gute Stimmen: *Microsoft Katja*, *Microsoft Hedda*, *Microsoft Stefan*.
* **macOS:** Systemeinstellungen → Bedienungshilfen → Gesprochene Inhalte →
  Systemstimme → Anpassen → Deutsch. Empfehlenswert: *Anna (Premium)*,
  *Petra*, *Markus*.
* **Linux:** Chrome bringt eigene Online-Stimmen mit; ansonsten
  `sudo apt install espeak-ng` und die Kommandozeilen-Variante nutzen.

## Variante 2: Kommandozeile

```bash
python3 tts.py "Guten Morgen, hier spricht der Computer."
python3 tts.py --speed 1.4 --file brief.txt
python3 tts.py --list-voices
python3 tts.py --speed 0.9 --voice Anna --out ansage.wav "Der Zug fällt heute aus."
echo "Auch über eine Pipe." | python3 tts.py -s 1.2
```

Optionen:

| Option | Bedeutung |
|---|---|
| `-s`, `--speed` | Tempo: `1.0` normal, `1.5` schneller, `0.8` langsamer (0.3 – 3.0) |
| `-v`, `--voice` | Stimme nach Namen, Teiltreffer genügt (`--voice anna`) |
| `-f`, `--file` | Text aus einer Datei (UTF-8) |
| `-o`, `--out` | In eine WAV-Datei schreiben statt abzuspielen |
| `-l`, `--list-voices` | Zeigt alle Stimmen, deutsche zuerst |

Ohne `--voice` wird automatisch die erste deutsche Stimme des Systems gewählt.

Es wird nur Python 3 benötigt, keine zusätzlichen Pakete. Die Sprachausgabe
kommt vom Betriebssystem:

| System | Verwendet | Installation |
|---|---|---|
| macOS | `say` | vorinstalliert |
| Windows | SAPI 5 über PowerShell | vorinstalliert |
| Linux | `espeak-ng` | `sudo apt install espeak-ng` |

Hinweis: `espeak-ng` klingt deutlich synthetischer als die Stimmen von Windows
und macOS. Wer unter Linux eine natürliche Stimme braucht, fährt mit
`index.html` in Chrome besser.

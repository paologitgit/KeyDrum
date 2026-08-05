# Vorleser – Text to Speech

Ein Werkzeug, das Text mit einer deutlichen deutschen Stimme vorliest.
Geschwindigkeit und Sprechpausen sind stufenlos einstellbar.

Es gibt zwei Varianten – beide nutzen die Stimmen, die schon auf dem Rechner
installiert sind. Nichts wird ins Internet geschickt.

| | `index.html` (Browser) | `tts.py` (Kommandozeile) |
|---|---|---|
| Installation | keine | ggf. `espeak-ng` unter Linux |
| Bedienung | Oberfläche mit Reglern | Befehle, gut für Skripte |
| Geschwindigkeit | 0,5× – 3× per Schieberegler | `--speed 0.3` bis `3.0` |
| Satzpausen | 0 – 1400 ms per Schieberegler | `--pause 400` |
| Mitlesen | ja, aktuelles Wort wird markiert | – |
| Als WAV speichern | nein | ja, `--out datei.wav` |

## Warum es natürlicher klingt

Die Sprachausgaben setzen nach einem Satzpunkt von sich aus nur eine sehr
kurze Pause – dadurch wirkt vorgelesener Text gehetzt und abgehackt. Beide
Varianten zerlegen den Text deshalb selbst in Sätze und legen eine eigene,
einstellbare Pause dazwischen:

| nach … | Pause | bei 400 ms Grundwert |
|---|---|---|
| Satz (`.` `!` `?` `…`) | 1,0× | 400 ms |
| Absatz (Leerzeile) | 2,4× | 960 ms |
| Zeilenumbruch, z. B. Überschrift | 1,4× | 560 ms |
| Komma in einem sehr langen Satz | 0,35× | 140 ms |

Beim Sprechtempo werden die Pausen mitskaliert: wer 1,5× schnell hört, will
auch keine vollen Pausen, wer auf 0,8× verlangsamt, bekommt sie entsprechend
länger.

Damit dabei nicht an der falschen Stelle getrennt wird, gilt ein Punkt nicht
automatisch als Satzende. Nicht getrennt wird nach Zahlen (`am 1. Januar`,
`S. 25`), nach einzelnen Buchstaben (`z. B.`, `u. a.`) und nach gängigen
Abkürzungen (`Dr.`, `Prof.`, `ca.`, `vgl.`, `inkl.` …) sowie dann, wenn der
Text danach klein weitergeht.

Zusätzlich werden Abkürzungen für die Ausgabe ausgeschrieben – viele Stimmen
buchstabieren „z. B.“ sonst als „zett be“. Angezeigt wird weiterhin der
Originaltext; abschalten lässt sich das im Browser per Häkchen, auf der
Kommandozeile mit `--no-expand`.

## Variante 1: Browser (empfohlen)

`index.html` per Doppelklick öffnen – fertig. Am besten in **Chrome** oder
**Edge**, dort stehen die natürlich klingenden Online-Stimmen zur Verfügung
(im Auswahlfeld mit ★ markiert). Safari und Firefox funktionieren ebenfalls.

Funktionen:

* **Stimme** – standardmäßig werden nur deutsche Stimmen angezeigt, die
  hochwertigen zuerst. Das Häkchen entfernen zeigt alle Sprachen.
* **Geschwindigkeit** – Schieberegler von 0,5× bis 3×, dazu Schnellwahl
  (0,75× · 1× · 1,25× · 1,5× · 2×). Änderungen gelten ab dem nächsten Start.
* **Pause nach einem Satz** – Schieberegler von 0 bis 1400 ms, Voreinstellung
  400 ms. Diese Zeit kommt zu der kurzen Pause der Stimme noch dazu; unter dem
  Regler steht, wie lang die Pausen beim aktuellen Tempo tatsächlich werden.
  Für ein ruhiges, gut verständliches Vorlesen sind 400 – 650 ms ein guter
  Bereich.
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

Vorgelesen wird Satz für Satz. Das ist die Voraussetzung für die eigenen
Pausen, umgeht nebenbei einen Fehler in Chrome, der die Ausgabe nach etwa
15 Sekunden abbricht, und lässt Pause und Stopp sofort reagieren – auch
mitten in einer Pause zwischen zwei Sätzen.

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
python3 tts.py --speed 1.4 --pause 550 --file brief.txt
python3 tts.py --list-voices
python3 tts.py --speed 0.9 --voice Anna --out ansage.wav "Der Zug fällt heute aus."
echo "Auch über eine Pipe." | python3 tts.py -s 1.2
```

Optionen:

| Option | Bedeutung |
|---|---|
| `-s`, `--speed` | Tempo: `1.0` normal, `1.5` schneller, `0.8` langsamer (0.3 – 3.0) |
| `-p`, `--pause` | Pause nach einem Satz in Millisekunden (Standard `400`) |
| `-v`, `--voice` | Stimme nach Namen, Teiltreffer genügt (`--voice anna`) |
| `-f`, `--file` | Text aus einer Datei (UTF-8) |
| `-o`, `--out` | In eine WAV-Datei schreiben statt abzuspielen |
| `--no-expand` | Abkürzungen nicht ausschreiben |
| `-l`, `--list-voices` | Zeigt alle Stimmen, deutsche zuerst |

Die Pausen gehen hier als echte Pausenanweisung an die Sprachausgabe
(SSML `<break>` bzw. `[[slnc]]` bei macOS) und **ersetzen** deren eigene
Satzpause. `--pause 400` bedeutet also exakt 400 ms Stille; `--pause 0`
lässt der Stimme ihre gewohnten, sehr knappen Pausen.

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

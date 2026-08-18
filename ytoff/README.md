# ytoff

Kleines Kommandozeilen-Werkzeug für macOS, das YouTube-Videos, Playlists und
ganze Kanäle **für den privaten Offline-Gebrauch** archiviert. Es abonniert
Kanäle, merkt sich Geladenes und holt bei jedem Lauf nur das Neue.

Die eigentliche Arbeit macht [yt-dlp](https://github.com/yt-dlp/yt-dlp);
`ytoff` ist die Abo- und Bibliotheksverwaltung drumherum.

## Installation

```bash
brew install ffmpeg          # empfohlen — bringt auch ffprobe mit
brew install pipx            # falls noch nicht vorhanden
pipx install /pfad/zu/ytoff  # dieses Verzeichnis
ytoff doctor                 # prüft Python, yt-dlp, ffmpeg, Speicherplatz
```

Ohne Homebrew läuft es auch: `pip install imageio-ffmpeg` liefert ein
mitgeliefertes ffmpeg. Dann fehlt allerdings `ffprobe` — Zusammenfügen
funktioniert, Kapitelmarken und SponsorBlock brauchen es. `ytoff doctor` sagt,
was gerade da ist.

Alternativ ohne pipx:

```bash
python3 -m venv ~/.venvs/ytoff
~/.venvs/ytoff/bin/pip install -e /pfad/zu/ytoff
ln -s ~/.venvs/ytoff/bin/ytoff /usr/local/bin/ytoff
```

## Loslegen

```bash
ytoff init                                        # Konfiguration anlegen
ytoff add https://www.youtube.com/@kanalname \
      --name "Kanalname" --limit 10               # abonnieren
ytoff sync --dry-run                              # Vorschau: was fehlt, wie gross
ytoff sync                                        # laden (fragt vorher nach)
ytoff list                                        # Abos + Bibliothek
```

Voreinstellungen: Bibliothek in `~/Movies/YT-Offline`, Konfiguration in
`~/.config/ytoff/config.yaml`, maximal 1080p, die neuesten 20 Videos pro Abo.

Dateien landen als `Kanal/JJJJ-MM-TT - Titel [videoid].mp4` — sortierbar und
für die Mediathek deiner Wahl (IINA, VLC, Infuse) direkt brauchbar.

## Befehle

| Befehl | Zweck |
|---|---|
| `ytoff init` | Konfiguration anlegen |
| `ytoff add <url>` | Kanal, Playlist oder einzelnes Video abonnieren |
| `ytoff remove <muster>` | Abo entfernen (Teilstring von URL oder Name) |
| `ytoff list` | Abos und Bibliotheksbestand anzeigen |
| `ytoff sync` | fehlende Videos holen (`--dry-run`, `--only`, `-y`, `-v`) |
| `ytoff doctor` | Umgebung prüfen |
| `ytoff update` | yt-dlp aktualisieren |

Nützliche Schalter bei `add`: `--audio` (nur Tonspur als m4a, für Podcast-
Nutzung), `--since JJJJMMTT`, `--height 720`.

## Konfiguration

```yaml
ziel: ~/Movies/YT-Offline
max_hoehe: 1080
tempo:
  pause_zwischen_anfragen: 0.75   # Drosselung gegen temporäre Sperren
  parallele_fragmente: 4
extras:
  untertitel: [de, en]
  kapitel: true
  thumbnail: true
  metadaten: true
  sponsor_entfernen: []           # z. B. [sponsor, selfpromo, intro]
kanaele:
  - url: https://www.youtube.com/@kanalname
    name: Kanalname
    limit_neueste: 20
    ab_datum: "20250101"          # optional
    nur_audio: false              # optional
    max_hoehe: 720                # optional, überschreibt max_hoehe global
```

Ein vertippter Schlüssel ist ein Fehler und keine stille Nichtbeachtung —
`ytoff` sagt dann, welcher Schlüssel unbekannt ist.

## Wie „nur das Neue" funktioniert

yt-dlp führt eine Archivdatei mit den IDs aller geladenen Videos. `ytoff` legt
sie als `.ytoff-archive.txt` **in der Bibliothek** ab, nicht neben der
Konfiguration: Wer die Bibliothek löscht, löscht den Zustand mit, und der
nächste Sync füllt sie sauber wieder auf, statt alles fälschlich als „schon
vorhanden" zu überspringen.

Ein Sync-Lauf ist damit jederzeit abbrechbar und beliebig oft wiederholbar.

## Automatisch laufen lassen

`launchd` startet den Sync z. B. täglich um 03:00. Datei
`~/Library/LaunchAgents/com.ytoff.sync.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
  <key>Label</key><string>com.ytoff.sync</string>
  <key>ProgramArguments</key>
  <array><string>/Users/DEINNAME/.local/bin/ytoff</string><string>sync</string><string>-y</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>3</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/ytoff.log</string>
  <key>StandardErrorPath</key><string>/tmp/ytoff.log</string>
</dict></plist>
```

Aktivieren mit `launchctl load ~/Library/LaunchAgents/com.ytoff.sync.plist`.
Achtung: `-y` lädt ohne Rückfrage — vorher einmal mit `--dry-run` prüfen, wie
gross die Läufe ausfallen.

## Wenn etwas nicht geht

**„Unable to extract …", „Sign in to confirm you're not a bot", leere Antwort.**
Fast immer eine veraltete yt-dlp-Version: `ytoff update`. YouTube ändert die
Auslieferung laufend (PO-Tokens, SABR); eine Version von vor ein paar Monaten
bricht typischerweise. `ytoff doctor` warnt ab 60 Tagen Alter.

**Video ist altersbeschränkt oder Mitglieder-Inhalt.** Braucht Cookies aus dem
Browser. In `ytoff` noch nicht verdrahtet — direkt mit
`yt-dlp --cookies-from-browser safari` prüfen.

**Downloads brechen ab oder werden gedrosselt.** `pause_zwischen_anfragen`
erhöhen und `parallele_fragmente` senken.

**Zu wenig Speicher.** Grobwerte pro Stunde Material: 720p ≈ 0.55 GB,
1080p ≈ 1.5 GB, 4K ≈ 11 GB, reines Audio ≈ 0.06 GB. `ytoff sync --dry-run`
rechnet das vorab aus.

## Rechtlicher Rahmen

Das Herunterladen widerspricht den YouTube-Nutzungsbedingungen; in CH/DE deckt
die Privatkopie-Schranke den rein persönlichen Gebrauch. Dieses Werkzeug ist
bewusst nur dafür gebaut: kein Teilen, kein Hosting, keine Weitergabe. Inhalte
mit DRM (YouTube Movies, gekaufte Filme) sind ausdrücklich nicht unterstützt.

## Stand

Erste Version. 48 Tests laufen (`python3 -m pytest tests`) und decken
Konfiguration, Optionsbau, Dateinamen-Schablone, Grössenschätzung, Planer und
CLI ab — jeweils ohne Netzzugriff.

**Noch nicht gegen das echte YouTube getestet:** Die Entwicklungsumgebung hat
keinen Zugang zu youtube.com. Der erste Lauf auf deinem Mac ist damit der erste
echte Test — am besten mit `ytoff sync --dry-run` auf einem kleinen Kanal
beginnen.

# Grobabklärung: Tool für YouTube-Videos & ganze Kanäle offline

Stand: 2026-08-18 · Status: **Vorabklärung, noch keine Implementierung**

## Kurzfazit

**Ja, machbar** — und zwar mit überschaubarem Aufwand. Der schwierige Teil
(YouTube-Streams entschlüsseln, Formate zusammenfügen, Kanäle/Playlists
auflösen) ist bereits gelöste Arbeit und steckt in `yt-dlp`. Unser Tool wäre
im Kern eine **Bibliotheks-Verwaltung um yt-dlp herum**: Abo-Liste, Sync-Lauf,
Zustand merken, lokal abspielen.

Realistischer Aufwand für eine brauchbare erste Version: **2–4 Tage**.
Der Dauerbetrieb ist der teurere Teil, nicht der Bau (siehe Risiken).

## Was ich konkret geprüft habe

| Prüfpunkt | Ergebnis |
|---|---|
| `yt-dlp` installierbar | ✅ `pip install yt-dlp` → Version 2026.07.04 |
| ffmpeg nötig (Video+Audio zusammenfügen) | ✅ ohne System-Installation lösbar: `pip install imageio-ffmpeg` liefert statisches ffmpeg 7.0.2 |
| Kanal-/Playlist-Auflösung | ✅ eingebaut (`-I`, `--dateafter`) |
| „nur neue Videos" (Inkrement-Sync) | ✅ `--download-archive` — genau der Mechanismus, den ein Abo-Tool braucht |
| Untertitel, Kapitel, Thumbnails, Metadaten einbetten | ✅ `--embed-subs/-chapters/-thumbnail/-metadata` |
| Werbe-/Sponsor-Segmente entfernen | ✅ `--sponsorblock-remove` |
| Login-pflichtige Inhalte | ✅ `--cookies-from-browser` |
| Live-Test gegen youtube.com | ❌ **hier nicht möglich** — der Proxy dieser Sandbox blockt YouTube (403). Kein Hinweis auf ein Problem des Ansatzes, nur diese Umgebung. Der Test muss auf deinem Rechner laufen. |

Zusatzbefund aus dem Extraktor-Code von yt-dlp: **35 Fundstellen zu
"PO-Token"** und Referenzen auf `visitor_data`/`sabr`. Das ist der Beleg für
das unten beschriebene Hauptrisiko — YouTube verlangt zunehmend Client-Tokens,
und yt-dlp muss dem laufend nachziehen.

## Architektur-Vorschlag

Drei Schichten, klar getrennt:

```
┌─ Abo-Konfiguration (YAML)  ── welche Kanäle/Playlists, Qualität, Limit
├─ Sync-Engine (Python)      ── yt-dlp als Bibliothek + Archiv-Datei
│                               → "hol alles Neue seit letztem Lauf"
└─ Bibliothek (Ordner + SQLite/JSON) ── Titel, Kanal, Datum, Dauer, Pfad
```

Skizze der Abo-Datei:

```yaml
qualitaet: "bestvideo[height<=1080]+bestaudio/best"
ziel: ~/Videos/YT-Offline
kanaele:
  - url: https://www.youtube.com/@beispielkanal
    limit_neueste: 20        # nicht 800 Videos auf einmal
    ab_datum: "20250101"
  - url: https://www.youtube.com/playlist?list=...
```

Ein Sync-Lauf = `yt-dlp` pro Eintrag mit gemeinsamer `archive.txt`. Bereits
geladene Video-IDs werden übersprungen — der Lauf ist damit beliebig oft
wiederholbar und abbruchsicher.

### Bedienung — drei Ausbaustufen

1. **CLI** (`ytoff sync`, `ytoff add <url>`, `ytoff list`) — Kern, 1 Tag.
2. **Lokale Web-Oberfläche** (kleiner Flask-Server, Bibliothek durchsuchen,
   im Browser abspielen) — +1 Tag.
3. **Automatik** (Cron/systemd-Timer, z. B. nächtlicher Sync) — +0.5 Tage.

Für „nur offline schauen" reicht Stufe 1 plus VLC. Stufe 2 lohnt sich, sobald
mehrere Kanäle drin sind.

## Risiken und offene Punkte

**1. Rechtliches (der eigentliche Entscheidungspunkt, nicht der technische).**
Herunterladen widerspricht den YouTube-Nutzungsbedingungen. In CH/DE existiert
gleichzeitig die Privatkopie-Schranke für den rein persönlichen Gebrauch. Für
dich privat: praktisch unproblematisch. Weitergeben, öffentlich hosten oder
als Dienst anbieten: **nicht** — dann wird es Verbreitung geschützter Werke.
Ich baue das Tool als reines Privatarchiv-Werkzeug, ohne Sharing-Funktionen.

**2. Wartungsaufwand — das größte praktische Risiko.**
YouTube ändert regelmäßig die Auslieferung (PO-Tokens, SABR-Streaming).
yt-dlp zieht nach, aber das heißt: **die Abhängigkeit muss laufend aktuell
gehalten werden.** Eine drei Monate alte Version bricht typischerweise. Das
Tool sollte deshalb ein `ytoff update` mitbringen und bei Extraktor-Fehlern
verständlich melden „yt-dlp veraltet" statt einen Stacktrace zu werfen.

**3. Ganze Kanäle sind mengenmäßig heikel.**
Grober Speicherbedarf pro Stunde Material: 720p ≈ 0.4–0.7 GB, 1080p ≈ 1–2 GB,
4K ≈ 8–15 GB. Ein Kanal mit 500 Videos à 15 min in 1080p landet schnell bei
~200 GB. Deshalb: Standardmäßig **Limit + Qualitätsdeckel + Vorschau der
geschätzten Größe vor dem Start**, nicht blind „alles".

**4. Rate-Limits.**
Zu schnelles Herunterladen führt zu temporären Sperren. Gegenmittel sind
vorhanden (`--sleep-requests`, gedrosselte Parallelität) und gehören in die
Voreinstellung, nicht als Option für später.

**5. Dieses Repo passt nicht.**
`KeyDrum` ist eine pygame-Drum-Machine — inhaltlich unverwandt. Vorschlag:
**eigenes Repo** für das Tool. Ich habe hier nur diese Abklärung abgelegt.

## Was ich nicht abgeklärt habe

- Kein Live-Test gegen YouTube (Sandbox blockt) — Format-Auswahl und
  Kanal-Auflösung sind auf deinem Rechner gegenzuprüfen.
- Keine Prüfung auf macOS/Windows; die Abklärung lief auf Linux.
- DRM-geschützte Inhalte (YouTube Movies, gekaufte Filme) sind **außerhalb**
  des Scopes — dort ist Umgehung technisch wie rechtlich eine andere Sache.

## Empfohlener nächster Schritt

Stufe 1 bauen: CLI + Abo-YAML + Archiv-Sync, mit einem einzelnen Kanal als
Testfall. Danach entscheiden, ob die Weboberfläche kommt.

Offene Fragen an dich, bevor ich loslege:
- Zielplattform — Linux, macOS oder Windows?
- Nur Video, oder auch reiner Audio-Modus (Podcast-Nutzung)?
- Eigenes Repo anlegen, oder soll das hier als Unterordner leben?

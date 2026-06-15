# KeyLooper – Setup

## Voraussetzungen
- macOS 14 (Sonoma) oder neuer
- Xcode 15 oder neuer

## Öffnen in Xcode
1. Öffne Xcode
2. File → Open → wähle `KeyLooper/Package.swift`
3. Xcode erkennt es automatisch als Swift Package

## Berechtigungen setzen (einmalig)
1. Im Project Navigator: `KeyLooper` → Target `KeyLooper` → Signing & Capabilities
2. Klicke `+` → füge **Audio Input** hinzu
3. Unter **Info** → füge `Privacy - Microphone Usage Description` hinzu mit Text: "KeyLooper benötigt Mikrofonzugriff"

## Behringer Euphoria
Die App erkennt die Euphoria automatisch beim Start. Falls nicht:
- Menüleiste → Gerät-Picker → deine Soundkarte wählen

## Bauen & Starten
- In Xcode: `Cmd+R`

## Tastatur-Shortcuts

| Taste     | Funktion                     |
|-----------|------------------------------|
| `1`–`5`   | Spur auswählen               |
| `R`       | Aufnehmen / Overdub          |
| `Space`   | Play / Stop (aktive Spur)    |
| `S`       | Alle Spuren stoppen          |
| `T`       | Tap Tempo                    |
| `[` / `]` | Multiplikator kleiner/größer |
| `M`       | MIDI Learn (aktive Spur)     |
| `C`       | Spur löschen                 |
| `ESC`     | MIDI Learn abbrechen         |

## Multiplikatoren
- **1×** = 1 Master-Loop (z.B. 4 Beats)
- **2×** = 2 Master-Loops (8 Beats)
- **4×** = 4 Master-Loops (16 Beats)
- **8×** = 8 Master-Loops (32 Beats)

## MIDI Learn
1. Klicke **MIDI** bei einer Spur (oder drücke `M`)
2. Drücke die gewünschte MIDI-Taste/Pad
3. Mapping wird gespeichert und bleibt beim nächsten Start erhalten

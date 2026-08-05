#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tts.py - Text to Speech fuer die Kommandozeile.

Liest Text mit einer deutschen Systemstimme vor. Die Geschwindigkeit laesst
sich frei einstellen (1.0 = normal, 1.5 = anderthalbfach, 0.8 = langsamer).

Beispiele:
    python3 tts.py "Guten Morgen, hier spricht der Computer."
    python3 tts.py --speed 1.4 --file brief.txt
    python3 tts.py --list-voices
    python3 tts.py --speed 0.9 --out ansage.wav "Der Zug faellt heute aus."

Es wird die Sprachausgabe verwendet, die das Betriebssystem mitbringt:
    macOS    say
    Windows  SAPI ueber PowerShell
    Linux    espeak-ng / espeak (apt install espeak-ng)
"""

import argparse
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile

# Referenz-Sprechtempo in Woertern pro Minute (entspricht Faktor 1.0).
BASE_WPM = 175


def die(message):
    sys.stderr.write("Fehler: %s\n" % message)
    sys.exit(1)


def run(cmd, stdin_text=None):
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_text.encode("utf-8") if stdin_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        die("Programm nicht gefunden: %s" % cmd[0])
    if proc.returncode != 0:
        die("%s meldet einen Fehler:\n%s" % (cmd[0], proc.stderr.decode("utf-8", "replace").strip()))
    return proc.stdout.decode("utf-8", "replace")


# --------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------

class Backend(object):
    """Gemeinsame Schnittstelle: Stimmen auflisten, sprechen, in Datei schreiben."""

    name = "?"

    def voices(self):
        """Liste von (Name, Sprachkuerzel)."""
        raise NotImplementedError

    def speak(self, text, voice, speed, out=None):
        raise NotImplementedError

    def german_voices(self):
        return [v for v in self.voices() if v[1].lower().replace("_", "-").startswith("de")]

    def pick_voice(self, wanted):
        """Stimme nach Namen suchen, sonst die erste deutsche nehmen."""
        available = self.voices()
        if wanted:
            for name, lang in available:
                if name.lower() == wanted.lower():
                    return name
            for name, lang in available:
                if wanted.lower() in name.lower():
                    return name
            die("Stimme %r nicht gefunden. Verfuegbare Stimmen: python3 tts.py --list-voices" % wanted)
        german = self.german_voices()
        if german:
            return german[0][0]
        return None


class MacSay(Backend):
    """macOS: /usr/bin/say - liefert von Haus aus sehr klare deutsche Stimmen."""

    name = "say (macOS)"

    def voices(self):
        out = run(["say", "-v", "?"])
        result = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                lang_index = next((i for i, p in enumerate(parts) if "_" in p and len(p) == 5), None)
                if lang_index:
                    result.append((" ".join(parts[:lang_index]), parts[lang_index].replace("_", "-")))
        return result

    def speak(self, text, voice, speed, out=None):
        cmd = ["say", "-r", str(int(round(BASE_WPM * speed)))]
        if voice:
            cmd += ["-v", voice]
        if out:
            # say schreibt AIFF; ueber afconvert nach WAV wandeln.
            tmp = tempfile.mktemp(suffix=".aiff")
            run(cmd + ["-o", tmp, "--", text])
            run(["afconvert", "-f", "WAVE", "-d", "LEI16", tmp, out])
            os.remove(tmp)
        else:
            run(cmd + ["--", text])


class WindowsSapi(Backend):
    """Windows: System.Speech (SAPI 5) ueber PowerShell."""

    name = "SAPI (Windows)"

    PS = (
        "Add-Type -AssemblyName System.Speech;"
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    )

    def _ps(self, script):
        return run(["powershell", "-NoProfile", "-Command", self.PS + script])

    def voices(self):
        out = self._ps("$s.GetInstalledVoices() | % { $_.VoiceInfo.Name + '|' + $_.VoiceInfo.Culture.Name }")
        result = []
        for line in out.splitlines():
            if "|" in line:
                name, lang = line.rsplit("|", 1)
                result.append((name.strip(), lang.strip()))
        return result

    @staticmethod
    def _rate(speed):
        # SAPI kennt -10 .. 10; ein Schritt entspricht grob dem Faktor 3^(1/10).
        return max(-10, min(10, int(round(10 * math.log(speed, 3)))))

    def speak(self, text, voice, speed, out=None):
        script = "$s.Rate = %d;" % self._rate(speed)
        if voice:
            script += "$s.SelectVoice('%s');" % voice.replace("'", "''")
        if out:
            script += "$s.SetOutputToWaveFile('%s');" % os.path.abspath(out).replace("'", "''")
        script += "$s.Speak('%s');$s.Dispose();" % text.replace("'", "''")
        self._ps(script)


class Espeak(Backend):
    """Linux: espeak-ng - immer verfuegbar, klingt aber deutlich synthetischer."""

    name = "espeak-ng (Linux)"

    def __init__(self, binary):
        self.binary = binary

    def voices(self):
        out = run([self.binary, "--voices"])
        result = []
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4:
                result.append((parts[3], parts[1]))
        return result

    def speak(self, text, voice, speed, out=None):
        cmd = [self.binary, "-s", str(int(round(BASE_WPM * speed)))]
        cmd += ["-v", voice or "de"]
        if out:
            cmd += ["-w", out]
        run(cmd + ["--stdin"], stdin_text=text)


def detect_backend():
    system = platform.system()
    if system == "Darwin" and shutil.which("say"):
        return MacSay()
    if system == "Windows" and shutil.which("powershell"):
        return WindowsSapi()
    for binary in ("espeak-ng", "espeak"):
        if shutil.which(binary):
            return Espeak(binary)
    if system == "Windows" and shutil.which("powershell"):
        return WindowsSapi()
    die(
        "Keine Sprachausgabe gefunden.\n"
        "  Linux:   sudo apt install espeak-ng\n"
        "  macOS:   'say' ist vorinstalliert\n"
        "  Windows: PowerShell muss im PATH liegen\n"
        "Alternative ohne Installation: index.html im Browser oeffnen."
    )


# --------------------------------------------------------------------------

def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Liest Text mit einer deutschen Stimme vor.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Beispiel: python3 tts.py --speed 1.3 \"Das Paket kommt morgen an.\"",
    )
    p.add_argument("text", nargs="*", help="Der vorzulesende Text.")
    p.add_argument("-f", "--file", help="Text aus einer Datei lesen (UTF-8).")
    p.add_argument("-s", "--speed", type=float, default=1.0,
                   help="Geschwindigkeit: 1.0 = normal, 1.5 = schneller, 0.8 = langsamer (0.3-3.0).")
    p.add_argument("-v", "--voice", help="Name der Stimme (siehe --list-voices).")
    p.add_argument("-o", "--out", help="In eine WAV-Datei schreiben statt abzuspielen.")
    p.add_argument("-l", "--list-voices", action="store_true", help="Verfuegbare Stimmen anzeigen.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    backend = detect_backend()

    if args.list_voices:
        german = backend.german_voices()
        print("Sprachausgabe: %s\n" % backend.name)
        print("Deutsche Stimmen:")
        for name, lang in german or []:
            print("  %-28s %s" % (name, lang))
        if not german:
            print("  (keine gefunden - bitte eine deutsche Stimme im System nachinstallieren)")
        print("\nAlle Stimmen:")
        for name, lang in backend.voices():
            print("  %-28s %s" % (name, lang))
        return 0

    if not 0.3 <= args.speed <= 3.0:
        die("Die Geschwindigkeit muss zwischen 0.3 und 3.0 liegen.")

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            die("Datei nicht lesbar: %s" % exc)
    elif args.text:
        text = " ".join(args.text)
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        die("Kein Text angegeben. Hilfe: python3 tts.py --help")

    text = text.strip()
    if not text:
        die("Der Text ist leer.")

    voice = backend.pick_voice(args.voice)
    if voice is None:
        sys.stderr.write("Hinweis: keine deutsche Stimme gefunden, es wird die Standardstimme verwendet.\n")

    backend.speak(text, voice, args.speed, args.out)

    if args.out:
        print("Gespeichert: %s (%s, %.2fx)" % (args.out, voice or "Standardstimme", args.speed))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

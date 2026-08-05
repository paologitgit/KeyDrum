#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tts.py - Text to Speech fuer die Kommandozeile.

Liest Text mit einer deutschen Systemstimme vor. Geschwindigkeit und die
Sprechpausen zwischen den Saetzen lassen sich frei einstellen.

Beispiele:
    python3 tts.py "Guten Morgen, hier spricht der Computer."
    python3 tts.py --speed 1.4 --pause 550 --file brief.txt
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
import re
import shutil
import subprocess
import sys
import tempfile

# Referenz-Sprechtempo in Woertern pro Minute (entspricht Faktor 1.0).
BASE_WPM = 175

# Ab dieser Laenge wird ein Satz zusaetzlich an einem Komma getrennt.
MAX_LEN = 220

# Pausenlaenge je Abschnittsart, als Vielfaches der eingestellten Satzpause.
FACTOR = {"sentence": 1.0, "paragraph": 2.4, "line": 1.4, "clause": 0.35, "end": 0.0}
RANK = {"clause": 0, "sentence": 1, "line": 2, "paragraph": 3}

TERMINATORS = ".!?…"
CLOSERS = "\"'»«”’)]}"

# Abkuerzungen, nach denen praktisch nie ein Satz endet.
ABBREV = set(
    "abb abs art bd bspw bzgl bzw ca dgl dipl dr ebd evtl geb gem ggf ggfs hr hrsg incl inkl "
    "insb jh jhd kap lt max min mio mrd nr od pos prof rd sog st std str tel vgl vs zzgl".split()
)

# Ausgeschrieben klingen diese Kuerzel deutlich runder.
EXPANSIONS = [
    (r"\bz\.\s*B\.", "zum Beispiel"),
    (r"\bd\.\s*h\.", "das heißt"),
    (r"\bu\.\s*a\.", "unter anderem"),
    (r"\bu\.\s*U\.", "unter Umständen"),
    (r"\bi\.\s*d\.\s*R\.", "in der Regel"),
    (r"\bi\.\s*A\.", "im Auftrag"),
    (r"\bv\.\s*a\.", "vor allem"),
    (r"\bz\.\s*T\.", "zum Teil"),
    (r"\bz\.\s*Zt?\.", "zurzeit"),
    (r"\bu\.\s*s\.\s*w\.|\busw\.", "und so weiter"),
    (r"\bu\.\s*v\.\s*m\.", "und vieles mehr"),
    (r"\betc\.", "et cetera"),
    (r"\bbzw\.", "beziehungsweise"),
    (r"\bbspw\.", "beispielsweise"),
    (r"\bggfs?\.", "gegebenenfalls"),
    (r"\bevtl\.", "eventuell"),
    (r"\binkl\.", "inklusive"),
    (r"\bexkl\.", "exklusive"),
    (r"\bzzgl\.", "zuzüglich"),
    (r"\bvgl\.", "vergleiche"),
    (r"\bca\.", "circa"),
    (r"\bDr\.", "Doktor"),
    (r"\bProf\.", "Professor"),
    (r"\bNr\.", "Nummer"),
    (r"\bMio\.", "Millionen"),
    (r"\bMrd\.", "Milliarden"),
    (r"\bTel\.", "Telefon"),
    (r"\bStr\.", "Straße"),
    (r"\bsog\.", "sogenannt"),
    (r"\bJh\.", "Jahrhundert"),
    (r"\s*&\s*", " und "),
]

WORD_BEFORE = re.compile(r"([A-Za-zÄÖÜäöüß]+|\d+)$")


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
# Text in Sprechabschnitte zerlegen
# --------------------------------------------------------------------------

def is_sentence_end(text, dot, end):
    """Beendet der Punkt an Position `dot` wirklich einen Satz?"""
    rest = text[end:]
    if not rest.strip():
        return True

    stripped = rest.lstrip(" \t")
    if not stripped:
        return True
    # Geht es klein weiter oder folgt ein Komma, war das kein Satzende.
    if stripped[0] in ",;:)" or stripped[0].islower():
        return False

    match = WORD_BEFORE.search(text[:dot])
    if match:
        word = match.group(1)
        if word.isdigit():          # "1. Januar", "S. 25"
            return False
        if len(word) == 1:          # "z. B.", "u. a."
            return False
        if word.lower() in ABBREV:
            return False
    return True


def segment(text):
    """Liefert [(Abschnitt, Art), ...] mit Art aus FACTOR."""
    segments = []
    start = 0
    i = 0
    n = len(text)

    def push(to, kind):
        nonlocal start
        a, b = start, to
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        start = to
        if b > a:
            segments.append([text[a:b], kind])
        elif segments and RANK.get(kind, -1) > RANK.get(segments[-1][1], -1):
            # Absatz direkt nach einem Satzpunkt: vorigen Abschnitt aufwerten.
            segments[-1][1] = kind

    while i < n:
        char = text[i]

        if char == "\n":
            j = i
            breaks = 0
            while j < n and text[j] in " \t\r\n":
                if text[j] == "\n":
                    breaks += 1
                j += 1
            push(i, "paragraph" if breaks > 1 else "line")
            start = j
            i = j
            continue

        if char in TERMINATORS:
            end = i + 1
            while end < n and text[end] in TERMINATORS + CLOSERS:
                end += 1
            if is_sentence_end(text, i, end):
                push(end, "sentence")
            i = end
            continue

        i += 1

    push(n, "end")
    if segments:
        segments[-1][1] = "end"

    result = []
    for body, kind in segments:
        result.extend(split_long(body, kind))
    return result


def split_long(body, kind):
    """Sehr lange Saetze zusaetzlich an Kommas trennen."""
    out = []
    while len(body) > MAX_LEN * 1.6:
        cut, sep = -1, ""
        for candidate in (", ", "; ", ": ", " – ", " - "):
            k = body.rfind(candidate, 0, MAX_LEN + len(candidate))
            if k > cut:
                cut, sep = k, candidate
        if cut < 40:
            cut, sep = body.rfind(" ", 0, MAX_LEN + 1), " "
        if cut < 40:
            cut, sep = MAX_LEN, ""

        out.append((body[:cut + len(sep.rstrip())], "clause"))
        body = body[cut + len(sep):]
    out.append((body, kind))
    return out


def expand(text):
    for pattern, replacement in EXPANSIONS:
        text = re.sub(pattern, replacement, text)
    return text


def gap_ms(kind, pause, speed):
    """Pausenlaenge in Millisekunden - schneller sprechen, kuerzer pausieren."""
    return int(round(pause * FACTOR[kind] / speed))


# --------------------------------------------------------------------------
# Backends
# --------------------------------------------------------------------------

class Backend(object):
    """Gemeinsame Schnittstelle: Stimmen auflisten, sprechen, in Datei schreiben."""

    name = "?"

    def voices(self):
        """Liste von (Name, Sprachkuerzel)."""
        raise NotImplementedError

    def speak(self, segments, voice, speed, pause, out=None):
        raise NotImplementedError

    def german_voices(self):
        return [v for v in self.voices() if v[1].lower().replace("_", "-").startswith("de")]

    def pick_voice(self, wanted):
        """Stimme nach Namen suchen, sonst die erste deutsche nehmen."""
        available = self.voices()
        if wanted:
            for name, _lang in available:
                if name.lower() == wanted.lower():
                    return name
            for name, _lang in available:
                if wanted.lower() in name.lower():
                    return name
            die("Stimme %r nicht gefunden. Verfuegbare Stimmen: python3 tts.py --list-voices" % wanted)
        german = self.german_voices()
        return german[0][0] if german else None


def ssml_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_ssml(segments, speed, pause, lang="de-DE"):
    parts = ['<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="%s">' % lang]
    for body, kind in segments:
        parts.append(ssml_escape(body))
        gap = gap_ms(kind, pause, speed)
        if gap:
            parts.append('<break time="%dms"/>' % gap)
    parts.append("</speak>")
    return " ".join(parts)


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

    def speak(self, segments, voice, speed, pause, out=None):
        # say kennt eingebettete Steuerbefehle: [[slnc 400]] = 400 ms Stille.
        chunks = []
        for body, kind in segments:
            chunks.append(body.replace("[[", "").replace("]]", ""))
            gap = gap_ms(kind, pause, speed)
            if gap:
                chunks.append("[[slnc %d]]" % gap)
        script = " ".join(chunks)

        cmd = ["say", "-r", str(int(round(BASE_WPM * speed)))]
        if voice:
            cmd += ["-v", voice]
        if out:
            # say schreibt AIFF; ueber afconvert nach WAV wandeln.
            tmp = tempfile.mktemp(suffix=".aiff")
            run(cmd + ["-o", tmp, "--", script])
            run(["afconvert", "-f", "WAVE", "-d", "LEI16", tmp, out])
            os.remove(tmp)
        else:
            run(cmd + ["--", script])


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

    def speak(self, segments, voice, speed, pause, out=None):
        ssml = build_ssml(segments, speed, pause)
        script = "$s.Rate = %d;" % self._rate(speed)
        if voice:
            script += "$s.SelectVoice('%s');" % voice.replace("'", "''")
        if out:
            script += "$s.SetOutputToWaveFile('%s');" % os.path.abspath(out).replace("'", "''")
        script += "$s.SpeakSsml('%s');$s.Dispose();" % ssml.replace("'", "''")
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

    def speak(self, segments, voice, speed, pause, out=None):
        ssml = build_ssml(segments, speed, pause)
        cmd = [self.binary, "-m", "-s", str(int(round(BASE_WPM * speed))), "-v", voice or "de"]
        if out:
            cmd += ["-w", out]
        run(cmd + ["--stdin"], stdin_text=ssml)


def detect_backend():
    system = platform.system()
    if system == "Darwin" and shutil.which("say"):
        return MacSay()
    if system == "Windows" and shutil.which("powershell"):
        return WindowsSapi()
    for binary in ("espeak-ng", "espeak"):
        if shutil.which(binary):
            return Espeak(binary)
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
        epilog="Beispiel: python3 tts.py --speed 1.3 --pause 500 \"Das Paket kommt morgen an.\"",
    )
    p.add_argument("text", nargs="*", help="Der vorzulesende Text.")
    p.add_argument("-f", "--file", help="Text aus einer Datei lesen (UTF-8).")
    p.add_argument("-s", "--speed", type=float, default=1.0,
                   help="Geschwindigkeit: 1.0 = normal, 1.5 = schneller, 0.8 = langsamer (0.3-3.0).")
    p.add_argument("-p", "--pause", type=int, default=400, metavar="MS",
                   help="Pause nach einem Satz in Millisekunden (Standard 400). Absaetze bekommen "
                        "das 2,4-fache, Zeilenumbrueche das 1,4-fache. 0 laesst der Stimme ihre "
                        "eigenen, sehr knappen Pausen.")
    p.add_argument("-v", "--voice", help="Name der Stimme (siehe --list-voices).")
    p.add_argument("-o", "--out", help="In eine WAV-Datei schreiben statt abzuspielen.")
    p.add_argument("--no-expand", action="store_true",
                   help="Abkuerzungen nicht ausschreiben (z. B. -> zum Beispiel).")
    p.add_argument("-l", "--list-voices", action="store_true", help="Verfuegbare Stimmen anzeigen.")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv if argv is not None else sys.argv[1:])
    backend = detect_backend()

    if args.list_voices:
        german = backend.german_voices()
        print("Sprachausgabe: %s\n" % backend.name)
        print("Deutsche Stimmen:")
        for name, lang in german:
            print("  %-28s %s" % (name, lang))
        if not german:
            print("  (keine gefunden - bitte eine deutsche Stimme im System nachinstallieren)")
        print("\nAlle Stimmen:")
        for name, lang in backend.voices():
            print("  %-28s %s" % (name, lang))
        return 0

    if not 0.3 <= args.speed <= 3.0:
        die("Die Geschwindigkeit muss zwischen 0.3 und 3.0 liegen.")
    if not 0 <= args.pause <= 5000:
        die("Die Pause muss zwischen 0 und 5000 Millisekunden liegen.")

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

    if not text.strip():
        die("Der Text ist leer.")

    segments = segment(text)
    if not args.no_expand:
        segments = [(expand(body), kind) for body, kind in segments]

    voice = backend.pick_voice(args.voice)
    if voice is None:
        sys.stderr.write("Hinweis: keine deutsche Stimme gefunden, es wird die Standardstimme verwendet.\n")

    backend.speak(segments, voice, args.speed, args.pause, args.out)

    if args.out:
        print("Gespeichert: %s (%s, %.2fx, %d ms Satzpause)"
              % (args.out, voice or "Standardstimme", args.speed, args.pause))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

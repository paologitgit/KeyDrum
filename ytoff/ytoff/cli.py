"""ytoff -- Kommandozeile."""

from __future__ import annotations

import argparse
import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path

from . import config as cfgmod
from . import library, media, sync
from .config import Config, ConfigError, Subscription

#: yt-dlp muss aktuell bleiben: YouTube aendert die Auslieferung laufend.
STALE_AFTER_DAYS = 60


def _load(args) -> Config:
    return cfgmod.load(args.config)


# ---------------------------------------------------------------- Befehle


def cmd_init(args) -> int:
    if args.config.exists() and not args.force:
        print(f"{args.config} existiert bereits. Mit --force ueberschreiben.")
        return 1
    cfg = Config()
    cfgmod.save(cfg, args.config)
    cfg.ziel.mkdir(parents=True, exist_ok=True)
    print(f"Konfiguration angelegt: {args.config}")
    print(f"Bibliothek:             {cfg.ziel}")
    print("\nNaechster Schritt: ytoff add <kanal-url>")
    return 0


def cmd_add(args) -> int:
    cfg = _load(args)
    if any(s.url == args.url for s in cfg.kanaele):
        print("Diese URL ist bereits abonniert.")
        return 1
    cfg.kanaele.append(
        Subscription(
            url=args.url,
            name=args.name or "",
            limit_neueste=args.limit,
            ab_datum=args.since or "",
            nur_audio=args.audio,
            max_hoehe=args.height or 0,
        )
    )
    cfgmod.save(cfg, args.config)
    print(f"Abonniert: {args.name or args.url}")
    print(f"Es werden die neuesten {args.limit} Videos beruecksichtigt "
          f"(anpassbar in {args.config}).")
    return 0


def cmd_remove(args) -> int:
    cfg = _load(args)
    before = len(cfg.kanaele)
    cfg.kanaele = [s for s in cfg.kanaele if args.muster not in s.url and args.muster not in s.name]
    if len(cfg.kanaele) == before:
        print(f"Kein Abo passt auf '{args.muster}'.")
        return 1
    cfgmod.save(cfg, args.config)
    print(f"{before - len(cfg.kanaele)} Abo(s) entfernt.")
    return 0


def cmd_list(args) -> int:
    cfg = _load(args)
    if not cfg.kanaele:
        print("Noch keine Abos. Anlegen mit: ytoff add <url>")
    else:
        print("Abos:")
        for sub in cfg.kanaele:
            flags = []
            if sub.nur_audio:
                flags.append("nur Audio")
            if sub.max_hoehe:
                flags.append(f"max {sub.max_hoehe}p")
            if sub.ab_datum:
                flags.append(f"ab {sub.ab_datum}")
            suffix = f"  [{', '.join(flags)}]" if flags else ""
            print(f"  - {sub.label()}  (neueste {sub.limit_neueste}){suffix}")

    items = library.scan(cfg.ziel)
    total = sum(i.size for i in items)
    print(f"\nBibliothek: {cfg.ziel}")
    if not items:
        print("  (noch leer)")
        return 0
    for channel, (count, size) in library.by_channel(items).items():
        print(f"  {channel}: {count} Datei(en), {library.human(size)}")
    print(f"  gesamt: {len(items)} Datei(en), {library.human(total)}")
    return 0


def cmd_sync(args) -> int:
    cfg = _load(args)
    if not cfg.kanaele:
        print("Keine Abos konfiguriert. Erst 'ytoff add <url>'.")
        return 1

    subs = cfg.kanaele
    if args.only:
        subs = [s for s in subs if args.only in s.url or args.only in s.name]
        if not subs:
            print(f"Kein Abo passt auf '{args.only}'.")
            return 1

    ff = media.find()
    if not ff.usable:
        print("ffmpeg nicht gefunden -- ohne ffmpeg lassen sich Bild- und Tonspur "
              "nicht zusammenfuegen.")
        print(media.hint())
        return 1

    archived = sync.read_archive(cfg.archive_path)
    print(f"Pruefe {len(subs)} Abo(s) ...\n")

    plans = []
    for sub in subs:
        plan = sync.plan_subscription(cfg, sub, ff, archived)
        plans.append(plan)
        if plan.error:
            print(f"  {sub.label()}: FEHLER -- {_short(plan.error)}")
            continue
        size = plan.estimated_bytes(cfg)
        print(
            f"  {sub.label()}: {len(plan.pending)} neu, "
            f"{plan.already_have} bereits vorhanden, ca. {library.human(size)}"
        )
        if args.verbose:
            for entry in plan.pending:
                mark = "" if entry.duration_known else " (Dauer geschaetzt)"
                print(f"      - {entry.title}{mark}")

    pending_total = sum(len(p.pending) for p in plans)
    size_total = sum(p.estimated_bytes(cfg) for p in plans)
    guessed = sum(p.guessed_durations for p in plans)

    print(f"\nSumme: {pending_total} Video(s), geschaetzt {library.human(size_total)}")
    if guessed:
        print(f"Hinweis: bei {guessed} Video(s) war die Dauer unbekannt, "
              f"dafuer wurden je {sync.ASSUMED_DURATION_S // 60} Minuten angenommen.")
    _warn_disk(cfg.ziel, size_total)

    if pending_total == 0:
        print("Nichts zu tun.")
        return 0
    if args.dry_run:
        print("(Vorschau -- es wurde nichts geladen.)")
        return 0

    if not args.yes and sys.stdin.isatty():
        answer = input("\nHerunterladen? [j/N] ").strip().lower()
        if answer not in {"j", "ja", "y", "yes"}:
            print("Abgebrochen.")
            return 1

    failures = 0
    for plan in plans:
        if plan.error or not plan.pending:
            continue
        print(f"\n=== {plan.sub.label()} ===")
        code = sync.download_subscription(cfg, plan.sub, ff)
        if code != 0:
            failures += 1
            print(f"  {plan.sub.label()}: mit Fehlern beendet (Exitcode {code}).")

    print("\nFertig." if not failures else f"\nFertig, {failures} Abo(s) mit Fehlern.")
    print("Bei Extraktor-Fehlern zuerst 'ytoff update' ausfuehren.")
    return 1 if failures else 0


def cmd_doctor(args) -> int:
    problems = 0
    print(f"Python:   {sys.version.split()[0]}")

    try:
        import yt_dlp

        version = yt_dlp.version.__version__
        age = _version_age_days(version)
        note = ""
        if age is None:
            note = " (Alter unbekannt)"
        elif age > STALE_AFTER_DAYS:
            note = f" -- {age} Tage alt, bitte 'ytoff update' ausfuehren"
            problems += 1
        print(f"yt-dlp:   {version}{note}")
    except ImportError:
        print("yt-dlp:   FEHLT -- 'pip install yt-dlp'")
        problems += 1

    ff = media.find()
    if not ff.usable:
        print(f"ffmpeg:   FEHLT -- {media.hint()}")
        problems += 1
    elif not ff.complete:
        print(f"ffmpeg:   {ff.ffmpeg} (mitgeliefert, ohne ffprobe)")
        print(f"          Zusammenfuegen geht, Kapitel/SponsorBlock brauchen ffprobe. {media.hint()}")
    else:
        print(f"ffmpeg:   {ff.ffmpeg}")

    try:
        cfg = _load(args)
        print(f"Konfig:   {args.config} ({len(cfg.kanaele)} Abo(s))")
        free = shutil.disk_usage(_existing_parent(cfg.ziel)).free
        print(f"Ziel:     {cfg.ziel} -- {library.human(free)} frei")
    except ConfigError as exc:
        print(f"Konfig:   PROBLEM -- {exc}")
        problems += 1

    print("\nAlles in Ordnung." if not problems else f"\n{problems} Punkt(e) zu beheben.")
    return 1 if problems else 0


def cmd_update(args) -> int:
    """yt-dlp aktuell halten ist Wartung, kein Extra: eine veraltete Version
    bricht typischerweise binnen Monaten."""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
    print("Fuehre aus:", " ".join(cmd))
    return subprocess.call(cmd)


# ---------------------------------------------------------------- Helfer


def _short(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _existing_parent(path: Path) -> Path:
    while not path.exists() and path != path.parent:
        path = path.parent
    return path


def _warn_disk(target: Path, needed: int) -> None:
    free = shutil.disk_usage(_existing_parent(target)).free
    print(f"Frei auf dem Zieldatentraeger: {library.human(free)}")
    if needed > free * 0.9:
        print("ACHTUNG: Die Schaetzung liegt nahe am freien Speicher oder darueber.")


def _version_age_days(version: str) -> int | None:
    try:
        year, month, day = (int(p) for p in version.split(".")[:3])
        released = dt.date(year, month, day)
    except (ValueError, TypeError):
        return None
    return (dt.date.today() - released).days


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytoff",
        description="YouTube-Videos und Kanaele fuer den privaten Offline-Gebrauch archivieren.",
    )
    parser.add_argument(
        "--config", type=Path, default=cfgmod.CONFIG_PATH, help="Pfad zur config.yaml"
    )
    sub = parser.add_subparsers(dest="befehl", required=True)

    p = sub.add_parser("init", help="Konfiguration anlegen")
    p.add_argument("--force", action="store_true", help="vorhandene Konfiguration ueberschreiben")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("add", help="Kanal, Playlist oder einzelnes Video abonnieren")
    p.add_argument("url")
    p.add_argument("--name", help="Anzeigename")
    p.add_argument("--limit", type=int, default=20, help="nur die neuesten N Videos (Vorgabe 20)")
    p.add_argument("--since", metavar="JJJJMMTT", help="nur Videos ab diesem Datum")
    p.add_argument("--audio", action="store_true", help="nur Tonspur (m4a)")
    p.add_argument("--height", type=int, help="Hoehenlimit nur fuer dieses Abo")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("remove", help="Abo entfernen")
    p.add_argument("muster", help="Teilstring von URL oder Name")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("list", help="Abos und Bibliothek anzeigen")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("sync", help="fehlende Videos holen")
    p.add_argument("--only", help="nur Abos, die auf diesen Teilstring passen")
    p.add_argument("-n", "--dry-run", action="store_true", help="nur Vorschau")
    p.add_argument("-y", "--yes", action="store_true", help="ohne Rueckfrage laden")
    p.add_argument("-v", "--verbose", action="store_true", help="jeden Titel auflisten")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("doctor", help="Umgebung pruefen")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("update", help="yt-dlp aktualisieren")
    p.set_defaults(func=cmd_update)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"Konfigurationsfehler: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nAbgebrochen.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

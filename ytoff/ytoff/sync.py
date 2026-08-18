"""Sync-Engine: yt-dlp-Optionen bauen, Vorschau rechnen, Abos abarbeiten."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import Config, Subscription
from .media import FFmpegInfo

#: Grobe Groessenannahme in Gigabyte pro Stunde Material, nach Hoehe.
#: Reine Schaetzung fuer die Vorschau -- YouTube liefert je nach Codec
#: (VP9/AV1) und Bewegtheit deutlich abweichende Bitraten.
GB_PER_HOUR = {2160: 11.0, 1440: 4.0, 1080: 1.5, 720: 0.55, 480: 0.3}
AUDIO_GB_PER_HOUR = 0.06

#: Wenn yt-dlp bei der flachen Abfrage keine Dauer liefert, rechnen wir
#: mit diesem Wert weiter, statt das Video aus der Schaetzung zu kippen.
ASSUMED_DURATION_S = 12 * 60


def format_selector(height: int, audio_only: bool) -> str:
    if audio_only:
        return "bestaudio/best"
    return (
        f"bestvideo[height<={height}]+bestaudio/"
        f"best[height<={height}]/best"
    )


def gb_per_hour(height: int, audio_only: bool) -> float:
    if audio_only:
        return AUDIO_GB_PER_HOUR
    for tier in sorted(GB_PER_HOUR, reverse=True):
        if height >= tier:
            return GB_PER_HOUR[tier]
    return GB_PER_HOUR[480]


def estimate_bytes(duration_s: float, height: int, audio_only: bool) -> int:
    return int(duration_s / 3600 * gb_per_hour(height, audio_only) * 1024**3)


def read_archive(path: Path) -> set[str]:
    """yt-dlp schreibt Zeilen der Form '<extractor> <id>'."""
    if not path.exists():
        return set()
    ids = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            ids.add(parts[-1])
    return ids


def outtmpl(cfg: Config) -> str:
    return str(
        cfg.ziel
        / "%(channel,uploader,playlist_title|Unbekannt)s"
        / "%(upload_date>%Y-%m-%d,release_date>%Y-%m-%d|0000-00-00)s"
          " - %(title)s [%(id)s].%(ext)s"
    )


def build_opts(
    cfg: Config,
    sub: Subscription,
    ffmpeg: FFmpegInfo,
    *,
    flat: bool = False,
) -> dict:
    """Baut das Optionen-Dict fuer yt-dlp. `flat=True` liefert die Variante
    fuer die Vorschau: nur Metadaten der Playlist, kein Download."""
    height = cfg.height_for(sub)

    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": flat,
        "ignoreerrors": True,   # ein kaputtes Video kippt nicht den ganzen Lauf
        "sleep_interval_requests": cfg.tempo.pause_zwischen_anfragen,
        "retries": 5,
        "fragment_retries": 10,
    }

    if sub.limit_neueste:
        opts["playlistend"] = sub.limit_neueste
    if sub.ab_datum:
        opts["daterange"] = _daterange(sub.ab_datum)

    if flat:
        opts["extract_flat"] = "in_playlist"
        opts["skip_download"] = True
        return opts

    opts.update(
        {
            "format": format_selector(height, sub.nur_audio),
            "outtmpl": {"default": outtmpl(cfg)},
            "download_archive": str(cfg.archive_path),
            "concurrent_fragment_downloads": cfg.tempo.parallele_fragmente,
            "trim_file_name": 200,
            "windowsfilenames": False,
            "postprocessors": _postprocessors(cfg, sub),
        }
    )
    if not sub.nur_audio:
        opts["merge_output_format"] = "mp4"
    if cfg.extras.untertitel:
        opts["writesubtitles"] = True
        opts["subtitleslangs"] = list(cfg.extras.untertitel)
    if cfg.extras.thumbnail:
        opts["writethumbnail"] = True
    if ffmpeg.usable:
        opts["ffmpeg_location"] = str(ffmpeg.ffmpeg)
    return opts


def _daterange(ab_datum: str):
    from yt_dlp.utils import DateRange

    return DateRange(ab_datum, None)


def _postprocessors(cfg: Config, sub: Subscription) -> list[dict]:
    """Reihenfolge entspricht der von yt-dlp selbst verwendeten: erst Segmente
    entfernen, dann konvertieren, dann einbetten."""
    pps: list[dict] = []
    if cfg.extras.sponsor_entfernen:
        cats = set(cfg.extras.sponsor_entfernen)
        pps.append({"key": "SponsorBlock", "categories": cats, "when": "after_filter"})
        pps.append({"key": "ModifyChapters", "remove_sponsor_segments": cats})
    if sub.nur_audio:
        pps.append(
            {"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "0"}
        )
    if cfg.extras.untertitel and not sub.nur_audio:
        pps.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False})
    if cfg.extras.metadaten:
        pps.append(
            {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": cfg.extras.kapitel}
        )
    if cfg.extras.thumbnail:
        pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
    return pps


@dataclass
class PlanEntry:
    video_id: str
    title: str
    duration_s: float
    duration_known: bool


@dataclass
class SubscriptionPlan:
    sub: Subscription
    pending: list[PlanEntry] = field(default_factory=list)
    already_have: int = 0
    error: str = ""

    def estimated_bytes(self, cfg: Config) -> int:
        height = cfg.height_for(self.sub)
        return sum(
            estimate_bytes(e.duration_s, height, self.sub.nur_audio) for e in self.pending
        )

    @property
    def guessed_durations(self) -> int:
        return sum(1 for e in self.pending if not e.duration_known)


def plan_subscription(
    cfg: Config, sub: Subscription, ffmpeg: FFmpegInfo, archived: set[str]
) -> SubscriptionPlan:
    """Fragt die Playlist/den Kanal flach ab und meldet, was noch fehlt.

    Hinweis: bei der flachen Abfrage liefert YouTube kein Upload-Datum mit,
    'ab_datum' greift daher erst beim eigentlichen Download. Die Vorschau kann
    also mehr Videos zeigen, als am Ende geladen werden."""
    from yt_dlp import YoutubeDL

    result = SubscriptionPlan(sub=sub)
    try:
        with YoutubeDL(build_opts(cfg, sub, ffmpeg, flat=True)) as ydl:
            info = ydl.extract_info(sub.url, download=False)
    except Exception as exc:  # yt-dlp wirft eine breite Palette
        result.error = str(exc)
        return result

    if info is None:
        result.error = "Keine Daten erhalten (Kanal privat, geloescht oder Extraktor veraltet?)"
        return result

    entries = info.get("entries")
    if entries is None:
        entries = [info]  # Einzelvideo statt Playlist

    for entry in entries:
        if not entry:
            continue
        video_id = entry.get("id")
        if not video_id:
            continue
        if video_id in archived:
            result.already_have += 1
            continue
        duration = entry.get("duration")
        result.pending.append(
            PlanEntry(
                video_id=video_id,
                title=entry.get("title") or video_id,
                duration_s=float(duration) if duration else float(ASSUMED_DURATION_S),
                duration_known=bool(duration),
            )
        )
    return result


def download_subscription(cfg: Config, sub: Subscription, ffmpeg: FFmpegInfo) -> int:
    """Laedt alles Fehlende des Abos. Rueckgabe: yt-dlp-Exitcode (0 = ok)."""
    from yt_dlp import YoutubeDL

    cfg.ziel.mkdir(parents=True, exist_ok=True)
    opts = build_opts(cfg, sub, ffmpeg)
    opts["quiet"] = False
    opts["no_warnings"] = False
    with YoutubeDL(opts) as ydl:
        return ydl.download([sub.url])

"""ffmpeg finden. Ohne ffmpeg kann yt-dlp Video- und Tonspur nicht zusammenfuegen."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FFmpegInfo:
    ffmpeg: Path | None
    ffprobe: Path | None
    source: str  # "system" | "imageio" | "fehlt"

    @property
    def usable(self) -> bool:
        return self.ffmpeg is not None

    @property
    def complete(self) -> bool:
        """ffprobe fehlt beim mitgelieferten Binary. Zusammenfuegen geht trotzdem,
        einzelne Nachbearbeitungsschritte (Kapitel, SponsorBlock) brauchen es aber."""
        return self.ffmpeg is not None and self.ffprobe is not None


def find() -> FFmpegInfo:
    system = shutil.which("ffmpeg")
    if system:
        probe = shutil.which("ffprobe")
        return FFmpegInfo(Path(system), Path(probe) if probe else None, "system")

    try:
        import imageio_ffmpeg
    except ImportError:
        return FFmpegInfo(None, None, "fehlt")

    try:
        bundled = Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        return FFmpegInfo(None, None, "fehlt")
    return FFmpegInfo(bundled, None, "imageio")


def hint() -> str:
    return "Empfohlen auf macOS: 'brew install ffmpeg' (bringt auch ffprobe mit)."

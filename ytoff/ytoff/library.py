"""Bestandsaufnahme dessen, was schon auf der Platte liegt."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MEDIA_SUFFIXES = {".mp4", ".mkv", ".webm", ".m4a", ".mp3", ".opus", ".mov"}
ID_PATTERN = re.compile(r"\[([A-Za-z0-9_-]{6,})\]\.[^.]+$")


@dataclass
class Item:
    path: Path
    channel: str
    video_id: str
    size: int


def scan(root: Path) -> list[Item]:
    if not root.exists():
        return []
    items = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in MEDIA_SUFFIXES:
            continue
        match = ID_PATTERN.search(path.name)
        channel = path.parent.name if path.parent != root else "(ohne Kanal)"
        items.append(
            Item(
                path=path,
                channel=channel,
                video_id=match.group(1) if match else "",
                size=path.stat().st_size,
            )
        )
    return items


def by_channel(items: list[Item]) -> dict[str, tuple[int, int]]:
    """Kanal -> (Anzahl, Bytes)."""
    out: dict[str, tuple[int, int]] = {}
    for item in items:
        count, size = out.get(item.channel, (0, 0))
        out[item.channel] = (count + 1, size + item.size)
    return dict(sorted(out.items()))


def human(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024 or unit == "TB":
            return f"{num_bytes:.1f} {unit}" if unit != "B" else f"{int(num_bytes)} B"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"

from pathlib import Path

import pytest

from ytoff import config as cfgmod
from ytoff import sync
from ytoff.media import FFmpegInfo

FF = FFmpegInfo(Path("/usr/bin/ffmpeg"), Path("/usr/bin/ffprobe"), "system")


def base_cfg(tmp_path, **over):
    raw = {"ziel": str(tmp_path), **over}
    return cfgmod.parse(raw)


# -------------------------------------------------- Formatwahl und Schaetzung


def test_format_selector_deckelt_hoehe():
    fmt = sync.format_selector(720, audio_only=False)
    assert "height<=720" in fmt
    assert fmt.endswith("/best")


def test_format_selector_audio():
    assert sync.format_selector(1080, audio_only=True) == "bestaudio/best"


@pytest.mark.parametrize(
    "height,expected", [(2160, 11.0), (1440, 4.0), (1080, 1.5), (720, 0.55), (360, 0.3)]
)
def test_gb_pro_stunde_stufen(height, expected):
    assert sync.gb_per_hour(height, False) == expected


def test_audio_ist_deutlich_kleiner():
    assert sync.gb_per_hour(1080, True) < sync.gb_per_hour(480, False)


def test_schaetzung_skaliert_mit_dauer(tmp_path):
    eine_stunde = sync.estimate_bytes(3600, 1080, False)
    assert eine_stunde == pytest.approx(1.5 * 1024**3, rel=0.01)
    assert sync.estimate_bytes(7200, 1080, False) == 2 * eine_stunde
    assert sync.estimate_bytes(0, 1080, False) == 0


# -------------------------------------------------- Archiv


def test_archiv_liest_ids(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("youtube abc123\nyoutube def456\n", encoding="utf-8")
    assert sync.read_archive(path) == {"abc123", "def456"}


def test_archiv_ignoriert_muell_und_fehlt(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("youtube abc123\n\nkaputt\n", encoding="utf-8")
    assert sync.read_archive(path) == {"abc123"}
    assert sync.read_archive(tmp_path / "nix.txt") == set()


# -------------------------------------------------- yt-dlp-Optionen


def test_build_opts_video(tmp_path):
    cfg = base_cfg(tmp_path)
    sub = cfgmod.Subscription(url="u", limit_neueste=7)
    opts = sync.build_opts(cfg, sub, FF)
    assert opts["playlistend"] == 7
    assert opts["merge_output_format"] == "mp4"
    assert opts["download_archive"] == str(cfg.archive_path)
    assert opts["ffmpeg_location"] == "/usr/bin/ffmpeg"
    assert opts["ignoreerrors"] is True
    assert opts["sleep_interval_requests"] == 0.75


def test_build_opts_audio_hat_kein_merge(tmp_path):
    cfg = base_cfg(tmp_path)
    sub = cfgmod.Subscription(url="u", nur_audio=True)
    opts = sync.build_opts(cfg, sub, FF)
    assert "merge_output_format" not in opts
    keys = [pp["key"] for pp in opts["postprocessors"]]
    assert "FFmpegExtractAudio" in keys
    assert "FFmpegEmbedSubtitle" not in keys  # in eine m4a gehoert kein Untertitel


def test_sponsorblock_erzeugt_beide_schritte(tmp_path):
    cfg = base_cfg(tmp_path, extras={"sponsor_entfernen": ["sponsor", "intro"]})
    opts = sync.build_opts(cfg, cfgmod.Subscription(url="u"), FF)
    keys = [pp["key"] for pp in opts["postprocessors"]]
    assert keys[:2] == ["SponsorBlock", "ModifyChapters"]


def test_flache_variante_laedt_nichts(tmp_path):
    cfg = base_cfg(tmp_path)
    opts = sync.build_opts(cfg, cfgmod.Subscription(url="u"), FF, flat=True)
    assert opts["skip_download"] is True
    assert opts["extract_flat"] == "in_playlist"
    assert "format" not in opts


def test_ab_datum_wird_zur_daterange(tmp_path):
    cfg = base_cfg(tmp_path)
    sub = cfgmod.Subscription(url="u", ab_datum="20250101")
    opts = sync.build_opts(cfg, sub, FF)
    assert "20250101" in str(opts["daterange"].start).replace("-", "")


# -------------------------------------------------- Dateinamen-Schablone
# yt-dlp rendert die Schablone hier ohne Netz -- damit ist der fehleranfaellige
# Teil (Feldnamen, Datumsformat, Rueckfallwerte) offline geprueft.


def render(cfg, info):
    from yt_dlp import YoutubeDL

    with YoutubeDL({"outtmpl": {"default": sync.outtmpl(cfg)}, "quiet": True}) as ydl:
        return Path(ydl.prepare_filename(info))


def test_dateiname_normalfall(tmp_path):
    cfg = base_cfg(tmp_path)
    name = render(cfg, {
        "id": "abc123", "title": "Ein Test", "ext": "mp4",
        "channel": "Mein Kanal", "upload_date": "20250314",
    })
    assert name.parent.name == "Mein Kanal"
    assert name.name == "2025-03-14 - Ein Test [abc123].mp4"


def test_dateiname_faellt_auf_uploader_zurueck(tmp_path):
    cfg = base_cfg(tmp_path)
    name = render(cfg, {
        "id": "x", "title": "T", "ext": "mp4",
        "uploader": "Uploader X", "upload_date": "20250101",
    })
    assert name.parent.name == "Uploader X"


def test_dateiname_ohne_kanal_und_datum(tmp_path):
    cfg = base_cfg(tmp_path)
    name = render(cfg, {"id": "x", "title": "T", "ext": "mp4"})
    assert name.parent.name == "Unbekannt"
    assert name.name.startswith("0000-00-00 - T")


def test_dateiname_liegt_unter_dem_ziel(tmp_path):
    cfg = base_cfg(tmp_path)
    name = render(cfg, {"id": "x", "title": "T", "ext": "mp4", "channel": "C"})
    assert str(name).startswith(str(tmp_path))


def test_schraegstrich_im_titel_erzeugt_keinen_unterordner(tmp_path):
    cfg = base_cfg(tmp_path)
    name = render(cfg, {
        "id": "x", "title": "AC/DC live", "ext": "mp4", "channel": "C",
        "upload_date": "20250101",
    })
    assert name.parent.name == "C"          # genau eine Ebene unter dem Ziel
    assert name.parent.parent == tmp_path

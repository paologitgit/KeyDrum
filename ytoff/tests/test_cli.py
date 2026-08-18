from pathlib import Path

import pytest
import yt_dlp

from ytoff import cli, library, sync
from ytoff import config as cfgmod
from ytoff.media import FFmpegInfo

FF = FFmpegInfo(Path("/usr/bin/ffmpeg"), Path("/usr/bin/ffprobe"), "system")


class FakeYDL:
    """Ersetzt yt_dlp.YoutubeDL, damit der Planer ohne Netz pruefbar ist."""

    payload: object = None
    raises: Exception | None = None

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download=False):
        if FakeYDL.raises:
            raise FakeYDL.raises
        return FakeYDL.payload


@pytest.fixture
def fake_ydl(monkeypatch):
    FakeYDL.payload = None
    FakeYDL.raises = None
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYDL)
    return FakeYDL


# -------------------------------------------------- Planer


def test_plan_trennt_neu_von_vorhanden(tmp_path, fake_ydl):
    fake_ydl.payload = {"entries": [
        {"id": "a", "title": "Alt", "duration": 600},
        {"id": "b", "title": "Neu", "duration": 1200},
        None,
        {"title": "ohne id"},
    ]}
    cfg = cfgmod.parse({"ziel": str(tmp_path)})
    sub = cfgmod.Subscription(url="u")
    plan = sync.plan_subscription(cfg, sub, FF, archived={"a"})
    assert plan.already_have == 1
    assert [e.video_id for e in plan.pending] == ["b"]
    assert plan.estimated_bytes(cfg) == sync.estimate_bytes(1200, 1080, False)


def test_plan_schaetzt_fehlende_dauer(tmp_path, fake_ydl):
    fake_ydl.payload = {"entries": [{"id": "a", "title": "T"}]}
    cfg = cfgmod.parse({"ziel": str(tmp_path)})
    plan = sync.plan_subscription(cfg, cfgmod.Subscription(url="u"), FF, set())
    assert plan.guessed_durations == 1
    assert plan.pending[0].duration_s == sync.ASSUMED_DURATION_S


def test_plan_einzelvideo_ohne_entries(tmp_path, fake_ydl):
    fake_ydl.payload = {"id": "solo", "title": "Solo", "duration": 60}
    cfg = cfgmod.parse({"ziel": str(tmp_path)})
    plan = sync.plan_subscription(cfg, cfgmod.Subscription(url="u"), FF, set())
    assert [e.video_id for e in plan.pending] == ["solo"]


def test_plan_faengt_fehler_ab(tmp_path, fake_ydl):
    fake_ydl.raises = RuntimeError("Extraktor kaputt")
    cfg = cfgmod.parse({"ziel": str(tmp_path)})
    plan = sync.plan_subscription(cfg, cfgmod.Subscription(url="u"), FF, set())
    assert "Extraktor kaputt" in plan.error
    assert plan.pending == []


def test_plan_meldet_leere_antwort(tmp_path, fake_ydl):
    fake_ydl.payload = None
    cfg = cfgmod.parse({"ziel": str(tmp_path)})
    plan = sync.plan_subscription(cfg, cfgmod.Subscription(url="u"), FF, set())
    assert plan.error


# -------------------------------------------------- Bibliothek


def test_scan_liest_kanal_und_id(tmp_path):
    kanal = tmp_path / "Mein Kanal"
    kanal.mkdir()
    (kanal / "2025-01-01 - Titel [abc123].mp4").write_bytes(b"x" * 100)
    (kanal / "notiz.txt").write_text("kein Medium")
    items = library.scan(tmp_path)
    assert len(items) == 1
    assert items[0].channel == "Mein Kanal"
    assert items[0].video_id == "abc123"
    assert library.by_channel(items) == {"Mein Kanal": (1, 100)}


def test_scan_leeres_ziel(tmp_path):
    assert library.scan(tmp_path / "gibtsnicht") == []


def test_human():
    assert library.human(512) == "512 B"
    assert library.human(1536) == "1.5 KB"
    assert library.human(3 * 1024**3) == "3.0 GB"


# -------------------------------------------------- CLI


def test_init_add_list(tmp_path, capsys):
    conf = tmp_path / "config.yaml"
    ziel = tmp_path / "lib"

    assert cli.main(["--config", str(conf), "init"]) == 0
    cfg = cfgmod.load(conf)
    cfg.ziel = ziel
    cfgmod.save(cfg, conf)

    assert cli.main(["--config", str(conf), "add", "https://x/@a", "--name", "A",
                     "--limit", "5", "--audio"]) == 0
    assert cli.main(["--config", str(conf), "list"]) == 0
    out = capsys.readouterr().out
    assert "A" in out and "nur Audio" in out and "neueste 5" in out

    # zweites Mal dieselbe URL: abgelehnt
    assert cli.main(["--config", str(conf), "add", "https://x/@a"]) == 1


def test_init_ueberschreibt_nicht_ungefragt(tmp_path):
    conf = tmp_path / "config.yaml"
    assert cli.main(["--config", str(conf), "init"]) == 0
    assert cli.main(["--config", str(conf), "init"]) == 1
    assert cli.main(["--config", str(conf), "init", "--force"]) == 0


def test_remove(tmp_path):
    conf = tmp_path / "config.yaml"
    cli.main(["--config", str(conf), "init"])
    cli.main(["--config", str(conf), "add", "https://x/@a"])
    assert cli.main(["--config", str(conf), "remove", "keintreffer"]) == 1
    assert cli.main(["--config", str(conf), "remove", "@a"]) == 0
    assert cfgmod.load(conf).kanaele == []


def test_sync_dry_run_laedt_nichts(tmp_path, capsys, monkeypatch, fake_ydl):
    conf = tmp_path / "config.yaml"
    cli.main(["--config", str(conf), "init"])
    cfg = cfgmod.load(conf)
    cfg.ziel = tmp_path / "lib"
    cfg.kanaele.append(cfgmod.Subscription(url="https://x/@a", name="A"))
    cfgmod.save(cfg, conf)

    fake_ydl.payload = {"entries": [{"id": "neu", "title": "Neu", "duration": 3600}]}
    monkeypatch.setattr(cli.media, "find", lambda: FF)

    def boom(*a, **kw):
        raise AssertionError("dry-run darf nichts laden")

    monkeypatch.setattr(cli.sync, "download_subscription", boom)

    assert cli.main(["--config", str(conf), "sync", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "1 Video(s)" in out
    assert "1.5 GB" in out
    assert "Vorschau" in out


def test_sync_ohne_ffmpeg_bricht_ab(tmp_path, capsys, monkeypatch):
    conf = tmp_path / "config.yaml"
    cli.main(["--config", str(conf), "init"])
    cfg = cfgmod.load(conf)
    cfg.kanaele.append(cfgmod.Subscription(url="https://x/@a"))
    cfgmod.save(cfg, conf)
    monkeypatch.setattr(cli.media, "find", lambda: FFmpegInfo(None, None, "fehlt"))
    assert cli.main(["--config", str(conf), "sync"]) == 1
    assert "brew install ffmpeg" in capsys.readouterr().out


def test_sync_ohne_abos(tmp_path):
    conf = tmp_path / "config.yaml"
    cli.main(["--config", str(conf), "init"])
    assert cli.main(["--config", str(conf), "sync"]) == 1


def test_konfigurationsfehler_gibt_code_2(tmp_path, capsys):
    conf = tmp_path / "config.yaml"
    conf.write_text("max_hoehe: 1080\nquality: 3\n", encoding="utf-8")
    assert cli.main(["--config", str(conf), "list"]) == 2
    assert "Konfigurationsfehler" in capsys.readouterr().err


def test_doctor_meldet_veraltetes_ytdlp(tmp_path, monkeypatch, capsys):
    conf = tmp_path / "config.yaml"
    cli.main(["--config", str(conf), "init"])
    monkeypatch.setattr(yt_dlp.version, "__version__", "2020.01.01")
    assert cli.main(["--config", str(conf), "doctor"]) == 1
    assert "ytoff update" in capsys.readouterr().out


def test_version_alter():
    assert cli._version_age_days("kaputt") is None
    assert cli._version_age_days("2020.01.01") > 1000

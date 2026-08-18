import pytest
import yaml

from ytoff import config as cfgmod
from ytoff.config import Config, ConfigError, Subscription


def test_defaults_roundtrip(tmp_path):
    cfg = Config()
    cfg.kanaele.append(Subscription(url="https://x/@a", name="A", nur_audio=True))
    path = tmp_path / "config.yaml"
    cfgmod.save(cfg, path)
    back = cfgmod.load(path)
    assert back.max_hoehe == cfg.max_hoehe
    assert back.ziel == cfg.ziel
    assert [s.url for s in back.kanaele] == ["https://x/@a"]
    assert back.kanaele[0].nur_audio is True


def test_kanal_als_blosse_url():
    cfg = cfgmod.parse({"kanaele": ["https://x/@a"]})
    assert cfg.kanaele[0].url == "https://x/@a"
    assert cfg.kanaele[0].limit_neueste == 20


def test_vertippter_schluessel_faellt_auf():
    with pytest.raises(ConfigError, match="Unbekannte Schluessel"):
        cfgmod.parse({"quality": 1080})
    with pytest.raises(ConfigError, match="unbekannte Schluessel"):
        cfgmod.parse({"kanaele": [{"url": "u", "limit": 5}]})


def test_datum_wird_geprueft():
    with pytest.raises(ConfigError, match="JJJJMMTT"):
        cfgmod.parse({"kanaele": [{"url": "u", "ab_datum": "2025-01-01"}]})
    cfgmod.parse({"kanaele": [{"url": "u", "ab_datum": "20250101"}]})


def test_unbekannte_sponsor_kategorie():
    with pytest.raises(ConfigError, match="SponsorBlock"):
        cfgmod.parse({"extras": {"sponsor_entfernen": ["werbung"]}})
    cfg = cfgmod.parse({"extras": {"sponsor_entfernen": "sponsor"}})
    assert cfg.extras.sponsor_entfernen == ["sponsor"]


def test_kanal_ohne_url():
    with pytest.raises(ConfigError, match="keine 'url'"):
        cfgmod.parse({"kanaele": [{"name": "A"}]})


def test_hoehe_pro_abo_ueberschreibt_global():
    cfg = cfgmod.parse({"max_hoehe": 1080, "kanaele": [{"url": "u", "max_hoehe": 480}]})
    assert cfg.height_for(cfg.kanaele[0]) == 480
    assert cfg.height_for(Subscription(url="v")) == 1080


def test_archiv_liegt_in_der_bibliothek(tmp_path):
    cfg = cfgmod.parse({"ziel": str(tmp_path)})
    assert cfg.archive_path.parent == tmp_path


def test_fehlende_datei_meldet_init(tmp_path):
    with pytest.raises(ConfigError, match="ytoff init"):
        cfgmod.load(tmp_path / "gibtsnicht.yaml")


def test_kaputtes_yaml(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text("kanaele: [\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="gueltiges YAML"):
        cfgmod.load(path)

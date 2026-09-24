import pytest
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.infrastructure.config.config_loader import (
    load_settings,
    save_settings,
)


def test_roundtrip(tmp_path):
    path = tmp_path / "nested" / "settings.json"
    settings = Settings(folders={"Тест": "/tmp/certs"}, warning_days=30)
    save_settings(settings, path)
    assert load_settings(path) == settings


def test_bad_config_not_overwritten(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{broken")
    with pytest.raises(ValueError):
        load_settings(path)
    assert path.read_text() == "{broken"


@pytest.mark.parametrize(
    "kwargs", [{"warning_days": -1}, {"check_interval": 0}, {"folders": []}]
)
def test_validate_settings(kwargs):
    with pytest.raises(ValueError):
        Settings(**kwargs)

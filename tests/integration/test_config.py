import pytest

from certificate_analyzer.infrastructure.config.config_loader import (
    load_settings,
    save_settings,
)
from certificate_analyzer.infrastructure.config.settings import Settings


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


def test_environment_defaults_and_explicit_settings_take_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv("CERTIFICATE_ANALYZER_WARNING_DAYS", "12")
    monkeypatch.setenv("CERTIFICATE_ANALYZER_CHECK_INTERVAL", "180")
    monkeypatch.setenv("CERTIFICATE_ANALYZER_NOTIFICATION_URLS", '["json://localhost:9999"]')
    settings = load_settings(tmp_path / "absent.json")
    assert settings.warning_days == 12
    assert settings.check_interval == 180
    assert settings.notification_urls == ["json://localhost:9999"]
    path = tmp_path / "settings.json"
    save_settings(Settings(warning_days=40, notification_urls=[]), path)
    assert load_settings(path).warning_days == 40
    assert load_settings(path).notification_urls == []


@pytest.mark.parametrize("kwargs", [{"warning_days": True}, {"warning_days": "12"}, {"check_interval": 1.5}, {"database_path": " "}, {"notification_urls": ["invalid://bad"]}])
def test_settings_reject_invalid_values(kwargs):
    with pytest.raises(ValueError):
        Settings(**kwargs)


def test_legacy_json_and_validated_updates(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"folders": {}, "warning_days": 20, "old_unknown_option": true}')
    settings = load_settings(path)
    assert settings.warning_days == 20
    assert settings.notification_urls == []
    with pytest.raises(ValueError):
        settings.updated(check_interval=0)
    assert settings.check_interval > 0
    save_settings(settings.updated(notification_urls=["json://localhost:9999"]), path)
    assert load_settings(path).notification_urls == ["json://localhost:9999"]


def test_profile_paths_preserve_override_and_existing_profile(tmp_path, monkeypatch):
    from pathlib import Path
    from certificate_analyzer.infrastructure.config import paths

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    standard = tmp_path / "standard-profile"
    monkeypatch.setattr(paths, "user_data_path", lambda *args, **kwargs: standard)
    override = tmp_path / "custom"
    monkeypatch.setenv("CERTIFICATE_ANALYZER_HOME", str(override))
    assert paths.config_dir() == override
    monkeypatch.delenv("CERTIFICATE_ANALYZER_HOME")
    assert paths.config_dir() == standard
    assert not standard.exists()
    legacy = tmp_path / ".certificate-analyzer"
    legacy.mkdir()
    assert paths.config_dir() == legacy

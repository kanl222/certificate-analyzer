from dataclasses import asdict, fields
from pathlib import Path
from certificate_analyzer.infrastructure.config.paths import config_dir
from certificate_analyzer.infrastructure.config.settings import Settings
from certificate_analyzer.infrastructure.persistence.json_storage import (
    read_json,
    write_json,
)


def load_settings(path=None):
    path = Path(path) if path else config_dir() / "settings.json"
    data = read_json(path, None)
    if data is None:
        legacy = read_json(Path.home() / "cert_analyzer_config.json", None)
        return Settings(folders=legacy) if legacy is not None else Settings()
    if not isinstance(data, dict):
        raise ValueError("Конфигурация должна содержать JSON-объект")
    known = {f.name for f in fields(Settings)}
    return Settings(**{k: v for k, v in data.items() if k in known})


def save_settings(settings, path=None):
    write_json(path or config_dir() / "settings.json", asdict(settings))


def load_config():
    return load_settings().folders


def save_config(config):
    settings = load_settings()
    settings.folders = dict(config)
    save_settings(settings)
    return True

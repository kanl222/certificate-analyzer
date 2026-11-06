import os
from pathlib import Path

from platformdirs import user_data_path


def config_dir() -> Path:
    override = os.environ.get("CERTIFICATE_ANALYZER_HOME")
    if override:
        return Path(override).expanduser()
    legacy = Path.home() / ".certificate-analyzer"
    if legacy.is_dir():
        return legacy
    return user_data_path("certificate-analyzer", appauthor=False)


def notification_config_path() -> Path:
    path = config_dir() / "notification_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

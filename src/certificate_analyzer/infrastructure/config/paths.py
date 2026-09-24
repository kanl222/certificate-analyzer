import os
from pathlib import Path


def config_dir() -> Path:
    override = os.environ.get("CERTIFICATE_ANALYZER_HOME")
    return (
        Path(override).expanduser()
        if override
        else Path.home() / ".certificate-analyzer"
    )


def notification_config_path() -> Path:
    path = config_dir() / "notification_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

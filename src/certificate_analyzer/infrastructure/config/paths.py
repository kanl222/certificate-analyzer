"""Пути конфигурации, профиля данных и каталогов настроек приложения."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_data_path


def config_dir() -> Path:
    """Определяет базовый каталог профиля и данных приложения с учётом приоритетов.

    Порядок: CERTIFICATE_ANALYZER_HOME -> существующий ~/.certificate-analyzer -> user_data_path.

    Returns:
        Path: Путь к каталогу конфигурации и данных.
    """
    override = os.environ.get("CERTIFICATE_ANALYZER_HOME")
    if override:
        return Path(override).expanduser()
    legacy = Path.home() / ".certificate-analyzer"
    if legacy.is_dir():
        return legacy
    return user_data_path("certificate-analyzer", appauthor=False)


def notification_config_path() -> Path:
    """Возвращает путь к файлу настроек уведомлений.

    Returns:
        Path: Путь к notification_config.json.
    """
    path = config_dir() / "notification_config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

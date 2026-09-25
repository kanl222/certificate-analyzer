"""Платформозависимые сервисы и адаптеры операционной системы."""

from certificate_analyzer.infrastructure.platform.base import (
    PlatformFileManager,
    get_platform_file_manager,
    open_path,
)

__all__ = ["PlatformFileManager", "get_platform_file_manager", "open_path"]

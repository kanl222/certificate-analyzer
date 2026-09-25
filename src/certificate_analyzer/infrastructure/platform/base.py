"""Базовые интерфейсы и классы для работы с файловой системой платформы."""

import sys
from pathlib import Path
from typing import Protocol


class PlatformFileManager(Protocol):
    """Абстрактный интерфейс для взаимодействия с файлами на уровне ОС."""

    def open_file(self, path: str | Path) -> None:
        """Открывает файл в ассоциированном приложении операционной системы.

        Args:
            path: Путь к открываемому файлу.

        Raises:
            FileNotFoundError: Если файл не существует.
            OSError: При ошибке открытия файла.
        """
        ...

    def reveal_file(self, path: str | Path) -> None:
        """Открывает системный файловый менеджер и выделяет указанный файл.

        Args:
            path: Путь к файлу, который необходимо подсветить.

        Raises:
            FileNotFoundError: Если файл не найден.
            OSError: При ошибке вызова файлового менеджера.
        """
        ...

    def move_to_trash(self, path: str | Path) -> bool:
        """Перемещает файл или директорию в системную корзину.

        Args:
            path: Путь к удаляемому объекту.

        Returns:
            bool: True в случае успешного перемещения в корзину, иначе False.

        Raises:
            FileNotFoundError: Если файл не существует.
            OSError: При ошибке удаления.
        """
        ...


def get_platform_file_manager() -> PlatformFileManager:
    """Возвращает платформозависимую реализацию файлового менеджера.

    Returns:
        PlatformFileManager: Реализация для текущей ОС (Windows или Linux).
    """
    if sys.platform == "win32":
        from certificate_analyzer.infrastructure.platform.windows import (
            WindowsPlatformFileManager,
        )

        return WindowsPlatformFileManager()
    from certificate_analyzer.infrastructure.platform.linux import (
        LinuxPlatformFileManager,
    )

    return LinuxPlatformFileManager()


def open_path(path: str | Path) -> None:
    """Совместимая функция быстрого открытия пути в ОС.

    Args:
        path: Путь к файлу или папке.

    Returns:
        None
    """
    manager = get_platform_file_manager()
    manager.open_file(path)

"""Реализация файлового менеджера платформы для операционных систем Windows."""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess

from certificate_analyzer.infrastructure.platform.safe_open import validate_open_file


class SHFILEOPSTRUCTW(ctypes.Structure):
    """Структура Win32 API для выполнения операций над файлами через оболочку."""

    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


FO_DELETE = 3
FOF_ALLOWUNDO = 0x0040
FOF_NOCONFIRMATION = 0x0010
FOF_SILENT = 0x0004


class WindowsPlatformFileManager:
    """Реализация управления файлами и оболочкой Windows."""

    def open_file(self, path: str | Path) -> None:
        """Открывает файл ассоциированным приложением Windows.

        Args:
            path: Путь к файлу.

        Raises:
            FileNotFoundError: Если файл не найден.
            OSError: При ошибке открытия.
        """
        p = validate_open_file(path)
        os.startfile(str(p))

    def reveal_file(self, path: str | Path) -> None:
        """Открывает проводник Windows и выделяет указанный файл.

        Args:
            path: Путь к целевому файлу.

        Raises:
            FileNotFoundError: Если путь не существует.
            OSError: При ошибке вызова explorer.exe.
        """
        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Файл для показа в проводнике не найден: {p}")
        subprocess.Popen(["explorer.exe", f"/select,{p}"])

    def move_to_trash(self, path: str | Path) -> bool:
        """Перемещает файл или каталог в Корзину Windows.

        Args:
            path: Путь к удаляемому объекту.

        Returns:
            bool: True, если перемещение в корзину успешно выполнено.

        Raises:
            FileNotFoundError: Если объект не существует.
            OSError: При ошибке операции файловой оболочки.
        """
        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Файл для удаления не найден: {p}")

        # Win32 API ожидает путь с двойным завершающим нулем
        path_str = str(p) + "\0\0"
        fileop = SHFILEOPSTRUCTW(
            hwnd=None,
            wFunc=FO_DELETE,
            pFrom=path_str,
            pTo=None,
            fFlags=FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT,
            fAnyOperationsAborted=False,
            hNameMappings=None,
            lpszProgressTitle=None,
        )
        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        if res != 0 or fileop.fAnyOperationsAborted:
            raise OSError(f"Ошибка перемещения файла в корзину (код {res}): {p}")
        return True

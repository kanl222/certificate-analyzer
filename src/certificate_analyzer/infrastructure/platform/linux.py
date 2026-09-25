"""Реализация файлового менеджера платформы для операционных систем Linux."""

from pathlib import Path
import shutil
import subprocess


class LinuxPlatformFileManager:
    """Реализация управления файлами и средой рабочего стола Linux."""

    def open_file(self, path: str | Path) -> None:
        """Открывает файл с помощью xdg-open.

        Args:
            path: Путь к открываемому файлу.

        Raises:
            FileNotFoundError: Если файл не найден.
            OSError: При ошибке выполнения команды.
        """
        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Файл не найден: {p}")
        subprocess.Popen(["xdg-open", str(p)])

    def reveal_file(self, path: str | Path) -> None:
        """Открывает файловый менеджер Linux и подсвечивает файл или открывает родительский каталог.

        Args:
            path: Путь к целевому файлу.

        Raises:
            FileNotFoundError: Если файл не найден.
            OSError: При ошибке открытия проводника.
        """
        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Файл не найден: {p}")

        parent_dir = str(p.parent if p.is_file() else p)
        subprocess.Popen(["xdg-open", parent_dir])

    def move_to_trash(self, path: str | Path) -> bool:
        """Перемещает файл или каталог в корзину с помощью утилиты gio или trash-cli.

        Args:
            path: Путь к удаляемому объекту.

        Returns:
            bool: True в случае успешного перемещения в корзину.

        Raises:
            FileNotFoundError: Если объект не существует.
            OSError: Если системная утилита корзины недоступна или завершилась ошибкой.
        """
        p = Path(path).resolve()
        if not p.exists():
            raise FileNotFoundError(f"Файл не найден: {p}")

        if shutil.which("gio"):
            cmd = ["gio", "trash", str(p)]
        elif shutil.which("trash-put"):
            cmd = ["trash-put", str(p)]
        else:
            raise OSError("Системная утилита для перемещения в корзину (gio или trash-cli) не найдена")

        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            raise OSError(f"Ошибка перемещения в корзину: {res.stderr.strip() or res.stdout.strip()}")
        return True

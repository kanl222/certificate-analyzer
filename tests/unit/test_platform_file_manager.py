"""Модульные тесты для платформозависимого файлового менеджера."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from certificate_analyzer.infrastructure.platform.base import (
    get_platform_file_manager,
    open_path,
)
from certificate_analyzer.infrastructure.platform.linux import (
    LinuxPlatformFileManager,
)
from certificate_analyzer.infrastructure.platform.windows import (
    WindowsPlatformFileManager,
)


def test_windows_open_file_success(tmp_path: Path):
    """Проверяет успешный вызов открытия существующего файла в Windows.

    Args:
        tmp_path: Временная директория теста.

    Returns:
        None
    """
    test_file = tmp_path / "cert.cer"
    test_file.write_text("test")

    manager = WindowsPlatformFileManager()
    with patch("os.startfile", create=True) as mock_startfile:
        manager.open_file(test_file)
        mock_startfile.assert_called_once_with(str(test_file.resolve()))


def test_windows_open_file_not_found(tmp_path: Path):
    """Проверяет выброс FileNotFoundError при попытке открыть несуществующий файл в Windows.

    Args:
        tmp_path: Временная директория теста.

    Returns:
        None
    """
    manager = WindowsPlatformFileManager()
    with pytest.raises(FileNotFoundError):
        manager.open_file(tmp_path / "non_existent.cer")


def test_windows_reveal_file(tmp_path: Path):
    """Проверяет формирование команды проводника explorer.exe в Windows.

    Args:
        tmp_path: Временная директория теста.

    Returns:
        None
    """
    test_file = tmp_path / "cert.cer"
    test_file.write_text("test")

    manager = WindowsPlatformFileManager()
    with patch("subprocess.Popen") as mock_popen:
        manager.reveal_file(test_file)
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "explorer.exe"
        assert f"/select,{test_file.resolve()}" in args[1]


def test_windows_move_to_trash(tmp_path: Path):
    """Проверяет вызов Win32 SHFileOperationW при перемещении файла в корзину.

    Args:
        tmp_path: Временная директория теста.

    Returns:
        None
    """
    test_file = tmp_path / "cert.cer"
    test_file.write_text("test")

    manager = WindowsPlatformFileManager()
    mock_windll = MagicMock()
    mock_windll.shell32.SHFileOperationW.return_value = 0
    with patch("ctypes.windll", mock_windll, create=True):
        result = manager.move_to_trash(test_file)
        assert result is True
        mock_windll.shell32.SHFileOperationW.assert_called_once()


def test_linux_open_file_success(tmp_path: Path):
    """Проверяет вызов xdg-open при открытии файла в Linux.

    Args:
        tmp_path: Временная директория теста.

    Returns:
        None
    """
    test_file = tmp_path / "cert.cer"
    test_file.write_text("test")

    manager = LinuxPlatformFileManager()
    with patch("subprocess.Popen") as mock_popen:
        manager.open_file(test_file)
        mock_popen.assert_called_once_with(["xdg-open", str(test_file.resolve())])


def test_linux_reveal_file(tmp_path: Path):
    """Проверяет открытие родительского каталога через xdg-open в Linux.

    Args:
        tmp_path: Временная директория теста.

    Returns:
        None
    """
    test_file = tmp_path / "cert.cer"
    test_file.write_text("test")

    manager = LinuxPlatformFileManager()
    with patch("subprocess.Popen") as mock_popen:
        manager.reveal_file(test_file)
        mock_popen.assert_called_once_with(["xdg-open", str(test_file.parent.resolve())])


def test_linux_move_to_trash_gio(tmp_path: Path):
    """Проверяет перемещение в корзину через утилиту gio в Linux.

    Args:
        tmp_path: Временная директория теста.

    Returns:
        None
    """
    test_file = tmp_path / "cert.cer"
    test_file.write_text("test")

    manager = LinuxPlatformFileManager()
    with patch("shutil.which", side_effect=lambda cmd: "/usr/bin/gio" if cmd == "gio" else None):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            result = manager.move_to_trash(test_file)
            assert result is True
            mock_run.assert_called_once_with(["gio", "trash", str(test_file.resolve())], capture_output=True, text=True, check=False)


def test_linux_move_to_trash_no_tool(tmp_path: Path):
    """Проверяет возникновение ошибки, если утилиты корзины отсутствуют в Linux.

    Args:
        tmp_path: Временная директория теста.

    Returns:
        None
    """
    test_file = tmp_path / "cert.cer"
    test_file.write_text("test")

    manager = LinuxPlatformFileManager()
    with patch("shutil.which", return_value=None):
        with pytest.raises(OSError, match="Системная утилита"):
            manager.move_to_trash(test_file)


def test_get_platform_file_manager():
    """Проверяет выбор реализации файлового менеджера в зависимости от ОС.

    Returns:
        None
    """
    with patch("sys.platform", "win32"):
        mgr = get_platform_file_manager()
        assert isinstance(mgr, WindowsPlatformFileManager)

    with patch("sys.platform", "linux"):
        mgr = get_platform_file_manager()
        assert isinstance(mgr, LinuxPlatformFileManager)


def test_open_path_helper(tmp_path: Path):
    """Проверяет работу функции обратной совместимости open_path.

    Args:
        tmp_path: Временная директория теста.

    Returns:
        None
    """
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello")

    with patch("certificate_analyzer.infrastructure.platform.base.get_platform_file_manager") as mock_get:
        mock_mgr = MagicMock()
        mock_get.return_value = mock_mgr
        open_path(test_file)
        mock_mgr.open_file.assert_called_once_with(test_file)

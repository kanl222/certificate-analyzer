import ctypes
from types import SimpleNamespace
from unittest.mock import Mock

from certificate_analyzer.presentation.gui import app


def test_windows_app_id_is_set(monkeypatch):
    setter = Mock(return_value=0)
    monkeypatch.setattr(app.sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(shell32=SimpleNamespace(SetCurrentProcessExplicitAppUserModelID=setter)), raising=False)
    app._enable_windows_identity()
    setter.assert_called_once_with(app.WINDOWS_APP_ID)
    assert setter.argtypes == [ctypes.c_wchar_p]


def test_non_windows_does_not_call_windows_shell(monkeypatch):
    setter = Mock()
    monkeypatch.setattr(app.sys, "platform", "linux")
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(shell32=SimpleNamespace(SetCurrentProcessExplicitAppUserModelID=setter)), raising=False)
    app._enable_windows_identity()
    setter.assert_not_called()

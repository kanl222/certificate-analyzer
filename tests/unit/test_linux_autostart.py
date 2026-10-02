from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from certificate_analyzer.runtime import user_daemon


@pytest.fixture
def linux_systemd(tmp_path, monkeypatch):
    monkeypatch.setattr(user_daemon.sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(user_daemon.shutil, "which", lambda _: "/usr/bin/systemctl")
    monkeypatch.setattr(user_daemon, "executable_command", lambda: ["/opt/My App/analyzer"])
    run = Mock(return_value=SimpleNamespace(returncode=0, stderr="", stdout=""))
    monkeypatch.setattr(user_daemon.subprocess, "run", run)
    return tmp_path / "systemd/user", run


def test_enable_creates_unit_with_config_and_enables(linux_systemd, tmp_path):
    folder, run = linux_systemd
    config = tmp_path / "settings % test.json"
    user_daemon.set_autostart(True, config)
    text = (folder / "certificate-analyzer.service").read_text(encoding="utf-8")
    assert 'ExecStart="/opt/My App/analyzer" "--config"' in text
    assert "settings %% test.json" in text
    assert '"worker"' in text
    assert [call.args[0][2:] for call in run.call_args_list] == [
        ["unmask", "certificate-analyzer.service"], ["daemon-reload"],
        ["enable", "certificate-analyzer.service"],
    ]


def test_disable_preserves_override_before_masking(linux_systemd):
    folder, run = linux_systemd
    folder.mkdir(parents=True)
    target = folder / "certificate-analyzer.service"
    target.write_text("custom unit", encoding="utf-8")
    user_daemon.set_autostart(False)
    assert not target.exists()
    backups = list(folder.glob("certificate-analyzer.service.disabled.*"))
    assert len(backups) == 1 and backups[0].read_text() == "custom unit"
    assert [call.args[0][2:] for call in run.call_args_list] == [
        ["disable", "certificate-analyzer.service"],
        ["mask", "--force", "certificate-analyzer.service"],
    ]


def test_legacy_autostart_is_disabled(linux_systemd):
    folder, run = linux_systemd
    folder.mkdir(parents=True)
    (folder / "cert-analyzer.service").write_text("legacy")
    user_daemon.set_autostart(True)
    assert run.call_args_list[0].args[0] == ["systemctl", "--user", "disable", "cert-analyzer.service"]


def test_missing_systemd_reports_error(linux_systemd, monkeypatch):
    monkeypatch.setattr(user_daemon.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="systemctl не найден"):
        user_daemon.set_autostart(True)


def test_systemd_error_is_visible(linux_systemd):
    _, run = linux_systemd
    run.return_value = SimpleNamespace(returncode=1, stderr="Failed to connect to bus", stdout="")
    with pytest.raises(RuntimeError, match="Failed to connect to bus"):
        user_daemon.set_autostart(True)

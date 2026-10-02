from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from certificate_analyzer.infrastructure.platform.windows import WindowsPlatformFileManager
from certificate_analyzer.infrastructure.platform.linux import LinuxPlatformFileManager
from certificate_analyzer.infrastructure.notifications.api_notifier import ApiNotificationBackend
from certificate_analyzer.domain.services.mchd_status import mchd_status
from certificate_analyzer.domain.enums.mchd_status import MchdStatus


@pytest.mark.parametrize("manager", [WindowsPlatformFileManager, LinuxPlatformFileManager])
@pytest.mark.parametrize("name", ["evil.exe", "evil.cmd", "evil.lnk", "evil.desktop", "report.pdf.exe"])
def test_dangerous_files_never_reach_shell(tmp_path, manager, name):
    p = tmp_path / name
    p.write_bytes(b"test")
    with patch("os.startfile", create=True) as start, patch("subprocess.Popen") as popen:
        with pytest.raises(ValueError):
            manager().open_file(p)
        start.assert_not_called()
        popen.assert_not_called()


@pytest.mark.parametrize("manager", [WindowsPlatformFileManager, LinuxPlatformFileManager])
def test_directory_not_opened_as_file(tmp_path, manager):
    with pytest.raises(ValueError):
        manager().open_file(tmp_path)


@pytest.mark.parametrize("size, expected", [(8, "success"), (9, "error")])
def test_http_response_limit(size, expected):
    response = MagicMock()
    response.__enter__.return_value = response
    response.status = 200
    stream = BytesIO(b"a" * size)
    response.read.side_effect = stream.read
    backend = ApiNotificationBackend(stub_mode=False, max_response_bytes=8)
    with patch("urllib.request.urlopen", return_value=response):
        result = backend.send("test", "test")
    assert result["status"] == expected
    response.read.assert_called_once_with(9)
    response.__exit__.assert_called_once()


def test_history_bounded():
    backend = ApiNotificationBackend(history_limit=2)
    for i in range(4):
        backend.send(str(i), "test")
    assert [r["payload"]["title"] for r in backend.history] == ["2", "3"]
    backend.clear_history()
    assert backend.history == []


def test_mchd_future_start_not_active():
    assert mchd_status(datetime(2028, 1, 1), now=datetime(2026, 1, 1), valid_from=datetime(2027, 1, 1)) == MchdStatus.INVALID


def test_windows_service_installation_is_disabled():
    from certificate_analyzer.cli import main
    with pytest.raises(SystemExit) as error:
        main(["service", "--startup", "auto", "install"])
    assert error.value.code == 2


def test_linux_reveal_directory_preserved(tmp_path):
    with patch("subprocess.Popen") as popen:
        LinuxPlatformFileManager().reveal_file(tmp_path)
    popen.assert_called_once_with(["xdg-open", str(tmp_path.resolve())])


def test_linux_trash_arbitrary_file_preserved(tmp_path):
    p = tmp_path / "blocked.exe"
    p.write_bytes(b"test")
    with patch("shutil.which", return_value="/usr/bin/gio"), patch("subprocess.run", return_value=MagicMock(returncode=0)) as run:
        assert LinuxPlatformFileManager().move_to_trash(p)
    assert run.call_args.args[0] == ["gio", "trash", str(p.resolve())]

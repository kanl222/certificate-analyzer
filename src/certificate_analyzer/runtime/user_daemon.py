"""User-session daemon and login startup, without SCM/admin privileges."""

from dataclasses import asdict
import json
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
import shutil
import threading
import time

from certificate_analyzer.infrastructure.database.session import get_database_path
from certificate_analyzer.runtime.ipc import WriteClient, WriterServer, WriterUnavailable, token_path

logger = logging.getLogger(__name__)


def executable_command():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    executable = Path(sys.executable)
    if sys.platform == "win32" and executable.with_name("pythonw.exe").exists():
        executable = executable.with_name("pythonw.exe")
    return [str(executable), "-m", "certificate_analyzer"]


def ensure_writer(settings, timeout=15):
    client = WriteClient(get_database_path(settings), timeout=2)
    try:
        client.call()
        return
    except WriterUnavailable:
        pass
    environment = os.environ.copy()
    logger.info("Запрошен запуск фонового процесса")
    environment["CERTIFICATE_ANALYZER_DAEMON_SETTINGS"] = json.dumps(asdict(settings))
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {"start_new_session": True}
    process = subprocess.Popen(executable_command() + ["worker"], env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, **options)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            client.call()
            logger.info("Фоновый процесс готов к работе")
            return
        except WriterUnavailable:
            if process.poll() is not None:
                # Another GUI may have won the race and still be initializing.
                time.sleep(0.1)
            else:
                time.sleep(0.1)
    raise WriterUnavailable("Не удалось запустить фоновый процесс. Проверьте журнал приложения и настройки БД.")


def run_writer(settings):
    from certificate_analyzer.bootstrap import create_application
    from certificate_analyzer.runtime.worker import MonitoringWorker
    logger.info("Запуск демона; интервал мониторинга: %s секунд", settings.check_interval)
    with WriterServer(get_database_path(settings)) as server:
        stop = server.stop_requested
        with create_application(settings=settings) as app:
            server.attach(app)
            logger.info("Демон запущен; локальный API готов; БД: %s", app.database.path)
            worker = MonitoringWorker(application=app)

            def monitor():
                while not stop.is_set():
                    try:
                        with server.command_lock:
                            worker.run_once()
                    except Exception:
                        logger.exception("Ошибка фоновой проверки")
                    stop.wait(settings.check_interval)

            previous = {}
            def on_signal(signum, _):
                logger.info("Получен сигнал остановки: %s", signum)
                stop.set()
            for sig in (signal.SIGINT, signal.SIGTERM):
                previous[sig] = signal.signal(sig, on_signal)
            thread = threading.Thread(target=monitor, name="monitoring", daemon=True)
            thread.start()
            server.timeout = 0.5
            try:
                while not stop.is_set():
                    server.handle_request()
            finally:
                stop.set()
                thread.join()
                worker.close()
                for sig, handler in previous.items():
                    signal.signal(sig, handler)
    logger.info("Демон остановлен; ресурсы освобождены")


def stop_writer(settings, timeout=15):
    path = get_database_path(settings)
    client = WriteClient(path, timeout=timeout)
    if not token_path(path).exists():
        logger.info("Остановка не требуется: фоновый процесс не запущен")
        return
    logger.info("Запрошена остановка фонового процесса")
    client.call(method="stop")
    deadline = time.monotonic() + timeout
    while token_path(path).exists():
        if time.monotonic() >= deadline:
            raise WriterUnavailable("Фоновый процесс не завершился вовремя. Проверьте журнал приложения.")
        time.sleep(0.1)
    logger.info("Остановка фонового процесса подтверждена")


def restart_writer(settings):
    logger.info("Запрошен перезапуск фонового процесса")
    stop_writer(settings)
    ensure_writer(settings)


def set_autostart(enabled, config_path=None):
    if sys.platform.startswith("linux"):
        _set_linux_autostart(enabled, config_path)
        logger.info("Автозапуск Linux: %s", "включён" if enabled else "отключён")
        return
    if sys.platform != "win32":
        raise RuntimeError("Автозапуск поддерживается в Windows и Linux с systemd")
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            command = executable_command()
            if config_path:
                command += ["--config", str(Path(config_path).resolve())]
            command += ["worker"]
            winreg.SetValueEx(key, "CertificateAnalyzer", 0, winreg.REG_SZ, subprocess.list2cmdline(command))
        else:
            try:
                winreg.DeleteValue(key, "CertificateAnalyzer")
            except FileNotFoundError:
                pass
    logger.info("Автозапуск Windows: %s", "включён" if enabled else "отключён")


def _systemctl(*arguments):
    try:
        result = subprocess.run(["systemctl", "--user", *arguments],
            capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Не удалось обратиться к пользовательскому systemd.") from exc
    if result.returncode:
        raise RuntimeError("Ошибка пользовательского systemd: " + (result.stderr.strip() or result.stdout.strip()))


def _systemd_quote(value):
    # systemd uses its own quoting and expands percent specifiers, not shell syntax.
    value = str(value)
    if "\n" in value or "\r" in value:
        raise ValueError("Путь не должен содержать перевод строки")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def _set_linux_autostart(enabled, config_path=None):
    if not shutil.which("systemctl"):
        raise RuntimeError("Для автозапуска в Linux требуется systemd (systemctl не найден).")
    unit = "certificate-analyzer.service"
    folder = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "systemd/user"
    legacy = folder / "cert-analyzer.service"
    if legacy.exists():
        _systemctl("disable", legacy.name)
    if not enabled:
        _systemctl("disable", unit)
        target = folder / unit
        if target.is_file() and not target.is_symlink():
            # systemctl cannot mask a unit over a regular user override.
            # Preserve it before creating the /dev/null mask.
            target.replace(folder / (unit + ".disabled." + str(time.time_ns())))
        # Mask also overrides DEB's global enablement for this user.
        _systemctl("mask", "--force", unit)
        return
    _systemctl("unmask", unit)
    command = executable_command()
    if config_path:
        command += ["--config", str(Path(config_path).resolve())]
    command += ["worker"]
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / unit
    text = "[Unit]\nDescription=Certificate Analyzer monitoring\nAfter=graphical-session.target\n\n[Service]\nType=simple\n"
    if os.environ.get("CERTIFICATE_ANALYZER_HOME"):
        text += "Environment=" + _systemd_quote("CERTIFICATE_ANALYZER_HOME=" + str(Path(os.environ["CERTIFICATE_ANALYZER_HOME"]).resolve())) + "\n"
    text += "ExecStart=" + " ".join(_systemd_quote(arg).replace("$", "$$") for arg in command) + "\nRestart=on-failure\nRestartSec=30\n\n[Install]\nWantedBy=default.target\n"
    target.write_text(text, encoding="utf-8")
    _systemctl("daemon-reload")
    _systemctl("enable", unit)

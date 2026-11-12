"""Пользовательский демон сессии и управление автозапуском без прав администратора."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import TYPE_CHECKING, Any

from certificate_analyzer.infrastructure.config.paths import config_dir
from certificate_analyzer.infrastructure.database.session import get_database_path
from certificate_analyzer.runtime.ipc import WriteClient, WriterServer, WriterUnavailable, token_path

if TYPE_CHECKING:
    from certificate_analyzer.infrastructure.config.settings import Settings
    from certificate_analyzer.runtime.worker import MonitoringWorker

logger: logging.Logger = logging.getLogger(__name__)


def executable_command() -> list[str]:
    """Возвращает список аргументов для вызова исполняемого файла приложения."""
    if getattr(sys, "frozen", False):
        return [sys.executable]
    executable: Path = Path(sys.executable)
    if sys.platform == "win32" and executable.with_name("pythonw.exe").exists():
        executable = executable.with_name("pythonw.exe")
    return [str(executable), "-m", "certificate_analyzer"]


def ensure_writer(settings: Settings, timeout: float = 15.0) -> None:
    """Гарантирует, что пишущий фоновый процесс запущен и готов принимать команды."""
    client: WriteClient = WriteClient(get_database_path(settings), timeout=2.0)
    try:
        client.call()
        return
    except WriterUnavailable:
        pass
    environment: dict[str, str] = os.environ.copy()
    logger.info("Запрошен запуск фонового процесса")
    environment["CERTIFICATE_ANALYZER_DAEMON_SETTINGS"] = settings.model_dump_json()
    options: dict[str, Any] = (
        {"creationflags": subprocess.CREATE_NO_WINDOW}
        if sys.platform == "win32"
        else {"start_new_session": True}
    )
    err_path: Path = config_dir() / "daemon_startup.err"
    err_path.parent.mkdir(parents=True, exist_ok=True)
    with err_path.open("w", encoding="utf-8", errors="replace") as err_file:
        process: subprocess.Popen[Any] = subprocess.Popen(
            executable_command() + ["worker"],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=err_file,
            **options,
        )

    def _cleanup_err() -> None:
        try:
            err_path.unlink(missing_ok=True)
        except OSError:
            pass

    deadline: float = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            client.call()
            logger.info("Фоновый процесс готов к работе")
            _cleanup_err()
            return
        except WriterUnavailable:
            if process.poll() is not None:
                time.sleep(0.1)
                try:
                    client.call()
                    _cleanup_err()
                    return
                except WriterUnavailable:
                    detail: str = ""
                    try:
                        detail = err_path.read_text(encoding="utf-8", errors="replace").strip()
                    except OSError:
                        pass
                    _cleanup_err()
                    msg: str = f"Фоновый процесс завершился с кодом {process.returncode}."
                    if detail:
                        msg += f"\nПодробности:\n{detail}"
                    else:
                        msg += " Проверьте журнал приложения и настройки БД."
                    raise WriterUnavailable(msg)
            time.sleep(0.1)
    _cleanup_err()
    raise WriterUnavailable("Не удалось запустить фоновый процесс. Проверьте журнал приложения и настройки БД.")


def run_writer(settings: Settings) -> None:
    """Запускает цикл единого пишущего сервера и периодического мониторинга."""
    from certificate_analyzer.bootstrap import create_application
    from certificate_analyzer.runtime.worker import MonitoringWorker

    logger.info("Запуск демона; интервал мониторинга: %s секунд", settings.check_interval)
    with WriterServer(get_database_path(settings)) as server:
        stop: threading.Event = server.stop_requested
        with create_application(settings=settings) as app:
            server.attach(app)
            logger.info("Демон запущен; локальный API готов; БД: %s", app.database.path)
            worker: MonitoringWorker = MonitoringWorker(application=app)

            def monitor() -> None:
                while not stop.is_set():
                    try:
                        worker.run_once(db_lock=server.command_lock)
                    except Exception:
                        logger.exception("Ошибка фоновой проверки")
                    stop.wait(settings.check_interval)

            previous: dict[signal.Signals, Any] = {}

            def on_signal(signum: int, _: Any) -> None:
                logger.info("Получен сигнал остановки: %s", signum)
                stop.set()

            for sig in (signal.SIGINT, signal.SIGTERM):
                previous[sig] = signal.signal(sig, on_signal)
            thread: threading.Thread = threading.Thread(target=monitor, name="monitoring", daemon=True)
            thread.start()
            server.timeout = 0.5
            try:
                while not stop.is_set():
                    server.handle_request()
            finally:
                stop.set()
                thread.join()
                # Ожидание завершения активных IPC-команд перед удалением контекста БД.
                server.server_close()
                worker.close()
                for sig, handler in previous.items():
                    signal.signal(sig, handler)
    logger.info("Демон остановлен; ресурсы освобождены")


def stop_writer(settings: Settings, timeout: float = 15.0) -> None:
    """Останавливает запущенный фоновый процесс демона."""
    path: Path = get_database_path(settings)
    client: WriteClient = WriteClient(path, timeout=timeout)
    if not token_path(path).exists():
        logger.info("Остановка не требуется: фоновый процесс не запущен")
        return
    logger.info("Запрошена остановка фонового процесса")
    client.call(method="stop")
    deadline: float = time.monotonic() + timeout
    while token_path(path).exists():
        if time.monotonic() >= deadline:
            raise WriterUnavailable("Фоновый процесс не завершился вовремя. Проверьте журнал приложения.")
        time.sleep(0.1)
    logger.info("Остановка фонового процесса подтверждена")


def restart_writer(settings: Settings) -> None:
    """Выполняет последовательную остановку и повторный запуск фонового процесса."""
    logger.info("Запрошен перезапуск фонового процесса")
    stop_writer(settings)
    ensure_writer(settings)


def set_autostart(enabled: bool, config_path: str | Path | None = None) -> None:
    """Включает или выключает автозапуск приложения при входе пользователя."""
    if sys.platform.startswith("linux"):
        _set_linux_autostart(enabled, config_path)
        logger.info("Автозапуск Linux: %s", "включён" if enabled else "отключён")
        return
    if sys.platform != "win32":
        raise RuntimeError("Автозапуск поддерживается в Windows и Linux с systemd")
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
        if enabled:
            command: list[str] = executable_command()
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


def _systemctl(*arguments: str) -> None:
    """Выполняет команду systemctl для пользовательской службы systemd."""
    try:
        result: subprocess.CompletedProcess[str] = subprocess.run(
            ["systemctl", "--user", *arguments],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Не удалось обратиться к пользовательскому systemd.") from exc
    if result.returncode:
        raise RuntimeError("Ошибка пользовательского systemd: " + (result.stderr.strip() or result.stdout.strip()))


def _systemd_quote(value: Any) -> str:
    """Экранирует значение в формате директив systemd."""
    val: str = str(value)
    if "\n" in val or "\r" in val:
        raise ValueError("Путь не должен содержать перевод строки")
    return '"' + val.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def _set_linux_autostart(enabled: bool, config_path: str | Path | None = None) -> None:
    """Настраивает пользовательскую службу systemd в Linux."""
    if not shutil.which("systemctl"):
        raise RuntimeError("Для автозапуска в Linux требуется systemd (systemctl не найден).")
    unit: str = "certificate-analyzer.service"
    folder: Path = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "systemd/user"
    legacy: Path = folder / "cert-analyzer.service"
    if legacy.exists():
        _systemctl("disable", legacy.name)
    if not enabled:
        _systemctl("disable", unit)
        target: Path = folder / unit
        if target.is_file() and not target.is_symlink():
            # systemctl не может замаскировать юнит поверх пользовательского переопределения.
            target.replace(folder / (unit + ".disabled." + str(time.time_ns())))
        # Маскировка также переопределяет глобальное включение из DEB-пакета для текущего пользователя.
        _systemctl("mask", "--force", unit)
        return
    _systemctl("unmask", unit)
    command: list[str] = executable_command()
    if config_path:
        command += ["--config", str(Path(config_path).resolve())]
    command += ["worker"]
    folder.mkdir(parents=True, exist_ok=True)
    target_unit: Path = folder / unit
    text: str = (
        "[Unit]\nDescription=Certificate Analyzer monitoring\nAfter=graphical-session.target\n\n"
        "[Service]\nType=simple\n"
    )
    if os.environ.get("CERTIFICATE_ANALYZER_HOME"):
        text += (
            "Environment="
            + _systemd_quote(
                "CERTIFICATE_ANALYZER_HOME="
                + str(Path(os.environ["CERTIFICATE_ANALYZER_HOME"]).resolve())
            )
            + "\n"
        )
    text += (
        "ExecStart="
        + " ".join(_systemd_quote(arg).replace("$", "$$") for arg in command)
        + "\nRestart=on-failure\nRestartSec=30\n\n[Install]\nWantedBy=default.target\n"
    )
    target_unit.write_text(text, encoding="utf-8")
    _systemctl("daemon-reload")
    _systemctl("enable", unit)

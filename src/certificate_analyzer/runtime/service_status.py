"""Определение состояния системного процесса фонового мониторинга."""

import subprocess
import sys

from certificate_analyzer.constants import SERVICE_NAME


def monitoring_process_status() -> str:
    """Возвращает краткий статус службы мониторинга для строки состояния GUI."""
    try:
        if sys.platform == "win32":
            return _windows_service_status()
        if sys.platform.startswith("linux"):
            return _systemd_service_status()
    except (OSError, subprocess.SubprocessError):
        return "Мониторинг: статус недоступен"
    return "Мониторинг: не поддерживается"


def _windows_service_status() -> str:
    result = subprocess.run(
        ["sc.exe", "query", SERVICE_NAME],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=2,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0:
        return "Мониторинг: служба не установлена"
    if "RUNNING" in output or "РАБОТАЕТ" in output or ": 4 " in output:
        return "Мониторинг: активен"
    return "Мониторинг: остановлен"


def _systemd_service_status() -> str:
    result = subprocess.run(
        [
            "systemctl",
            "--user",
            "is-active",
            "certificate-analyzer.service",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=2,
        check=False,
    )
    state = result.stdout.strip()
    if result.returncode == 0 and state == "active":
        return "Мониторинг: активен"
    labels = {
        "inactive": "остановлен",
        "failed": "ошибка",
        "activating": "запускается",
        "deactivating": "останавливается",
    }
    if state in labels:
        return f"Мониторинг: {labels[state]}"
    return "Мониторинг: служба не установлена"

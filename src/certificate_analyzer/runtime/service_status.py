"""State of the user-session daemon, queried through its API."""

from certificate_analyzer.infrastructure.config.config_loader import load_settings
from certificate_analyzer.infrastructure.database.session import get_database_path
from certificate_analyzer.runtime.ipc import WriteClient, WriterUnavailable, WriteCommandError


def monitoring_process_status(settings=None) -> str:
    try:
        WriteClient(get_database_path(settings or load_settings()), timeout=2).call()
        return "Мониторинг: активен"
    except (WriterUnavailable, WriteCommandError):
        return "Мониторинг: фоновый процесс недоступен"

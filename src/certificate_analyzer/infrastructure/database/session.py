"""Движок SQLAlchemy и фабрика сессий в контексте экземпляра приложения."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from sqlalchemy import URL, Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from certificate_analyzer.infrastructure.config.paths import config_dir
from certificate_analyzer.infrastructure.database.models import Base
from certificate_analyzer.infrastructure.database.migrations import migrate

if TYPE_CHECKING:
    from certificate_analyzer.infrastructure.config.settings import Settings


BUSY_TIMEOUT_MS: int = 30000


def get_database_path(settings: Settings | None = None) -> Path:
    """Определяет актуальный путь к файлу базы данных SQLite.

    Args:
        settings: Объект конфигурации приложения.

    Returns:
        Path: Абсолютный путь к файлу БД.
    """
    if settings and settings.database_path:
        return Path(settings.database_path).expanduser().resolve()
    if not os.environ.get("CERTIFICATE_ANALYZER_HOME"):
        previous = Path.home() / ".local/share/certificate-analyzer/certificates.db"
        if previous.is_file():
            return previous
    return config_dir() / "certificates.db"


class Database:
    """Управление подключением к SQLite и жизненным циклом сессий SQLAlchemy."""

    def __init__(self, path: str | Path, *, read_only: bool = False) -> None:
        """Инициализирует подключение к базе данных.

        Args:
            path: Путь к файлу базы данных.
            read_only: Режим «только для чтения» (query_only).
        """
        self.path: Path = Path(path).expanduser().resolve()
        self.read_only: bool = read_only
        if not read_only:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(
            ("sqlite:///file:" + quote(self.path.as_posix(), safe="/:") + "?mode=ro&uri=true")
            if read_only else URL.create("sqlite", database=self.path.as_posix()),
            connect_args={"timeout": BUSY_TIMEOUT_MS / 1000},
        )

        @event.listens_for(self.engine, "connect")
        def configure(connection: Any, _: Any) -> None:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
            # Для учётных данных сохраняем синхронизацию WAL при каждом коммите.
            connection.execute("PRAGMA synchronous=FULL")
            if read_only:
                connection.execute("PRAGMA query_only=ON")

        try:
            if not read_only:
                migrate(self.engine, self.path)
                Base.metadata.create_all(self.engine)
                with self.engine.connect() as connection:
                    mode = connection.exec_driver_sql("PRAGMA journal_mode=WAL").scalar()
                    if mode != "wal":
                        raise RuntimeError("Не удалось включить WAL для базы данных")
            self.sessions: sessionmaker[Session] = sessionmaker(self.engine, expire_on_commit=False)
        except Exception:
            self.engine.dispose()
            raise

    def close(self) -> None:
        """Закрывает пул соединений базы данных."""
        self.engine.dispose()

    def __enter__(self) -> Database:
        """Вход в контекстный менеджер."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Выход из контекстного менеджера с освобождением соединений."""
        self.close()

"""Upgrade an offline SQLite COPY to the application's current data schema."""

from contextlib import closing
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import tempfile

from sqlalchemy import create_engine

from certificate_analyzer.infrastructure.database.migrations import SCHEMA_VERSION, migrate
from certificate_analyzer.infrastructure.database.models import Base


@dataclass(frozen=True)
class UpgradeResult:
    database_path: Path
    source_version: int
    target_version: int


def upgrade_database_copy(source: Path, destination: Path) -> UpgradeResult:
    """Preserve original, including WAL. Publish only a verified upgraded copy.

    Caller must stop the daemon and close database users before switching profiles.
    This is not an API for GUI to modify the active database.
    """
    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError("Целевая база уже существует")
    if Path(str(source) + ".ipc-token").exists():
        raise ValueError("Перед преобразованием остановите фоновый процесс")
    with tempfile.TemporaryDirectory(prefix="ca-upgrade-", dir=destination.parent) as temp:
        snapshot = Path(temp) / "upgraded.db"
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            # sqlite3 backup includes committed pages from WAL.
            with closing(sqlite3.connect(snapshot)) as backup:
                original.backup(backup)
                backup.execute("PRAGMA journal_mode=DELETE")
                version = backup.execute("PRAGMA user_version").fetchone()[0]
                if not 0 <= version <= SCHEMA_VERSION:
                    raise ValueError("Версия базы новее приложения; обратное преобразование запрещено")
                if backup.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ValueError("Исходная база повреждена")
                tables = {row[0] for row in backup.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not tables & {"certificates", "employees", "mchds", "certificate_requests"}:
                    raise ValueError("Это не база Certificate Analyzer")
                if backup.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' LIMIT 1").fetchone():
                    raise ValueError("База с триггерами не поддерживается")
                counts = {table: backup.execute('SELECT count(*) FROM "' + table.replace('"', '""') + '"').fetchone()[0] for table in tables}
        engine = create_engine("sqlite:///" + snapshot.as_posix())
        try:
            migrate(engine, snapshot)
            Base.metadata.create_all(engine)
            with engine.connect() as connection:
                if connection.exec_driver_sql("PRAGMA integrity_check").all() != [("ok",)]:
                    raise ValueError("Проверка преобразованной базы не пройдена")
                for table, count in counts.items():
                    if table == "sqlite_sequence":
                        continue
                    actual = connection.exec_driver_sql('SELECT count(*) FROM "' + table.replace('"', '""') + '"').scalar()
                    if actual < count:
                        raise ValueError(f"Миграция потеряла записи таблицы {table}")
        finally:
            engine.dispose()
        snapshot.chmod(0o600)
        # Hard link publishes a complete file exclusively, with no overwrite window.
        os.link(snapshot, destination)
    return UpgradeResult(destination, version, SCHEMA_VERSION)

"""Обновление офлайн-копии SQLite до текущей схемы данных приложения."""

from contextlib import closing
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from certificate_analyzer.infrastructure.database.migrations import SCHEMA_VERSION, migrate
from certificate_analyzer.infrastructure.database.models import Base


@dataclass(frozen=True)
class UpgradeResult:
    database_path: Path
    source_version: int
    target_version: int


def upgrade_database_copy(source: Path, destination: Path) -> UpgradeResult:
    """Сохраняет оригинал, включая WAL. Публикует только проверенную обновленную копию.

    Вызывающая сторона должна остановить фоновый процесс и закрыть соединения перед сменой профиля.
    Это не API для изменения активной БД из графического интерфейса.
    """
    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError("Целевая база уже существует")
    if Path(str(source) + ".ipc-token").exists():
        raise ValueError("Перед преобразованием остановите фоновый процесс")
    with tempfile.TemporaryDirectory(prefix="ca-upgrade-", dir=destination.parent, ignore_cleanup_errors=True) as temp:
        snapshot = Path(temp) / "upgraded.db"
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            # Резервное копирование sqlite3 включает зафиксированные страницы из WAL.
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
        engine = create_engine("sqlite:///" + snapshot.as_posix(), poolclass=NullPool)
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
        # Эксклюзивное резервирование, чтобы случайно созданный параллельно файл назначения не был перезаписан.
        descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        try:
            os.replace(snapshot, destination)
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
    return UpgradeResult(destination, version, SCHEMA_VERSION)

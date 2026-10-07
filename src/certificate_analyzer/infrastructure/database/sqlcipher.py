"""Optional SQLCipher 4 adapter, deliberately not used by application bootstrap."""

from contextlib import closing
import importlib
from pathlib import Path
import sqlite3
import tempfile


class SQLCipherUnavailable(RuntimeError):
    """A genuine supported SQLCipher driver is required; no SQLite fallback."""


class SQLCipherError(ValueError):
    """Wrong key, corrupt database or unsupported operation."""


def _driver():
    try:
        return importlib.import_module("sqlcipher3.dbapi2")
    except (ImportError, OSError):
        raise SQLCipherUnavailable("Установите драйвер sqlcipher3 с SQLCipher 4") from None


def _key_literal(key: bytes) -> str:
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("Ключ SQLCipher должен содержать ровно 32 байта")
    # Only fixed-length hex is interpolated. Arbitrary strings/passwords are forbidden.
    return '\"x\'' + key.hex() + '\'\"'


def _check_driver(connection):
    version = connection.execute("PRAGMA cipher_version").fetchone()
    if not version:
        raise SQLCipherUnavailable("Драйвер не поддерживает SQLCipher; обычный SQLite запрещён")
    try:
        major, minor = (int(part) for part in version[0].split(".")[:2])
    except (ValueError, TypeError):
        raise SQLCipherUnavailable("Не удалось определить версию SQLCipher") from None
    if major != 4 or minor < 2:
        raise SQLCipherUnavailable("Требуется SQLCipher версии 4.2 или новее в ветке 4")


def _verify(connection):
    connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
    if connection.execute("PRAGMA cipher_integrity_check").fetchall():
        raise SQLCipherError("Нарушена целостность зашифрованной базы")
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise SQLCipherError("База данных повреждена")


def connect(path: Path, key: bytes, *, read_only: bool = True):
    """Open an existing encrypted DB. Caller must close the returned connection."""
    literal = _key_literal(key)
    path = Path(path).expanduser().resolve()
    driver = _driver()
    connection = driver.connect(path.as_uri() + ("?mode=ro" if read_only else "?mode=rw"), uri=True, timeout=30)
    try:
        _check_driver(connection)
        connection.execute(f"PRAGMA key={literal}")
        connection.execute("PRAGMA cipher_compatibility=4")
        connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA temp_store=MEMORY")
        if read_only:
            connection.execute("PRAGMA query_only=ON")
        else:
            if connection.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() != "wal":
                raise SQLCipherError("Не удалось включить WAL")
        return connection
    except (driver.DatabaseError, SQLCipherError):
        connection.close()
        raise SQLCipherError("Не удалось открыть базу: неверный ключ или данные повреждены") from None
    except BaseException:
        connection.close()
        raise


def _reserve(path):
    path = Path(path).expanduser().absolute()
    for candidate in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm"), Path(str(path) + "-journal")):
        if candidate.exists() or candidate.is_symlink():
            raise SQLCipherError("База или её журнал уже существуют; перезапись запрещена")
    with path.open("xb"):
        pass
    path.chmod(0o600)
    return path


def _remove_owned(path):
    for suffix in ("", "-wal", "-shm", "-journal"):
        Path(str(path) + suffix).unlink(missing_ok=True)


def create_database(destination: Path, key: bytes) -> Path:
    """Create an empty encrypted database without touching any existing profile."""
    _key_literal(key)
    _driver()
    destination = _reserve(destination)
    try:
        with closing(connect(destination, key, read_only=False)) as connection:
            # Persist an actual schema page so the empty DB has an encrypted header.
            connection.execute("PRAGMA user_version=0")
            connection.commit()
            _verify(connection)
    except BaseException:
        _remove_owned(destination)
        raise
    return destination


def _export(source: Path, destination: Path, new_key: bytes, source_key: bytes | None):
    literal = _key_literal(new_key)
    driver = _driver()
    if source_key is not None:
        _key_literal(source_key)
    destination = _reserve(destination)
    try:
        with closing(driver.connect(Path(source).resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            _check_driver(connection)
            if source_key is not None:
                connection.execute(f"PRAGMA key={_key_literal(source_key)}")
                connection.execute("PRAGMA cipher_compatibility=4")
            connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
            if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise SQLCipherError("Исходная база повреждена")
            user_version = connection.execute("PRAGMA user_version").fetchone()[0]
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            connection.execute("PRAGMA temp_store=MEMORY")
            connection.execute(f"ATTACH DATABASE ? AS encrypted KEY {literal}", (str(destination),))
            connection.execute("SELECT sqlcipher_export('encrypted')").fetchone()
            connection.execute(f"PRAGMA encrypted.user_version={int(user_version)}")
            connection.execute(f"PRAGMA encrypted.application_id={int(application_id)}")
            connection.commit()
            connection.execute("DETACH DATABASE encrypted")
        with closing(connect(destination, new_key)) as check:
            _verify(check)
    except BaseException as exc:
        _remove_owned(destination)
        if isinstance(exc, driver.DatabaseError):
            raise SQLCipherError("Преобразование не выполнено: неверный ключ или повреждённая база") from None
        raise
    return destination


def encrypt_copy(source: Path, destination: Path, key: bytes) -> Path:
    """Convert a consistent SQLite backup using sqlcipher_export; original untouched."""
    _key_literal(key)
    _driver()
    source = Path(source).resolve()
    if Path(str(source) + ".ipc-token").exists():
        raise SQLCipherError("Перед преобразованием остановите фоновый процесс")
    with tempfile.TemporaryDirectory(prefix="ca-sqlcipher-", dir=Path(destination).absolute().parent) as temp:
        snapshot = Path(temp) / "snapshot.db"
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as plain:
            with closing(sqlite3.connect(snapshot)) as backup:
                plain.backup(backup)
                backup.execute("PRAGMA journal_mode=DELETE")
        return _export(snapshot, destination, key, None)


def rotate_key_copy(source: Path, destination: Path, old_key: bytes, new_key: bytes) -> Path:
    """Rotate into a NEW verified database. Caller must stop all database users first."""
    if Path(str(Path(source).resolve()) + ".ipc-token").exists():
        raise SQLCipherError("Перед сменой ключа остановите фоновый процесс")
    return _export(source, destination, new_key, old_key)


def create_sqlalchemy_engine(path: Path, key: bytes, *, read_only: bool = True):
    """Optional standalone engine; does not run schema migrations or bootstrap."""
    from sqlalchemy import create_engine
    _key_literal(key)
    driver = _driver()
    return create_engine("sqlite://", module=driver, creator=lambda: connect(path, key, read_only=read_only))

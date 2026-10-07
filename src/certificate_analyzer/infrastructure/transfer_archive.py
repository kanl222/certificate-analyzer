"""Offline portable backup API. Not connected to the GUI or running daemon."""

import io
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import zipfile

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from certificate_analyzer.infrastructure.database.migrations import SCHEMA_VERSION

HEADER = b"CATRANSFER\x01"
MAX_SIZE = 128 * 1024 * 1024
MAX_FILES = 10000
PATH_FIELDS = (("certificates", "source_path"), ("certificate_sources", "path"), ("mchds", "source_path"))


class ArchiveError(ValueError):
    """Invalid backup, incomplete source or failed authentication."""


def _key(password: str, salt: bytes) -> bytes:
    if not isinstance(password, str) or len(password) < 12:
        raise ArchiveError("Пароль должен содержать не менее 12 символов")
    if len(password.encode("utf-8")) > 1024:
        raise ArchiveError("Пароль слишком длинный")
    return Scrypt(salt=salt, length=32, n=2**17, r=8, p=1).derive(password.encode("utf-8"))


def _read(path: Path) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        raise ArchiveError("Превышен предел размера архива: 128 МиБ")
    return data


def _validate_db(connection):
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ArchiveError("База данных повреждена")
    if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        raise ArchiveError("Для переноса нужна база текущей версии приложения")
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {table for table, _ in PATH_FIELDS} <= tables:
        raise ArchiveError("Архив не содержит базу Certificate Analyzer")
    if connection.execute("SELECT 1 FROM sqlite_master WHERE type='trigger' LIMIT 1").fetchone():
        raise ArchiveError("База с триггерами не поддерживается")


def export_archive(database: Path, storage: Path, destination: Path, password: str) -> Path:
    """Export a SQLite backup and all managed/referenced files. Stop writer first."""
    database, storage, destination = Path(database).resolve(), Path(storage).resolve(), Path(destination)
    if database.with_suffix(database.suffix + ".ipc-token").exists():
        raise ArchiveError("Перед экспортом остановите фоновый процесс")
    if destination.exists():
        raise ArchiveError("Файл архива уже существует")
    salt, nonce = os.urandom(16), os.urandom(12)
    key = _key(password, salt)
    with tempfile.TemporaryDirectory(prefix="ca-export-") as temp:
        snapshot = Path(temp) / "certificates.db"
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as backup:
                source.backup(backup)
                backup.execute("PRAGMA journal_mode=DELETE")
        files, paths = {}, {}
        total = 0

        def include(path):
            nonlocal total
            path = Path(path)
            if path.is_symlink() or not path.is_file():
                raise ArchiveError(f"Файл отсутствует или является ссылкой: {path}")
            if str(path) not in paths:
                if len(files) >= MAX_FILES:
                    raise ArchiveError("Слишком много файлов")
                name = f"files/{len(files):06d}{path.suffix.lower()}"
                if not re.fullmatch(r"files/\d{6}\.[a-z0-9]{1,8}", name):
                    raise ArchiveError(f"Неподдерживаемое имя файла: {path.name}")
                data = _read(path)
                total += len(data)
                if total > MAX_SIZE:
                    raise ArchiveError("Превышен предел размера архива: 128 МиБ")
                files[name] = data
                paths[str(path)] = name
            return paths[str(path)]

        if storage.exists():
            for path in sorted(storage.rglob("*")):
                if path.is_symlink():
                    raise ArchiveError(f"Ссылки в хранилище не поддерживаются: {path}")
                if path.is_file():
                    include(path)
        mappings = {}
        with closing(sqlite3.connect(snapshot)) as connection:
            _validate_db(connection)
            for table, column in PATH_FIELDS:
                for (old,) in connection.execute(f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL AND "{column}" != \'\''):
                    candidate = Path(old)
                    if not candidate.is_file() and table in {"certificates", "certificate_sources"}:
                        field = "fingerprint_sha256" if table == "certificates" else "fingerprint"
                        fingerprint = connection.execute(f'SELECT "{field}" FROM "{table}" WHERE "{column}"=?', (old,)).fetchone()[0]
                        if not re.fullmatch(r"[0-9a-fA-F]{64}", fingerprint):
                            raise ArchiveError("Некорректный SHA-256 сертификата")
                        candidate = storage / f"{fingerprint}.cer"
                        if not candidate.is_file():
                            alternatives = connection.execute("SELECT path FROM certificate_sources WHERE fingerprint=?", (fingerprint,)).fetchall()
                            candidate = next((Path(path) for (path,) in alternatives if Path(path).is_file()), candidate)
                    mappings.setdefault(f"{table}.{column}", {})[old] = include(candidate)
                if table == "certificate_sources":
                    # Distinct source paths are primary keys, even if their files disappeared.
                    used = set()
                    for old, name in mappings.get(f"{table}.{column}", {}).items():
                        if name in used:
                            if len(files) >= MAX_FILES or total + len(files[name]) > MAX_SIZE:
                                raise ArchiveError("Превышен предел размера архива")
                            alias = f"files/{len(files):06d}{Path(name).suffix}"
                            files[alias] = files[name]
                            total += len(files[name])
                            mappings[f"{table}.{column}"][old] = alias
                            name = alias
                        used.add(name)
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("certificates.db", _read(snapshot))
            archive.writestr("manifest.json", json.dumps({"version": 1, "paths": mappings}, ensure_ascii=False))
            for name, data in files.items():
                archive.writestr(name, data)
        if payload.tell() > MAX_SIZE - len(HEADER) - 44:
            raise ArchiveError("Превышен предел размера архива: 128 МиБ")
        header = HEADER + salt + nonce
        encrypted = header + AESGCM(key).encrypt(nonce, payload.getvalue(), header)
        # Exclusive creation never overwrites an existing backup.
        with destination.open("xb") as stream:
            try:
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                stream.close()
                destination.unlink(missing_ok=True)
                raise
    return destination


def import_archive(archive_path: Path, destination: Path, password: str) -> Path:
    """Restore into a NEW profile directory; never merge with an existing profile."""
    destination = Path(destination).absolute()
    if destination.exists():
        raise ArchiveError("Для восстановления выберите новую папку")
    envelope = _read(Path(archive_path))
    offset = len(HEADER)
    if not envelope.startswith(HEADER) or len(envelope) < offset + 44:
        raise ArchiveError("Неподдерживаемый или повреждённый архив")
    salt, nonce = envelope[offset:offset + 16], envelope[offset + 16:offset + 28]
    header = envelope[:offset + 28]
    try:
        payload = AESGCM(_key(password, salt)).decrypt(nonce, envelope[offset + 28:], header)
    except InvalidTag:
        raise ArchiveError("Неверный пароль или архив повреждён") from None
    with tempfile.TemporaryDirectory(prefix="ca-import-", dir=destination.parent) as temp:
        staging = Path(temp) / "profile"
        staging.mkdir(mode=0o700)
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                entries = archive.infolist()
                names = [entry.filename for entry in entries]
                if len(entries) > MAX_FILES + 2 or len(set(names)) != len(names):
                    raise ArchiveError("Некорректный список файлов архива")
                if not {"certificates.db", "manifest.json"} <= set(names):
                    raise ArchiveError("В архиве отсутствует база или описание")
                if sum(entry.file_size for entry in entries) > MAX_SIZE:
                    raise ArchiveError("Архив превышает допустимый размер")
                for entry in entries:
                    if entry.compress_type != zipfile.ZIP_STORED or (
                        entry.filename not in {"certificates.db", "manifest.json"}
                        and not re.fullmatch(r"files/\d{6}\.[a-z0-9]{1,8}", entry.filename)
                    ):
                        raise ArchiveError("Недопустимый файл или формат упаковки")
                manifest = json.loads(archive.read("manifest.json"))
                if not isinstance(manifest, dict) or manifest["version"] != 1:
                    raise ArchiveError("Неподдерживаемая версия архива")
                for name in names:
                    if name == "manifest.json":
                        continue
                    path = staging / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.read(name))
                    path.chmod(0o600)
        except (zipfile.BadZipFile, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ArchiveError("Некорректное содержимое архива") from exc
        with closing(sqlite3.connect(staging / "certificates.db")) as connection:
            connection.execute("PRAGMA trusted_schema=OFF")
            _validate_db(connection)
            expected = {f"{table}.{column}" for table, column in PATH_FIELDS}
            if not isinstance(manifest["paths"], dict) or not set(manifest["paths"]) <= expected:
                raise ArchiveError("Некорректная карта путей")
            for table, column in PATH_FIELDS:
                rows = connection.execute(f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL AND "{column}" != \'\'').fetchall()
                mapping = manifest["paths"].get(f"{table}.{column}", {})
                if not isinstance(mapping, dict):
                    raise ArchiveError("Некорректная карта путей")
                for (old,) in rows:
                    name = mapping.get(old)
                    if not isinstance(name, str) or name not in names or not name.startswith("files/"):
                        raise ArchiveError("В архиве отсутствует файл из базы")
                    connection.execute(f'UPDATE "{table}" SET "{column}"=? WHERE "{column}"=?', (str(destination / name), old))
            _validate_db(connection)
            connection.commit()
        settings = {"database_path": str(destination / "certificates.db"), "storage_folder": str(destination / "files"), "folders": {}, "mchd_folder": str(destination / "files"), "export_folder": str(destination / "reports")}
        (staging / "settings.json").write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
        (staging / "settings.json").chmod(0o600)
        # Reserve destination exclusively. Roll back only files created by this call.
        destination.mkdir(mode=0o700)
        try:
            for child in staging.iterdir():
                child.rename(destination / child.name)
        except BaseException:
            import shutil
            shutil.rmtree(destination)
            raise
    return destination / "settings.json"

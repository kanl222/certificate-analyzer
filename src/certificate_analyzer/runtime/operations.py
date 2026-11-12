"""Журнал результатов IPC-операций. Прерванная операция никогда не повторяется автоматически."""

from __future__ import annotations

from contextlib import closing
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
from typing import Any
from uuid import UUID


class OperationJournal:
    """Управление персистентным журналом операций демона для обеспечения идемпотентности."""

    def __init__(self, path: str | Path) -> None:
        """Инициализирует журнал операций.

        Args:
            path: Путь к файлу базы данных журнала SQLite.
        """
        self.path: Path = Path(path)
        with closing(self.connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, digest_key BLOB NOT NULL)")
            db.execute("INSERT OR IGNORE INTO metadata VALUES (1, ?)", (secrets.token_bytes(32),))
            self.key: bytes = db.execute("SELECT digest_key FROM metadata WHERE id=1").fetchone()[0]
            db.execute("""CREATE TABLE IF NOT EXISTS operations (
                id TEXT PRIMARY KEY, digest TEXT NOT NULL, state TEXT NOT NULL,
                response TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            # Фиксация сервиса и квитанция не образуют одну транзакцию (включая файловые операции).
            db.execute("UPDATE operations SET state='unknown' WHERE state='running'")
            db.execute("DELETE FROM operations WHERE created_at < datetime('now', '-14 days')")

    def connect(self) -> sqlite3.Connection:
        """Создает и настраивает прямое подключение к базе данных журнала."""
        db: sqlite3.Connection = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def validate(identifier: str) -> None:
        """Проверяет корректность UUID-идентификатора операции.

        Args:
            identifier: Строковый идентификатор.

        Raises:
            ValueError: Если идентификатор не является валидным UUID.
        """
        if not isinstance(identifier, str) or str(UUID(identifier)) != identifier:
            raise ValueError("Некорректный идентификатор операции")

    def begin(self, identifier: str, request: dict[str, Any]) -> dict[str, Any] | None:
        """Вызывается под блокировкой команд writer. Возвращает сохраненный ответ или резервирует ID.

        Args:
            identifier: Идентификатор операции.
            request: Словарь запроса IPC.

        Returns:
            dict | None: Сохраненный результат завершенной операции или None при новом запуске.

        Raises:
            ValueError: При попытке повторного вызова с другими параметрами или в состоянии unknown.
        """
        self.validate(identifier)
        payload: dict[str, Any] = {key: request[key] for key in ("service", "method", "args", "kwargs")}
        # Пароли и аргументы не сохраняются в открытом виде; дайджест на ключе защищает от подбора.
        digest: str = hmac.new(self.key, json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        with closing(self.connect()) as db, db:
            row: tuple[Any, ...] | None = db.execute(
                "SELECT digest, state, response FROM operations WHERE id=?", (identifier,)
            ).fetchone()
            if row:
                if not hmac.compare_digest(digest, row[0]):
                    raise ValueError("Идентификатор операции уже использован с другими параметрами")
                if row[1] == "completed":
                    return json.loads(row[2])
                raise ValueError("Результат операции неизвестен; повторное выполнение заблокировано. Проверьте данные.")
            db.execute("INSERT INTO operations(id,digest,state) VALUES (?,?,'running')", (identifier, digest))
        return None

    def finish(self, identifier: str, response: dict[str, Any]) -> None:
        """Фиксирует успешное или ошибочное завершение операции.

        Args:
            identifier: Идентификатор операции.
            response: Результат ответа IPC.
        """
        with closing(self.connect()) as db, db:
            db.execute(
                "UPDATE operations SET state='completed', response=? WHERE id=?",
                (json.dumps(response, ensure_ascii=False), identifier),
            )

    def status(self, identifier: str) -> dict[str, Any]:
        """Запрашивает текущий статус операции по её идентификатору.

        Args:
            identifier: Идентификатор операции.

        Returns:
            dict: Словарь со статусом ('running', 'completed', 'unknown', 'not_found') и ответом.
        """
        self.validate(identifier)
        with closing(self.connect()) as db:
            row: tuple[Any, ...] | None = db.execute(
                "SELECT state,response FROM operations WHERE id=?", (identifier,)
            ).fetchone()
        if row is None:
            return {"state": "not_found"}
        result: dict[str, Any] = {"state": row[0]}
        if row[1] is not None:
            result["response"] = json.loads(row[1])
        return result

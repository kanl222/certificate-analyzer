"""Durable IPC receipts. An interrupted operation is never automatically replayed."""

from contextlib import closing
import hashlib
import hmac
import json
import secrets
import sqlite3
from uuid import UUID


class OperationJournal:
    def __init__(self, path):
        self.path = path
        with closing(self.connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY, digest_key BLOB NOT NULL)")
            db.execute("INSERT OR IGNORE INTO metadata VALUES (1, ?)", (secrets.token_bytes(32),))
            self.key = db.execute("SELECT digest_key FROM metadata WHERE id=1").fetchone()[0]
            db.execute("""CREATE TABLE IF NOT EXISTS operations (
                id TEXT PRIMARY KEY, digest TEXT NOT NULL, state TEXT NOT NULL,
                response TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
            # A service commit and its receipt cannot be one transaction (file operations too).
            db.execute("UPDATE operations SET state='unknown' WHERE state='running'")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def validate(identifier):
        if not isinstance(identifier, str) or str(UUID(identifier)) != identifier:
            raise ValueError("Некорректный идентификатор операции")

    def begin(self, identifier, request):
        """Called under the writer command lock. Return a prior receipt or reserve the ID."""
        self.validate(identifier)
        payload = {key: request[key] for key in ("service", "method", "args", "kwargs")}
        # Persist no arguments/passwords; a keyed digest also prevents password guessing
        # from the digest alone. The journal file is private to the current OS user.
        digest = hmac.new(self.key, json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        with closing(self.connect()) as db, db:
            row = db.execute("SELECT digest, state, response FROM operations WHERE id=?", (identifier,)).fetchone()
            if row:
                if not hmac.compare_digest(digest, row[0]):
                    raise ValueError("Идентификатор операции уже использован с другими параметрами")
                if row[1] == "completed":
                    return json.loads(row[2])
                raise ValueError("Результат операции неизвестен; повторное выполнение заблокировано. Проверьте данные.")
            db.execute("INSERT INTO operations(id,digest,state) VALUES (?,?,'running')", (identifier, digest))
        return None

    def finish(self, identifier, response):
        with closing(self.connect()) as db, db:
            db.execute("UPDATE operations SET state='completed', response=? WHERE id=?",
                       (json.dumps(response, ensure_ascii=False), identifier))

    def status(self, identifier):
        self.validate(identifier)
        with closing(self.connect()) as db:
            row = db.execute("SELECT state,response FROM operations WHERE id=?", (identifier,)).fetchone()
        if row is None:
            return {"state": "not_found"}
        result = {"state": row[0]}
        if row[1] is not None:
            result["response"] = json.loads(row[1])
        return result

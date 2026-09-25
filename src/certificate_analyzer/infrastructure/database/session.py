"""SQLAlchemy engine and sessions owned by an application, never by module import."""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from certificate_analyzer.infrastructure.config.paths import config_dir
from certificate_analyzer.infrastructure.database.models import Base
from certificate_analyzer.infrastructure.database.migrations import migrate


def get_database_path(settings=None):
    if settings and settings.database_path:
        return Path(settings.database_path).expanduser().resolve()
    if not os.environ.get("CERTIFICATE_ANALYZER_HOME"):
        previous = Path.home() / ".local/share/certificate-analyzer/certificates.db"
        if previous.is_file():
            return previous
    return config_dir() / "certificates.db"


class Database:
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            "sqlite:///" + self.path.as_posix(), connect_args={"timeout": 30}
        )

        @event.listens_for(self.engine, "connect")
        def configure(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=30000")

        try:
            migrate(self.engine, self.path)
            Base.metadata.create_all(self.engine)
            with self.engine.connect() as connection:
                connection.exec_driver_sql("PRAGMA journal_mode=WAL")
            self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        except Exception:
            self.engine.dispose()
            raise

    def close(self):
        self.engine.dispose()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

"""Инициализация базы данных SQLAlchemy."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from certificate_analyzer.infrastructure.database.models import Base


def get_database_path() -> Path:
    """Вернуть путь к локальной базе данных приложения."""

    data_dir = Path.home() / ".local" / "share" / "certificate-analyzer"
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir / "certificates.db"


DATABASE_PATH = get_database_path()
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"


engine = create_engine(
    DATABASE_URL,
    echo=False,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def init_db() -> None:
    """Создать таблицы, если они ещё не существуют."""

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Создать SQLAlchemy-сессию."""

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
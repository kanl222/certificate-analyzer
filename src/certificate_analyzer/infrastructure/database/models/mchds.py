from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class MchdModel(Base):
    __tablename__ = "mchds"
    
    unified_number: Mapped[str] = mapped_column(String(255), primary_key=True)
    internal_number: Mapped[str | None] = mapped_column(String(255))
    principal_inn: Mapped[str] = mapped_column(String(20))
    principal_name: Mapped[str] = mapped_column(String(255))
    representative_inn: Mapped[str] = mapped_column(String(20))
    representative_fio: Mapped[str] = mapped_column(String(255))
    representative_snils: Mapped[str] = mapped_column(String(20))
    valid_from: Mapped[datetime] = mapped_column(DateTime)
    valid_to: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50))
    authority_codes: Mapped[str | None] = mapped_column(String(1024))
    source_path: Mapped[str | None] = mapped_column(String(1024))

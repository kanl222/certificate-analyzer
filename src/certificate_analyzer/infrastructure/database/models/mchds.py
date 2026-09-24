from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean
from datetime import datetime
from typing import List, Optional
from .base import Base


class MchdModel(Base):
    __tablename__ = "mchds"
    
    unified_number: Mapped[str] = mapped_column(String(255), primary_key=True)
    internal_number: Mapped[Optional[str]] = mapped_column(String(255))
    principal_inn: Mapped[str] = mapped_column(String(20))
    principal_name: Mapped[str] = mapped_column(String(255))
    representative_inn: Mapped[str] = mapped_column(String(20))
    representative_fio: Mapped[str] = mapped_column(String(255))
    representative_snils: Mapped[str] = mapped_column(String(20))
    valid_from: Mapped[datetime] = mapped_column(DateTime)
    valid_to: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50))
    authority_codes: Mapped[Optional[str]] = mapped_column(String(1024))
    source_path: Mapped[Optional[str]] = mapped_column(String(1024))

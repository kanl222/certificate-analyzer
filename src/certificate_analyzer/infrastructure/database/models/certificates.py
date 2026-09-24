from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class CertificateModel(Base):
    __tablename__ = "certificates"
    
    fingerprint_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject: Mapped[str] = mapped_column(String(255))
    issuer: Mapped[str] = mapped_column(String(255))
    valid_from: Mapped[datetime] = mapped_column(DateTime)
    valid_to: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    has_private_key_link: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_name: Mapped[str | None] = mapped_column(String(255))
    source_path: Mapped[str | None] = mapped_column(String(1024))
    
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    employee: Mapped[Optional["EmployeeModel"]] = relationship(back_populates="certificates")


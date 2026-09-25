"""SQLAlchemy-модель заявок на получение сертификатов."""

from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .certificates import CertificateModel
    from .employees import EmployeeModel


class CertificateRequestModel(Base):
    """Таблица заявок на выпуск и учет сертификатов."""

    __tablename__ = "certificate_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    department: Mapped[str] = mapped_column(String(255), default="")
    needs_signature: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(50), default="NOT_SUBMITTED", index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    certificate_fingerprint: Mapped[str | None] = mapped_column(
        ForeignKey("certificates.fingerprint_sha256", ondelete="SET NULL"),
        nullable=True,
    )
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    employee: Mapped["EmployeeModel | None"] = relationship(back_populates="requests")
    certificate: Mapped["CertificateModel | None"] = relationship(back_populates="requests")

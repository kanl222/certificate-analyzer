from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

if TYPE_CHECKING:
    from .certificate_requests import CertificateRequestModel
    from .employees import EmployeeModel


class CertificateModel(Base):
    __tablename__ = "certificates"
    fingerprint_sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject: Mapped[str] = mapped_column(String(255), index=True)
    issuer: Mapped[str] = mapped_column(String(255))
    valid_from: Mapped[datetime] = mapped_column(DateTime)
    valid_to: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(50))
    serial_number: Mapped[str | None] = mapped_column(String(100))
    has_private_key_link: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_name: Mapped[str | None] = mapped_column(String(255))
    source_path: Mapped[str | None] = mapped_column(Text)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    employee: Mapped["EmployeeModel"] = relationship(back_populates="certificates")
    requests: Mapped[list["CertificateRequestModel"]] = relationship(
        back_populates="certificate"
    )
    sources: Mapped[list["CertificateSourceModel"]] = relationship(
        back_populates="certificate", cascade="all, delete-orphan"
    )
    email: Mapped[str] = mapped_column(Text, default="")
    office: Mapped[str] = mapped_column(Text, default="")
    department: Mapped[str] = mapped_column(Text, default="")
    phones_json: Mapped[str] = mapped_column(Text, default="[]")
    original_name: Mapped[str] = mapped_column(Text, default="")
    search_text: Mapped[str] = mapped_column(Text, default="")


class CertificateSourceModel(Base):
    __tablename__ = "certificate_sources"
    path: Mapped[str] = mapped_column(Text, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(
        ForeignKey("certificates.fingerprint_sha256", ondelete="CASCADE"), index=True
    )
    content_sha256: Mapped[str] = mapped_column(String(64), default="")
    file_name: Mapped[str | None] = mapped_column(String(255), default="")
    size: Mapped[int | None] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow)

    certificate: Mapped["CertificateModel"] = relationship(back_populates="sources")


CertificateFileModel = CertificateSourceModel


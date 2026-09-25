"""SQLAlchemy-модель сотрудника организации."""

from datetime import date
from typing import TYPE_CHECKING
from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .certificate_requests import CertificateRequestModel
    from .certificates import CertificateModel


class EmployeeModel(Base):
    """Таблица сотрудников организации."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    office: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phones: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    snils: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    certificates: Mapped[list["CertificateModel"]] = relationship(
        back_populates="employee"
    )
    requests: Mapped[list["CertificateRequestModel"]] = relationship(
        back_populates="employee"
    )

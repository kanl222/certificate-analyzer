"""SQLAlchemy-модели машиночитаемых доверенностей (МЧД) и классификатора полномочий."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class MchdModel(Base):
    """Модель машиночитаемой доверенности (МЧД) в базе данных SQLite.

    Хранит основные регистрационные реквизиты доверенности, информацию
    о доверителе, представителе и сроках действия.
    """

    __tablename__ = "mchds"

    unified_number: Mapped[str] = mapped_column(String(255), primary_key=True)
    internal_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    principal_inn: Mapped[str] = mapped_column(String(20))
    principal_name: Mapped[str] = mapped_column(String(255))
    representative_inn: Mapped[str] = mapped_column(String(20))
    representative_fio: Mapped[str] = mapped_column(String(255))
    representative_snils: Mapped[str] = mapped_column(String(20))
    valid_from: Mapped[datetime] = mapped_column(DateTime)
    valid_to: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(50))
    authority_codes: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    authorities: Mapped[list["MchdAuthorityModel"]] = relationship(
        "MchdAuthorityModel",
        back_populates="mchd",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MchdAuthorityModel(Base):
    """Модель полномочия МЧД в нормализованной таблице БД.

    Связана с доверенностью отношением Many-to-One через единый
    регистрационный номер (unified_number).
    """

    __tablename__ = "mchd_authorities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mchd_number: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("mchds.unified_number", ondelete="CASCADE"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    mchd: Mapped["MchdModel"] = relationship(
        "MchdModel",
        back_populates="authorities",
    )

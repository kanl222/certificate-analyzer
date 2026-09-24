
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class EmployeeModel(Base):
    __tablename__ = "employees"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    department: Mapped[str | None] = mapped_column(String(255))
    office: Mapped[str | None] = mapped_column(String(50))
    phones: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    
    certificates: Mapped[list["CertificateModel"]] = relationship(back_populates="employee")
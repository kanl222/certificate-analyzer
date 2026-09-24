from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean
from datetime import datetime
from typing import List, Optional
from .base import Base


class EmployeeModel(Base):
    __tablename__ = "employees"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    department: Mapped[Optional[str]] = mapped_column(String(255))
    office: Mapped[Optional[str]] = mapped_column(String(50))
    phones: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    
    certificates: Mapped[List["CertificateModel"]] = relationship(back_populates="employee")
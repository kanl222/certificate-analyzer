"""Доменная модель организации и её полномочного представителя."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from certificate_analyzer.domain.models.employee import Employee


@dataclass(slots=True)
class OrganizationRepresentative:
    """Полномочный представитель или руководитель организации."""

    full_name: str
    inn: str
    snils: str
    position: str = "Руководитель"


@dataclass(slots=True)
class Organization:
    """Доменная модель организации для формирования МЧД и документов."""

    short_name: str
    full_name: str
    inn: str
    ogrn: str
    id: int | None = None
    kpp: str | None = None
    address: str = ""
    director_employee_id: int | None = None
    director_employee: Optional["Employee"] = None
    representative: OrganizationRepresentative | None = None

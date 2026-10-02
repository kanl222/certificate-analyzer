"""Доменная модель сотрудника организации."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(slots=True)
class Employee:
    """Сущность сотрудника организации.

    Является центральным источником персональных данных для сертификатов,
    заявок на их получение и машиночитаемых доверенностей (МЧД).

    Attributes:
        full_name: Полное имя (ФИО) сотрудника.
        department: Подразделение или отдел.
        office: Номер кабинета / офиса.
        phones: Список контактных телефонов.
        id: Уникальный идентификатор в базе данных.
        position: Должность сотрудника.
        email: Адрес корпоративной электронной почты.
        inn: Индивидуальный номер налогоплательщика (ИНН).
        snils: Страховой номер индивидуального лицевого счёта (СНИЛС).
        birth_date: Дата рождения.
        is_management: Признак принадлежности к руководящему составу (руководство).
    """

    full_name: str
    department: str | None = None
    office: str | None = None
    phones: list[str] = field(default_factory=list)
    id: int | None = None
    position: str | None = None
    email: str | None = None
    inn: str | None = None
    snils: str | None = None
    birth_date: date | None = None
    is_management: bool = False

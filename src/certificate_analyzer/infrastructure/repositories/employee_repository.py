"""Репозиторий сотрудников организации на базе SQLAlchemy и SQLite."""

from sqlalchemy import select

from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.infrastructure.database.models.employees import EmployeeModel


class EmployeeRepository:
    """Репозиторий для управления записями сотрудников в базе данных."""

    def __init__(self, session_factory):
        """Инициализирует репозиторий фабрикой сессий.

        Args:
            session_factory: Фабрика сессий SQLAlchemy.
        """
        self.sessions = session_factory

    @staticmethod
    def _to_domain(model: EmployeeModel) -> Employee:
        """Преобразует модель SQLAlchemy в доменную сущность Employee.

        Args:
            model: Экземпляр EmployeeModel.

        Returns:
            Employee: Доменная модель сотрудника.
        """
        phones = [p.strip() for p in (model.phones or "").split(",") if p.strip()]
        return Employee(
            id=model.id,
            full_name=model.full_name,
            department=model.department,
            office=model.office,
            phones=phones,
            email=model.email,
            position=model.position,
            inn=model.inn,
            snils=model.snils,
            birth_date=model.birth_date,
        )

    def save(self, employee: Employee) -> Employee:
        """Сохраняет или обновляет запись сотрудника.

        Args:
            employee: Доменная модель сотрудника.

        Returns:
            Employee: Сохраненный сотрудник с присвоенным ID.
        """
        phones_str = ", ".join(employee.phones) if employee.phones else None
        with self.sessions.begin() as session:
            if employee.id:
                model = session.get(EmployeeModel, employee.id)
            else:
                model = session.scalars(
                    select(EmployeeModel).where(EmployeeModel.full_name == employee.full_name)
                ).first()

            if not model:
                model = EmployeeModel(
                    full_name=employee.full_name,
                    department=employee.department,
                    office=employee.office,
                    phones=phones_str,
                    email=employee.email,
                    position=employee.position,
                    inn=employee.inn,
                    snils=employee.snils,
                    birth_date=employee.birth_date,
                )
                session.add(model)
                session.flush()
            else:
                model.department = employee.department or model.department
                model.office = employee.office or model.office
                if phones_str:
                    model.phones = phones_str
                model.email = employee.email or model.email
                model.position = employee.position or model.position
                model.inn = employee.inn or model.inn
                model.snils = employee.snils or model.snils
                model.birth_date = employee.birth_date or model.birth_date

            session.flush()
            session.refresh(model)
            return self._to_domain(model)

    def get_by_id(self, employee_id: int) -> Employee | None:
        """Возвращает сотрудника по его идентификатору.

        Args:
            employee_id: Первичный ключ сотрудника.

        Returns:
            Employee | None: Найденный сотрудник или None.
        """
        with self.sessions() as session:
            model = session.get(EmployeeModel, employee_id)
            return self._to_domain(model) if model else None

    def find_by_name(self, full_name: str) -> Employee | None:
        """Находит сотрудника по точному ФИО.

        Args:
            full_name: Полное имя сотрудника.

        Returns:
            Employee | None: Сотрудник или None.
        """
        with self.sessions() as session:
            model = session.scalars(
                select(EmployeeModel).where(EmployeeModel.full_name == full_name.strip())
            ).first()
            return self._to_domain(model) if model else None

    def list_all(self, search: str | None = None) -> list[Employee]:
        """Возвращает список всех сотрудников.

        Args:
            search: Строка поиска по ФИО, подразделению или должности (опционально).

        Returns:
            list[Employee]: Список сотрудников.
        """
        with self.sessions() as session:
            stmt = select(EmployeeModel).order_by(EmployeeModel.full_name)
            models = session.scalars(stmt).all()
            if search and search.strip():
                term = search.strip().casefold()
                return [
                    self._to_domain(m)
                    for m in models
                    if term in (m.full_name or "").casefold()
                    or term in (m.department or "").casefold()
                    or term in (m.position or "").casefold()
                    or term in (m.office or "").casefold()
                    or term in (m.phones or "").casefold()
                    or term in (m.email or "").casefold()
                ]
            return [self._to_domain(m) for m in models]


    def delete(self, employee_id: int) -> bool:
        """Удаляет запись сотрудника по первичному ключу.

        Args:
            employee_id: Идентификатор сотрудника.

        Returns:
            bool: True, если сотрудник был найден и удален, иначе False.
        """
        with self.sessions.begin() as session:
            model = session.get(EmployeeModel, employee_id)
            if not model:
                return False
            session.delete(model)
            return True


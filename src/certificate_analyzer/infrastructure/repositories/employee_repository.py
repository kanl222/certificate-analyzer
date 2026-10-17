"""Репозиторий сотрудников организации на базе SQLAlchemy и SQLite."""

from sqlalchemy import func, or_, select

from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.infrastructure.database.search import casefold_contains
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
            is_management=bool(model.is_management),
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
                # Новая запись не имеет идентификатора; одно лишь имя не является уникальным ключом.
                model = None

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
                    is_management=employee.is_management,
                )
                session.add(model)
                session.flush()
            else:
                model.full_name = employee.full_name
                model.department = employee.department
                model.office = employee.office
                model.phones = phones_str
                model.email = employee.email
                model.position = employee.position
                model.inn = employee.inn
                model.snils = employee.snils
                model.birth_date = employee.birth_date
                model.is_management = employee.is_management

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

    def find_by_name(self, full_name: str, department: str | None = None) -> Employee | None:
        """Находит сотрудника по точному ФИО.

        Args:
            full_name: Полное имя сотрудника.

        Returns:
            Employee | None: Сотрудник или None.
        """
        with self.sessions() as session:
            statement = select(EmployeeModel).where(EmployeeModel.full_name == full_name.strip())
            if department:
                statement = statement.where(EmployeeModel.department == department)
            models = session.scalars(
                statement
            ).all()
            return self._to_domain(models[0]) if len(models) == 1 else None

    def _search_condition(self, session, search):
        condition = casefold_contains(session, (
            EmployeeModel.full_name, EmployeeModel.department,
            EmployeeModel.position, EmployeeModel.office,
            EmployeeModel.phones, EmployeeModel.email,
        ), search)
        if search.strip().casefold() in ("руководство", "руководитель"):
            condition = or_(condition, EmployeeModel.is_management.is_(True))
        return condition

    def list_all(self, search: str | None = None, *, limit: int | None = None, offset: int = 0) -> list[Employee]:
        """Возвращает список всех сотрудников.

        Args:
            search: Строка поиска по ФИО, подразделению или должности (опционально).

        Returns:
            list[Employee]: Список сотрудников.
        """
        if offset < 0 or (limit is not None and limit < 0):
            raise ValueError("Лимит и смещение не могут быть отрицательными")
        with self.sessions() as session:
            stmt = select(EmployeeModel).order_by(EmployeeModel.full_name, EmployeeModel.id)
            if search and search.strip():
                stmt = stmt.where(self._search_condition(session, search))
            if limit is not None:
                stmt = stmt.limit(limit)
            stmt = stmt.offset(offset)
            models = session.scalars(stmt).all()
            return [self._to_domain(m) for m in models]

    def count(self, search: str | None = None) -> int:
        with self.sessions() as session:
            stmt = select(func.count()).select_from(EmployeeModel)
            if search and search.strip():
                stmt = stmt.where(self._search_condition(session, search))
            return session.scalar(stmt) or 0


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

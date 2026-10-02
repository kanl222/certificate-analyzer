"""Сервис приложения для работы с сотрудниками организации."""

from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.infrastructure.repositories.employee_repository import (
    EmployeeRepository,
)


class EmployeeService:
    """Сервис учета и поиска сотрудников."""

    def __init__(self, repository: EmployeeRepository):
        """Инициализирует сервис сотрудников.

        Args:
            repository: Репозиторий сотрудников.
        """
        self.repository = repository

    def list_employees(self, search: str | None = None) -> list[Employee]:
        """Возвращает список сотрудников с возможностью поиска.

        Args:
            search: Подстрока поиска по ФИО, подразделению, должности.

        Returns:
            list[Employee]: Список найденных сотрудников.
        """
        return self.repository.list_all(search=search)

    def get_employee(self, employee_id: int) -> Employee | None:
        """Получает сотрудника по идентификатору.

        Args:
            employee_id: Первичный ключ сотрудника.

        Returns:
            Employee | None: Найденный сотрудник.
        """
        return self.repository.get_by_id(employee_id)

    def find_by_name(self, full_name: str) -> Employee | None:
        """Ищет сотрудника по полному имени.

        Args:
            full_name: ФИО сотрудника.

        Returns:
            Employee | None: Сотрудник или None.
        """
        return self.repository.find_by_name(full_name)

    def save_employee(self, employee: Employee) -> Employee:
        """Сохраняет данные сотрудника в базе.

        Args:
            employee: Доменная модель сотрудника.

        Returns:
            Employee: Сохраненный сотрудник.
        """
        return self.repository.save(employee)

    def get_or_create(
        self,
        full_name: str,
        department: str | None = None,
        is_management: bool = False,
    ) -> Employee:
        """Получает существующего сотрудника по ФИО или создает нового.

        Args:
            full_name: Полное имя (ФИО) сотрудника.
            department: Подразделение сотрудника при создании.
            is_management: Признак принадлежности к руководящему составу.

        Returns:
            Employee: Найденный или вновь созданный сотрудник.
        """
        existing = self.find_by_name(full_name)
        if existing:
            return existing
        return self.save_employee(
            Employee(
                full_name=full_name,
                department=department,
                is_management=is_management,
            )
        )

    def delete_employee(self, employee_id: int) -> bool:
        """Удаляет сотрудника по его идентификатору.

        Args:
            employee_id: Идентификатор сотрудника.

        Returns:
            bool: True, если сотрудник удален, иначе False.
        """
        return self.repository.delete(employee_id)



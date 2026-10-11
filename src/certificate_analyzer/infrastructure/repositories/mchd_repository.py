"""Репозиторий машиночитаемых доверенностей (МЧД) с нормализованными полномочиями."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from certificate_analyzer.domain.enums.mchd_status import MchdStatus
from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.infrastructure.database.models.mchds import (
    MchdAuthorityModel,
    MchdModel,
)


class MchdRepository:
    """Репозиторий для управления записями МЧД и полномочий в SQLite."""

    def __init__(self, session_factory: Any) -> None:
        """Инициализирует репозиторий фабрикой сессий или экземпляром сессии.

        Args:
            session_factory: Фабрика сессий SQLAlchemy (sessionmaker) или открытая сессия.
        """
        self._session_factory = session_factory

    @contextmanager
    def _read_session(self) -> Iterator[Session]:
        """Предоставляет контекст сессии для операций чтения.

        Yields:
            Session: Активная сессия SQLAlchemy.
        """
        if isinstance(self._session_factory, Session):
            yield self._session_factory
        elif callable(self._session_factory):
            with self._session_factory() as session:
                yield session
        else:
            yield self._session_factory

    @contextmanager
    def _write_session(self) -> Iterator[Session]:
        """Предоставляет контекст транзакционной сессии для операций записи.

        Yields:
            Session: Сессия SQLAlchemy с автоматической фиксацией или откатом транзакции.
        """
        if isinstance(self._session_factory, Session):
            yield self._session_factory
            self._session_factory.commit()
        elif hasattr(self._session_factory, "begin"):
            with self._session_factory.begin() as session:
                yield session
        elif callable(self._session_factory):
            with self._session_factory() as session:
                with session.begin():
                    yield session
        else:
            yield self._session_factory

    @staticmethod
    def _to_domain(model: MchdModel) -> MchdDocument:
        """Преобразует модель SQLAlchemy в доменную сущность MchdDocument.

        Args:
            model: Экземпляр MchdModel.

        Returns:
            MchdDocument: Доменная сущность МЧД с нормализованными полномочиями.
        """
        auth_codes: list[str] = []
        auth_names: list[str] = []

        if model.authorities:
            for auth in model.authorities:
                auth_codes.append(auth.code)
                auth_names.append(auth.name or "")
        elif model.authority_codes:
            auth_codes = [c.strip() for c in model.authority_codes.split(",") if c.strip()]
            auth_names = ["" for _ in auth_codes]

        try:
            status = MchdStatus[model.status]
        except KeyError:
            status = MchdStatus.ACTIVE

        return MchdDocument(
            unified_number=model.unified_number,
            internal_number=model.internal_number,
            principal_inn=model.principal_inn,
            principal_name=model.principal_name,
            representative_inn=model.representative_inn,
            representative_fio=model.representative_fio,
            representative_snils=model.representative_snils,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            status=status,
            authority_codes=auth_codes,
            authority_names=auth_names,
            source_path=model.source_path or "",
            details={},
        )

    def save(self, mchd: MchdDocument) -> MchdDocument:
        """Сохраняет или обновляет запись МЧД и ее нормализованные полномочия.

        Args:
            mchd: Доменная модель машиночитаемой доверенности.

        Returns:
            MchdDocument: Сохраненная доменная модель МЧД.
        """
        with self._write_session() as session:
            model = session.get(MchdModel, mchd.unified_number)

            if not model:
                model = MchdModel(unified_number=mchd.unified_number)
                session.add(model)

            model.internal_number = mchd.internal_number
            model.principal_inn = mchd.principal_inn
            model.principal_name = mchd.principal_name
            model.representative_inn = mchd.representative_inn
            model.representative_fio = mchd.representative_fio
            model.representative_snils = mchd.representative_snils
            model.valid_from = mchd.valid_from
            model.valid_to = mchd.valid_to
            model.status = mchd.status.name
            model.source_path = mchd.source_path
            model.authority_codes = (
                ",".join(mchd.authority_codes) if mchd.authority_codes else None
            )

            # Синхронизация нормализованных полномочий
            model.authorities.clear()
            names = mchd.authority_names or []
            for idx, code in enumerate(mchd.authority_codes):
                clean_code = code.strip()
                if not clean_code:
                    continue
                name_val = names[idx].strip() if idx < len(names) and names[idx] else None
                model.authorities.append(
                    MchdAuthorityModel(
                        mchd_number=mchd.unified_number,
                        code=clean_code,
                        name=name_val,
                    )
                )

            session.flush()
            session.refresh(model)
            return self._to_domain(model)

    def get_by_number(self, unified_number: str) -> MchdDocument | None:
        """Возвращает МЧД по уникальному единому регистрационному номеру.

        Args:
            unified_number: Уникальный номер доверенности.

        Returns:
            MchdDocument | None: Доменная сущность МЧД или None, если запись не найдена.
        """
        with self._read_session() as session:
            model = session.get(MchdModel, unified_number)
            return self._to_domain(model) if model else None

    def get_all(self) -> list[MchdDocument]:
        """Возвращает список всех доверенностей из базы данных.

        Returns:
            list[MchdDocument]: Полный список зарегистрированных доверенностей.
        """
        return self.list_all()

    def list_all(
        self,
        search: str | None = None,
        authority_code: str | None = None,
        status: MchdStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[MchdDocument]:
        """Возвращает список МЧД с фильтрацией по поисковой строке, коду полномочия и статусу.

        Args:
            search: Подстрока для поиска по номеру, ФИО, ИНН или организации.
            authority_code: Точный код полномочия для фильтрации через таблицу mchd_authorities.
            status: Статус доверенности MchdStatus.

        Returns:
            list[MchdDocument]: Отфильтрованный список доверенностей.
        """
        if offset < 0 or (limit is not None and limit < 0):
            raise ValueError("Лимит и смещение не могут быть отрицательными")
        with self._read_session() as session:
            stmt = select(MchdModel).order_by(MchdModel.valid_to.desc(), MchdModel.unified_number)

            if status is not None:
                stmt = stmt.where(MchdModel.status == status.name)

            if authority_code and authority_code.strip():
                stmt = stmt.where(MchdModel.authorities.any(
                    MchdAuthorityModel.code == authority_code.strip()
                ))

            if search and search.strip():
                term = search.strip().casefold()
                # SQLite lower()/NOCASE приводят к нижнему регистру только ASCII. Регистрируем Unicode casefold
                # для данного соединения, чтобы поиск по русским строкам сохранял ожидаемое поведение.
                connection = session.connection().connection.driver_connection
                connection.create_function("ca_casefold", 1, lambda value: (value or "").casefold(), deterministic=True)
                stmt = stmt.where(or_(*(func.ca_casefold(column).contains(term, autoescape=True)
                                       for column in (MchdModel.unified_number, MchdModel.principal_name,
                                                      MchdModel.principal_inn, MchdModel.representative_fio,
                                                      MchdModel.representative_inn, MchdModel.representative_snils,
                                                      MchdModel.internal_number))))

            stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)
            models = session.scalars(stmt).unique().all()
            return [self._to_domain(m) for m in models]

    def find_by_authority_code(self, code: str) -> list[MchdDocument]:
        """Находит все доверенности, содержащие указанный код полномочия.

        Args:
            code: Код полномочия по классификатору.

        Returns:
            list[MchdDocument]: Список подходящих доверенностей.
        """
        return self.list_all(authority_code=code)

    def find_by_representative_inn(self, inn: str) -> list[MchdDocument]:
        """Находит доверенности по ИНН представителя (физического лица).

        Args:
            inn: ИНН физического лица - представителя.

        Returns:
            list[MchdDocument]: Список доверенностей представителя.
        """
        with self._read_session() as session:
            stmt = (
                select(MchdModel)
                .where(MchdModel.representative_inn == inn.strip())
                .order_by(MchdModel.valid_to.desc())
            )
            models = session.scalars(stmt).unique().all()
            return [self._to_domain(m) for m in models]

    def find_by_principal_inn(self, inn: str) -> list[MchdDocument]:
        """Находит доверенности по ИНН доверителя (организации).

        Args:
            inn: ИНН организации-доверителя.

        Returns:
            list[MchdDocument]: Список выданных организацией доверенностей.
        """
        with self._read_session() as session:
            stmt = (
                select(MchdModel)
                .where(MchdModel.principal_inn == inn.strip())
                .order_by(MchdModel.valid_to.desc())
            )
            models = session.scalars(stmt).unique().all()
            return [self._to_domain(m) for m in models]

    def delete(self, unified_number: str) -> bool:
        """Удаляет доверенность по ее уникальному номеру.

        Полномочия в таблице mchd_authorities удаляются каскадно.

        Args:
            unified_number: Уникальный номер удаляемой доверенности.

        Returns:
            bool: True, если запись существовала и была удалена, иначе False.
        """
        with self._write_session() as session:
            model = session.get(MchdModel, unified_number)
            if not model:
                return False
            session.delete(model)
            return True

    def count(self) -> int:
        """Возвращает общее количество зарегистрированных доверенностей в базе данных.

        Returns:
            int: Число записей МЧД.
        """
        with self._read_session() as session:
            return session.scalar(select(func.count()).select_from(MchdModel)) or 0

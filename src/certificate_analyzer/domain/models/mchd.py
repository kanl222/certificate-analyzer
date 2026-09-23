"""Доменная модель машиночитаемой доверенности (МЧД)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from certificate_analyzer.domain.enums.mchd_status import MchdStatus


@dataclass(slots=True)
class MchdDocument:
    """Сущность машиночитаемой доверенности (МЧД)."""

    unified_number: str
    internal_number: Optional[str]
    principal_inn: str
    principal_name: str
    representative_inn: str
    representative_fio: str
    representative_snils: str
    valid_from: datetime
    valid_to: datetime
    status: MchdStatus = MchdStatus.ACTIVE
    # Полномочия должны храниться в нормализованной таблице БД
    authority_codes: List[str] = field(default_factory=list)

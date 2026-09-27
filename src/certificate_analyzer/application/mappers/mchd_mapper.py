"""Маппинг между доменной моделью MchdDocument и DTO MchdDTO."""

from datetime import datetime
from pathlib import Path

from certificate_analyzer.application.dto.mchd_dto import STATUS_VIEW, MchdDTO
from certificate_analyzer.domain.enums.mchd_status import MchdStatus
from certificate_analyzer.domain.models.mchd import MchdDocument


def mchd_to_dto(doc: MchdDocument) -> MchdDTO:
    """Преобразует доменную сущность MchdDocument в DTO MchdDTO для интерфейса.

    Args:
        doc: Доменная модель МЧД.

    Returns:
        MchdDTO: Объект передачи данных с отформатированными полями.
    """
    path = Path(doc.source_path) if doc.source_path else Path()
    status_label, color = STATUS_VIEW.get(doc.status, (doc.status.value, "#9e9e9e"))

    return MchdDTO(
        file_name=path.name,
        file_type="XML",
        doc_number=doc.unified_number,
        issue_date=doc.valid_from.strftime("%d.%m.%Y") if doc.valid_from else "",
        expiry_date=doc.valid_to.strftime("%d.%m.%Y") if doc.valid_to else "",
        full_name=doc.representative_fio,
        inn=doc.representative_inn,
        snils=doc.representative_snils,
        authority_codes=list(doc.authority_codes),
        authority_names=list(doc.authority_names),
        issuer_org_name=doc.principal_name,
        issuer_org_inn=doc.principal_inn,
        status=status_label,
        color=color,
        details=dict(doc.details),
    )


def dto_to_mchd(dto: MchdDTO) -> MchdDocument:
    """Преобразует DTO MchdDTO в доменную сущность MchdDocument.

    Args:
        dto: Объект передачи данных МЧД.

    Returns:
        MchdDocument: Экземпляр доменной модели МЧД.
    """
    valid_from = (
        datetime.strptime(dto.issue_date, "%d.%m.%Y")
        if dto.issue_date
        else datetime.min
    )
    valid_to = (
        datetime.strptime(dto.expiry_date, "%d.%m.%Y")
        if dto.expiry_date
        else datetime.max
    )

    status = MchdStatus.ACTIVE
    if dto.status == "Просрочен":
        status = MchdStatus.EXPIRED
    elif dto.status == "Отозвана":
        status = MchdStatus.REVOKED

    return MchdDocument(
        unified_number=dto.doc_number,
        internal_number=None,
        principal_inn=dto.issuer_org_inn,
        principal_name=dto.issuer_org_name,
        representative_inn=dto.inn,
        representative_fio=dto.full_name,
        representative_snils=dto.snils,
        valid_from=valid_from,
        valid_to=valid_to,
        status=status,
        authority_codes=list(dto.authority_codes),
        authority_names=list(dto.authority_names),
        source_path=dto.file_name,
        details={k: str(v) for k, v in dto.details.items()},
    )

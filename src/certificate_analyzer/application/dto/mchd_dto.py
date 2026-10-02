from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any

from certificate_analyzer.domain.enums.mchd_status import MchdStatus

NOT_FOUND = "Не найдено"

STATUS_VIEW: dict[MchdStatus, tuple[str, str]] = {
    MchdStatus.INVALID: ("Срок не наступил / неверные даты", "#e57373"),
    MchdStatus.EXPIRED: ("Просрочен", "#e57373"),
    MchdStatus.ACTIVE: ("Действует", "#9b59b6"),
    MchdStatus.REVOKED: ("Отозвана", "#e57373"),
}


@dataclass(slots=True)
class MchdDTO:
    file_name: str
    file_type: str
    doc_number: str
    issue_date: str
    expiry_date: str

    full_name: str
    inn: str
    snils: str

    authority_codes: list[str] = field(default_factory=list)
    authority_names: list[str] = field(default_factory=list)

    issuer_org_name: str = NOT_FOUND
    issuer_org_inn: str = NOT_FOUND

    status: str = ""
    color: str = ""

    details: dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, item: str) -> Any:
        if item != "details" and hasattr(self, item):
            return getattr(self, item)

        return self.details.get(item, NOT_FOUND)

    def get(self, item: str, default: Any = None) -> Any:
        if item != "details" and hasattr(self, item):
            return getattr(self, item)

        return self.details.get(item, default)

    def keys(self) -> list[str]:
        dto_keys = [
            item.name
            for item in fields(self)
            if item.name != "details"
        ]

        return dto_keys + list(self.details)

    def to_dict(self) -> dict[str, Any]:
        """Flatten DTO fields and details into a regular dictionary."""
        result = {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if item.name != "details"
        }

        result.update(self.details)
        return result


def _status_view(
    status: MchdStatus,
    valid_to: datetime,
) -> tuple[str, str]:
    """Convert domain status into text/color representation."""

    if status is MchdStatus.EXPIRING_SOON:
        days = max(
            0,
            (valid_to.date() - datetime.now().date()).days,
        )
        return f"Истекает ({days} дн.)", "#ffd54f"

    return STATUS_VIEW.get(
        status,
        ("Неизвестен", "#bdbdbd"),
    )


def _display(value: Any, default: str = NOT_FOUND) -> Any:
    """Replace empty values with UI-friendly placeholder."""
    return value if value not in (None, "") else default


def mchd_to_dict(model) -> MchdDTO:
    """Convert domain MchdDocument into desktop-interface DTO."""

    status, color = _status_view(
        model.status,
        model.valid_to,
    )

    raw_details = getattr(model, "details", None) or {}

    details = {
        key: _display(value)
        for key, value in raw_details.items()
    }

    details["verification_status"] = "NOT_CHECKED"
    details["Проверка подлинности"] = "Не проверена (подпись, доверие, отзыв)"

    return MchdDTO(
        file_name=str(
            getattr(model, "source_path", None) or "—"
        ),
        file_type="МЧД",
        doc_number=_display(model.unified_number),
        issue_date=model.valid_from.strftime("%d.%m.%Y"),
        expiry_date=model.valid_to.strftime("%d.%m.%Y"),
        full_name=_display(model.representative_fio),
        inn=_display(model.representative_inn),
        snils=_display(model.representative_snils),
        authority_codes=list(
            getattr(model, "authority_codes", None) or []
        ),
        authority_names=list(
            getattr(model, "authority_names", None) or []
        ),
        issuer_org_name=_display(model.principal_name),
        issuer_org_inn=_display(model.principal_inn),
        status=status,
        color=color,
        details=details,
    )

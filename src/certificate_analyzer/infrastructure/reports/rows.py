from datetime import datetime
from pathlib import Path

from certificate_analyzer.application.dto.certificate_dto import certificate_to_dict
from certificate_analyzer.application.dto.mchd_dto import mchd_to_dict

HEADERS = [
    "Тип",
    "Файл",
    "Действ. с",
    "Действ. до",
    "ФИО",
    "Номер",
    "Email / ИНН",
    "Кабинет / СНИЛС",
    "Подразделение / Доверитель",
    "Телефон / Полномочия",
    "Статус",
]


def model_rows(certificates, mchds):
    return [certificate_to_dict(c) for c in certificates] + [
        mchd_to_dict(m) for m in mchds
    ]


def values(row):
    return [
        row.get("file_type", "Сертификат"),
        row.get("original_name") or Path(row.get("file_name", "")).name,
        row.get("valid_from", row.get("issue_date", "")),
        row.get("valid_to", row.get("expiry_date", "")),
        row.get("subject_cn", row.get("full_name", "")),
        row.get("serial_number", row.get("doc_number", "")),
        row.get("email", row.get("inn", "")),
        row.get("office_number", row.get("snils", "")),
        row.get("department", row.get("issuer_org_name", "")),
        row.get("phone", ", ".join(row.get("authority_codes", []))),
        row.get("status", ""),
    ]


def output_path(folder, path, extension):
    target = (
        Path(path)
        if path
        else Path(folder or ".")
        / f"report_{datetime.now():%Y%m%d_%H%M%S_%f}.{extension}"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    return str(target)

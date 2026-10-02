"""Allow only supported document files to reach OS associations."""
from pathlib import Path

ALLOWED_EXTENSIONS = frozenset({".cer", ".crt", ".der", ".pem", ".xml", ".pdf", ".xlsx", ".docx", ".txt"})


def validate_open_file(path: str | Path) -> Path:
    original = Path(path)
    p = original.resolve(strict=True)
    if not p.is_file():
        raise ValueError("Открывать можно только обычные файлы")
    if original.suffix.lower() not in ALLOWED_EXTENSIONS or p.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Открытие этого типа файлов запрещено")
    return p

from pathlib import Path


def scan_files(
    folder: str | Path,
    extensions: tuple[str, ...] = (".cer", ".crt", ".der", ".pem"),
) -> list[Path]:
    """Рекурсивно найти файлы сертификатов в каталоге."""

    path = Path(folder).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Папка не найдена: {path}")

    if not path.is_dir():
        raise NotADirectoryError(f"Это не папка: {path}")

    normalized_extensions = {
        ext.lower() if ext.startswith(".") else f".{ext.lower()}"
        for ext in extensions
    }

    return sorted(
        p
        for p in path.rglob("*")
        if p.is_file()
        and p.suffix.lower() in normalized_extensions
    )

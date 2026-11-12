"""Управляемое хранилище файлов сертификатов на диске. В базе данных хранятся только метаданные."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile


class CertificateStorage:
    """Управление хранилищем бинарных файлов сертификатов в формате DER."""

    def __init__(self, folder: str | Path) -> None:
        """Инициализирует каталог хранилища сертификатов.

        Args:
            folder: Путь к целевой папке для сохранения файлов.
        """
        self.folder: Path = Path(folder).expanduser().resolve()

    def put(self, fingerprint: str, der: bytes) -> Path:
        """Атомарно сохраняет сертификат в формате DER под именем <SHA256>.cer.

        Args:
            fingerprint: Отпечаток SHA-256 в верхнем регистре (64 шестнадцатеричных символа).
            der: Бинарное содержимое сертификата в кодировке DER.

        Returns:
            Path: Путь к сохранённому файлу сертификата.

        Raises:
            ValueError: Если отпечаток некорректен или обнаружен конфликт содержимого файла.
        """
        if len(fingerprint) != 64 or any(
            c not in "0123456789ABCDEF" for c in fingerprint
        ):
            raise ValueError("Некорректный SHA-256")
        self.folder.mkdir(parents=True, exist_ok=True)
        target = self.folder / (fingerprint + ".cer")
        if target.exists():
            if target.read_bytes() != der:
                raise ValueError(f"Файл хранилища повреждён: {target}")
            return target
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.folder, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(der)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, target)
            except FileExistsError:
                if target.read_bytes() != der:
                    raise ValueError(f"Конфликт файла хранилища: {target}")
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
        return target

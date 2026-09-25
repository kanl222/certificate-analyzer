"""Managed certificate directory. The database contains metadata only."""

import os
import tempfile
from pathlib import Path


class CertificateStorage:
    def __init__(self, folder):
        self.folder = Path(folder).expanduser().resolve()

    def put(self, fingerprint, der):
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
        temporary = None
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

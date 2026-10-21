"""Системная блокировка владельца БД, независимая от выбранного порта IPC."""

import errno
import os
from pathlib import Path


class WriterLock:
    """Удерживает файл до закрытия сервера; ОС освобождает его и после аварии."""

    def __init__(self, path):
        target = Path(str(Path(path).resolve()) + ".ipc-lock")
        target.parent.mkdir(parents=True, exist_ok=True)
        stream = target.open("a+b")
        try:
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise OSError(errno.EADDRINUSE, "База уже обслуживается другим фоновым процессом") from exc
        self._stream = stream

    def close(self):
        """Закрывает дескриптор, сохраняя файл для следующего владельца."""
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.close()

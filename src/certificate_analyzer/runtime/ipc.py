"""Модель единого пишущего процесса (Single Writer) и локальный транспорт JSON."""

import errno
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import socketserver
import threading
import time

from certificate_analyzer.exceptions import CertificateAnalyzerError
from certificate_analyzer.runtime.write_api import COMMANDS, decode, encode
from certificate_analyzer.runtime.writer_lock import WriterLock

MAX_MESSAGE = 16 * 1024 * 1024
logger = logging.getLogger(__name__)


class WriterUnavailable(CertificateAnalyzerError, RuntimeError):
    pass


class WriteCommandError(CertificateAnalyzerError, ValueError):
    pass


def _default_endpoint(path):
    canonical = os.path.normcase(str(Path(path).resolve()))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return ("127.0.0.1", 20000 + int(digest[:8], 16) % 30000)


def port_path(path):
    """Возвращает путь к опубликованному порту текущего владельца базы."""
    return Path(str(Path(path).resolve()) + ".ipc-port")


def endpoint(path):
    """Использует опубликованный порт, сохраняя совместимость с прежним демоном."""
    try:
        with port_path(path).open(encoding="ascii") as stream:
            port = int(stream.read(16).strip())
        if 1 <= port <= 65535:
            return ("127.0.0.1", port)
    except (OSError, ValueError, UnicodeError):
        pass
    return _default_endpoint(path)


def _listening(address):
    """Не позволяет обходить действующий старый демон выбором другого порта."""
    try:
        with socket.create_connection(address, timeout=0.25):
            return True
    except OSError:
        return False


def token_path(path):
    return Path(str(Path(path).resolve()) + ".ipc-token")


def receive(stream):
    raw = stream.readline(MAX_MESSAGE + 1)
    if not raw or len(raw) > MAX_MESSAGE or not raw.endswith(b"\n"):
        raise ValueError("Некорректный или слишком большой IPC-пакет")
    return json.loads(raw)


def send(stream, value):
    raw = json.dumps(value, ensure_ascii=False).encode() + b"\n"
    if len(raw) > MAX_MESSAGE:
        raise ValueError("Превышен размер IPC-пакета; уменьшите размер импорта")
    stream.write(raw)
    stream.flush()


class WriteClient:
    def __init__(self, path, timeout=120):
        self.path, self.timeout = Path(path), timeout

    def call(self, service="", method="ping", args=(), kwargs=None):
        try:
            token = token_path(self.path).read_text(encoding="ascii")
            with socket.create_connection(endpoint(self.path), timeout=self.timeout) as connection:
                connection.settimeout(self.timeout)
                with connection.makefile("rwb") as stream:
                    send(stream, {"version": 1, "token": token, "service": service,
                                  "method": method, "args": encode(args), "kwargs": encode(kwargs or {})})
                    response = receive(stream)
        except (OSError, ValueError) as exc:
            raise WriterUnavailable(
                "Фоновый процесс недоступен или не ответил. Запустите worker. "
                "Если связь прервалась после отправки, проверьте данные перед повтором: "
                "операция могла завершиться."
            ) from exc
        if not response.get("ok"):
            raise WriteCommandError(response.get("error", "Ошибка фонового процесса"))
        return decode(response.get("result")), response.get("errors", {})


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(5)
        try:
            request = receive(self.rfile)
            if request.get("version") != 1 or not hmac.compare_digest(str(request.get("token", "")), self.server.token):
                raise ValueError("Отказано в доступе к локальному API")
            if request["method"] in ("ping", "stop") and not request["service"]:
                if request["method"] == "stop":
                    logger.info("Принята команда остановки через IPC")
                    self.server.stop_requested.set()
                result, errors = {"pid": os.getpid(), "database": str(self.server.app.database.path)}, {}
                response = {"ok": True, "result": encode(result), "errors": errors}
            else:
                with self.server.command_lock:
                    if self.server.stop_requested.is_set():
                        raise ValueError("Фоновый процесс завершает работу")
                    name, method = request["service"], request["method"]
                    if method not in COMMANDS.get(name, set()):
                        raise ValueError("Неизвестная команда записи")
                    service = getattr(self.server.app, name)
                    started = time.monotonic()
                    logger.info("Выполнение команды IPC: %s.%s", name, method)
                    result = getattr(service, method)(*decode(request["args"]), **decode(request["kwargs"]))
                    errors = getattr(service, "errors", {})
                    logger.info("Команда IPC завершена: %s.%s, ошибок=%s, длительность=%.2f с",
                                name, method, len(errors), time.monotonic() - started)
                    # Freeze the reply before another command can mutate service state.
                    response = {"ok": True, "result": encode(result), "errors": dict(errors)}
        except Exception as exc:
            logger.exception("Ошибка команды IPC")
            response = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}
        try:
            send(self.wfile, response)
        except (OSError, ValueError):
            logger.exception("Не удалось вернуть результат IPC")


class WriterServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = False
    daemon_threads = False
    block_on_close = True
    request_queue_size = 32

    def __init__(self, path):
        # Блокировка берётся до открытия SQLite и не зависит от доступности порта.
        self.path = Path(path).resolve()
        self._closed = False
        self._port_published = False
        self._writer_lock = WriterLock(self.path)
        try:
            address = _default_endpoint(self.path)
            super().__init__(address, _Handler, bind_and_activate=False)
            if os.name == "nt":
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                self.server_bind()
            except OSError as exc:
                denied = exc.errno in (errno.EACCES, errno.EPERM) or getattr(exc, "winerror", None) == 10013
                if not denied or _listening(address):
                    raise
                self.server_address = (address[0], 0)
                self.server_bind()
            self.server_activate()
            # Старая информация после аварии не должна выглядеть как готовый API.
            token_path(self.path).unlink(missing_ok=True)
            port_path(self.path).unlink(missing_ok=True)
        except Exception:
            self.server_close()
            raise
        self.command_lock = threading.RLock()
        self.stop_requested = threading.Event()
        self.token = secrets.token_hex(32)

    def attach(self, app):
        self.app = app
        self._publish_private(port_path(self.path), str(self.server_address[1]))
        self._port_published = True
        self._publish_private(token_path(self.path), self.token)

    @staticmethod
    def _publish_private(destination, value):
        """Атомарно публикует данные IPC с доступом только текущему пользователю."""
        target = destination.with_name(destination.name + "." + str(os.getpid()))
        try:
            target.touch(mode=0o600, exist_ok=True)
            WriterServer._restrict_access(target)
            target.write_text(value, encoding="ascii")
            target.replace(destination)
        finally:
            target.unlink(missing_ok=True)

    @staticmethod
    def _restrict_access(target):
        """Выставляет права до записи токена или публикации порта."""
        # Ограничение прав доступа перед записью секрета, в том числе для Windows.
        if os.name == "nt":
            import win32api
            import win32con
            import win32security
            process_token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
            try:
                sid = win32security.GetTokenInformation(process_token, win32security.TokenUser)[0]
            finally:
                process_token.Close()
            acl = win32security.ACL()
            acl.AddAccessAllowedAce(win32security.ACL_REVISION, win32con.GENERIC_ALL, sid)
            win32security.SetNamedSecurityInfo(str(target), win32security.SE_FILE_OBJECT,
                win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
                None, None, acl, None)
        else:
            target.chmod(0o600)

    def server_close(self):
        if self._closed:
            return
        self._closed = True
        try:
            if hasattr(self, "socket"):
                super().server_close()
            if hasattr(self, "token"):
                self._remove_published(token_path(self.path), self.token)
            if self._port_published:
                self._remove_published(port_path(self.path), str(self.server_address[1]))
        finally:
            self._writer_lock.close()

    @staticmethod
    def _remove_published(path, expected):
        """Удаляет только принадлежащую этому экземпляру информацию IPC."""
        try:
            if path.read_text(encoding="ascii") == expected:
                path.unlink()
        except (OSError, UnicodeError):
            pass

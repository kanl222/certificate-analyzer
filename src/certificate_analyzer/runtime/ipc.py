"""Single writer ownership and bounded loopback JSON transport."""

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

MAX_MESSAGE = 16 * 1024 * 1024
logger = logging.getLogger(__name__)


class WriterUnavailable(CertificateAnalyzerError, RuntimeError):
    pass


class WriteCommandError(CertificateAnalyzerError, ValueError):
    pass


def endpoint(path):
    canonical = os.path.normcase(str(Path(path).resolve()))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return ("127.0.0.1", 20000 + int(digest[:8], 16) % 30000)


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
            with socket.create_connection(endpoint(self.path), timeout=2) as connection:
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
            with self.server.command_lock:
                if request["method"] in ("ping", "stop") and not request["service"]:
                    if request["method"] == "stop":
                        logger.info("Принята команда остановки через IPC")
                        self.server.stop_requested.set()
                    result, errors = {"pid": os.getpid(), "database": str(self.server.app.database.path)}, {}
                else:
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
                response = {"ok": True, "result": encode(result), "errors": errors}
        except Exception as exc:
            logger.exception("Ошибка команды IPC")
            response = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}
        try:
            send(self.wfile, response)
        except (OSError, ValueError):
            logger.exception("Не удалось вернуть результат IPC")


class WriterServer(socketserver.TCPServer):
    allow_reuse_address = False

    def __init__(self, path):
        # Bind before opening SQLite: a second worker must never migrate/write.
        super().__init__(endpoint(path), _Handler, bind_and_activate=False)
        try:
            if os.name == "nt":
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            self.server_bind()
            self.server_activate()
        except Exception:
            self.server_close()
            raise
        self.command_lock = threading.RLock()
        self.stop_requested = threading.Event()
        self.token = secrets.token_hex(32)
        self.path = Path(path)

    def attach(self, app):
        self.app = app
        target = token_path(self.path).with_suffix(".ipc-token." + str(os.getpid()))
        # Restrict access before writing the secret, including on Windows.
        target.touch(mode=0o600, exist_ok=True)
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
        target.write_text(self.token, encoding="ascii")
        target.replace(token_path(self.path))

    def server_close(self):
        super().server_close()
        if hasattr(self, "token"):
            target = token_path(self.path)
            try:
                if target.read_text(encoding="ascii") == self.token:
                    target.unlink()
            except OSError:
                pass

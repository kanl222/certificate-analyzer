"""Модель единого пишущего процесса (Single Writer) и локальный транспорт JSON."""

from __future__ import annotations

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
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from certificate_analyzer.exceptions import CertificateAnalyzerError
from certificate_analyzer.runtime.operations import OperationJournal
from certificate_analyzer.runtime.write_api import COMMANDS, READ_COMMANDS, decode, encode
from certificate_analyzer.runtime.writer_lock import WriterLock

if TYPE_CHECKING:
    from certificate_analyzer.bootstrap import ApplicationContainer

MAX_MESSAGE: int = 16 * 1024 * 1024
logger: logging.Logger = logging.getLogger(__name__)


class WriterUnavailable(CertificateAnalyzerError, RuntimeError):
    """Исключение при недоступности фонового пишущего процесса."""

    def __init__(self, message: str, operation_id: str | None = None) -> None:
        super().__init__(message)
        self.operation_id: str | None = operation_id


class WriteCommandError(CertificateAnalyzerError, ValueError):
    """Исключение при ошибке выполнения команды внутри фонового процесса."""

    pass


def _default_endpoint(path: str | Path) -> tuple[str, int]:
    """Вычисляет детерминированный TCP-адрес по умолчанию на основе пути к БД."""
    canonical: str = os.path.normcase(str(Path(path).resolve()))
    digest: str = hashlib.sha256(canonical.encode()).hexdigest()
    return ("127.0.0.1", 20000 + int(digest[:8], 16) % 30000)


def port_path(path: str | Path) -> Path:
    """Возвращает путь к файлу опубликованного порта текущего владельца базы."""
    return Path(str(Path(path).resolve()) + ".ipc-port")


def endpoint(path: str | Path) -> tuple[str, int]:
    """Определяет актуальный адрес демона: использует опубликованный порт или порт по умолчанию."""
    try:
        with port_path(path).open(encoding="ascii") as stream:
            port: int = int(stream.read(16).strip())
        if 1 <= port <= 65535:
            return ("127.0.0.1", port)
    except (OSError, ValueError, UnicodeError):
        pass
    return _default_endpoint(path)


def _listening(address: tuple[str, int]) -> bool:
    """Проверяет, слушает ли уже процесс указанный сетевой адрес."""
    try:
        with socket.create_connection(address, timeout=0.25):
            return True
    except OSError:
        return False


def token_path(path: str | Path) -> Path:
    """Возвращает путь к файлу токена авторизации IPC."""
    return Path(str(Path(path).resolve()) + ".ipc-token")


def receive(stream: Any) -> dict[str, Any]:
    """Считывает и декодирует один JSON-пакет из потока сокета."""
    raw: bytes = stream.readline(MAX_MESSAGE + 1)
    if not raw or len(raw) > MAX_MESSAGE or not raw.endswith(b"\n"):
        raise ValueError("Некорректный или слишком большой IPC-пакет")
    return json.loads(raw)


def send(stream: Any, value: dict[str, Any]) -> None:
    """Кодирует и отправляет JSON-пакет с завершающим символом перевода строки."""
    raw: bytes = json.dumps(value, ensure_ascii=False).encode() + b"\n"
    if len(raw) > MAX_MESSAGE:
        raise ValueError("Превышен размер IPC-пакета; уменьшите размер операции")
    stream.write(raw)
    stream.flush()


class WriteClient:
    """Клиент для взаимодействия с единым пишущим демоном базы данных."""

    def __init__(self, path: str | Path, timeout: float = 120.0) -> None:
        self.path: Path = Path(path)
        self.timeout: float = timeout

    def _exchange(
        self,
        service: str,
        method: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any] | None,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        """Отправляет команду на сервер и принимает ответ с поддержкой ретраев подключения."""
        connection: socket.socket | None = None
        token: str = ""
        max_attempts: int = 3
        last_exc: Exception | None = None

        for attempt in range(max_attempts):
            try:
                token = token_path(self.path).read_text(encoding="ascii")
                connection = socket.create_connection(endpoint(self.path), timeout=self.timeout)
                break
            except (OSError, UnicodeError) as exc:
                last_exc = exc
                if attempt < max_attempts - 1:
                    # Экспоненциальный бэкофф с джиттером для временных сетевых задержек
                    time.sleep(0.05 * (2 ** attempt) + (secrets.randbelow(20) / 1000))
                else:
                    raise WriterUnavailable(
                        "Фоновый процесс недоступен или не ответил. Запустите worker. "
                        "Если связь прервалась после отправки, проверьте данные перед повтором: "
                        "операция могла завершиться."
                    ) from last_exc

        assert connection is not None
        try:
            with connection:
                connection.settimeout(self.timeout)
                with connection.makefile("rwb") as stream:
                    send(stream, {
                        "version": 1,
                        "token": token,
                        "service": service,
                        "method": method,
                        "args": encode(args),
                        "kwargs": encode(kwargs or {}),
                        "operation_id": operation_id,
                    })
                    response: dict[str, Any] = receive(stream)
        except (OSError, ValueError) as exc:
            raise WriterUnavailable(
                "Фоновый процесс недоступен или не ответил. Запустите worker. "
                "Если связь прервалась после отправки, проверьте данные перед повтором: "
                "операция могла завершиться."
            ) from exc
        return response

    def ping(self) -> dict[str, Any]:
        """Быстрая проверка доступности и здоровья пишущего процесса."""
        result, _ = self.call(method="ping")
        return result

    def operation_status(self, operation_id: str) -> dict[str, Any]:
        """Запрашивает статус ранее отправленной операции по её идентификатору."""
        res: dict[str, Any]
        res, _ = self.call(method="operation_status", args=(operation_id,))
        return res

    def call(
        self,
        service: str = "",
        method: str = "ping",
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        *,
        operation_id: str | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        """Выполняет вызов удалённого метода через IPC с регистрацией идемпотентного ID."""
        tracked: bool = bool(service) and method not in READ_COMMANDS.get(service, set())
        op_id: str | None = (operation_id or str(uuid4())) if tracked else None
        try:
            response: dict[str, Any] = self._exchange(service, method, args, kwargs, op_id)
        except WriterUnavailable as exc:
            if not op_id:
                raise
            try:
                status: dict[str, Any] = self.operation_status(op_id)
            except (WriterUnavailable, WriteCommandError):
                status = {"state": "unknown"}
            if status.get("state") == "completed":
                response = status["response"]
            else:
                labels: dict[str, str] = {
                    "running": "Операция ещё выполняется.",
                    "not_found": "Операция пока не найдена в журнале.",
                }
                raise WriterUnavailable(
                    "Фоновый процесс недоступен или не вернул результат. "
                    + labels.get(status.get("state", ""), "Результат операции неизвестен.")
                    + f"\nИдентификатор: {op_id}\nПроверьте результат через меню «Служба → Результат операции». "
                    "Не повторяйте изменение до проверки данных.",
                    op_id,
                ) from exc
        if not response.get("ok"):
            raise WriteCommandError(response.get("error", "Ошибка фонового процесса"))
        return decode(response.get("result")), response.get("errors", {})


class _Handler(socketserver.StreamRequestHandler):
    """Обработчик входящих сетевых запросов IPC."""

    server: WriterServer

    def handle(self) -> None:
        self.connection.settimeout(5)
        response: dict[str, Any]
        try:
            request: dict[str, Any] = receive(self.rfile)
            if request.get("version") != 1 or not hmac.compare_digest(str(request.get("token", "")), self.server.token):
                raise ValueError("Отказано в доступе к локальному API")
            if request["method"] == "operation_status" and not request["service"]:
                identifier: str
                identifier, = decode(request["args"])
                response = {"ok": True, "result": self.server.operations.status(identifier), "errors": {}}
            elif request["method"] in ("ping", "stop") and not request["service"]:
                if request["method"] == "stop":
                    logger.info("Принята команда остановки через IPC")
                    self.server.stop_requested.set()
                result: dict[str, Any] = {"pid": os.getpid(), "database": str(self.server.app.database.path)}
                errors: dict[str, Any] = {}
                response = {"ok": True, "result": encode(result), "errors": errors}
            else:
                response = self.execute(request)
        except Exception as exc:
            logger.exception("Ошибка команды IPC")
            response = {"ok": False, "error": str(exc), "error_type": type(exc).__name__}
        try:
            send(self.wfile, response)
        except (OSError, ValueError):
            logger.exception("Не удалось вернуть результат IPC")

    def execute(self, request: dict[str, Any]) -> dict[str, Any]:
        """Сериализует операции изменения данных и сохраняет ответ перед отправкой."""
        with self.server.command_lock:
            if self.server.stop_requested.is_set():
                raise ValueError("Фоновый процесс завершает работу")
            name: str = request["service"]
            method: str = request["method"]
            if method not in COMMANDS.get(name, set()):
                raise ValueError("Неизвестная команда")
            identifier: str | None = request.get("operation_id")
            response: dict[str, Any] | None = (
                self.server.operations.begin(identifier, request) if identifier else None
            )
            if response is None:
                response = self.invoke(request)
                if identifier:
                    self.server.operations.finish(identifier, response)
            return response

    def invoke(self, request: dict[str, Any]) -> dict[str, Any]:
        """Вызывает соответствующий метод сервиса приложения."""
        name: str = request["service"]
        method: str = request["method"]
        try:
            service: Any = getattr(self.server.app, name)
            started: float = time.monotonic()
            logger.info("Выполнение команды IPC: %s.%s", name, method)
            result: Any = getattr(service, method)(*decode(request["args"]), **decode(request["kwargs"]))
            errors: dict[str, Any] = getattr(service, "errors", {})
            logger.info(
                "Команда IPC завершена: %s.%s, ошибок=%s, длительность=%.2f с",
                name, method, len(errors), time.monotonic() - started,
            )
            return {"ok": True, "result": encode(result), "errors": encode(dict(errors))}
        except Exception as exc:
            logger.exception("Ошибка выполнения команды IPC")
            return {"ok": False, "error": str(exc), "error_type": type(exc).__name__}


class WriterServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """TCP-сервер единого пишущего процесса с проверкой токена и блокировкой."""

    # Разрешить немедленный перезапуск после TIME_WAIT; SO_REUSEADDR не допускает второго слушателя без SO_REUSEPORT.
    allow_reuse_address: bool = os.name != "nt"
    daemon_threads: bool = False
    block_on_close: bool = True
    request_queue_size: int = 32

    def __init__(self, path: str | Path) -> None:
        # Блокировка берётся до открытия SQLite и не зависит от доступности порта.
        self.path: Path = Path(path).resolve()
        self._closed: bool = False
        self._port_published: bool = False
        self._writer_lock: WriterLock = WriterLock(self.path)
        try:
            address: tuple[str, int] = _default_endpoint(self.path)
            super().__init__(address, _Handler, bind_and_activate=False)
            if os.name == "nt":
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            try:
                self.server_bind()
            except OSError as exc:
                denied: bool = exc.errno in (errno.EACCES, errno.EPERM) or getattr(exc, "winerror", None) == 10013
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
        self.command_lock: threading.RLock = threading.RLock()
        self.stop_requested: threading.Event = threading.Event()
        self.token: str = secrets.token_hex(32)
        self.app: ApplicationContainer
        self.operations: OperationJournal

    def attach(self, app: ApplicationContainer) -> None:
        """Привязывает контейнер приложения и публикует порт и токен."""
        self.app = app
        journal_path: Path = Path(str(self.path) + ".operations.sqlite")
        journal_path.touch(mode=0o600, exist_ok=True)
        self._restrict_access(journal_path)
        self.operations = OperationJournal(journal_path)
        self._publish_private(port_path(self.path), str(self.server_address[1]))
        self._port_published = True
        self._publish_private(token_path(self.path), self.token)

    @staticmethod
    def _publish_private(destination: Path, value: str) -> None:
        """Атомарно публикует данные IPC с доступом только текущему пользователю."""
        target: Path = destination.with_name(destination.name + "." + str(os.getpid()))
        try:
            target.touch(mode=0o600, exist_ok=True)
            WriterServer._restrict_access(target)
            target.write_text(value, encoding="ascii")
            target.replace(destination)
        finally:
            target.unlink(missing_ok=True)

    @staticmethod
    def _restrict_access(target: Path) -> None:
        """Выставляет права доступа до записи токена или публикации порта."""
        # Ограничение прав доступа перед записью секрета, в том числе для Windows.
        if os.name == "nt":
            import win32api
            import win32con
            import win32security
            process_token: Any = win32security.OpenProcessToken(win32api.GetCurrentProcess(), win32con.TOKEN_QUERY)
            try:
                sid: Any = win32security.GetTokenInformation(process_token, win32security.TokenUser)[0]
            finally:
                process_token.Close()
            acl: Any = win32security.ACL()
            acl.AddAccessAllowedAce(win32security.ACL_REVISION, win32con.GENERIC_ALL, sid)
            win32security.SetNamedSecurityInfo(
                str(target),
                win32security.SE_FILE_OBJECT,
                win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
                None,
                None,
                acl,
                None,
            )
        else:
            target.chmod(0o600)

    def server_close(self) -> None:
        """Останавливает сервер и удаляет опубликованные файлы порта и токена."""
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
    def _remove_published(path: Path, expected: str) -> None:
        """Удаляет только принадлежащую этому экземпляру информацию IPC."""
        try:
            if path.read_text(encoding="ascii") == expected:
                path.unlink()
        except (OSError, UnicodeError):
            pass

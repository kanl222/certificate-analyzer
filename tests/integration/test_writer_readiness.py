from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import threading
import errno
import socket

import pytest

from certificate_analyzer.runtime.ipc import WriteClient, WriterServer


def test_denied_port_uses_fallback_with_single_writer_lock(tmp_path, monkeypatch):
    from certificate_analyzer.runtime import ipc
    path = tmp_path / "reserved.db"
    bind = WriterServer.server_bind
    attempts = []

    def denied_first_port(server):
        attempts.append(server.server_address[1])
        if len(attempts) == 1:
            raise PermissionError(errno.EACCES, "Reserved port")
        return bind(server)

    monkeypatch.setattr(WriterServer, "server_bind", denied_first_port)
    server = WriterServer(path)
    thread = None
    try:
        assert attempts == [ipc._default_endpoint(path)[1], 0]
        server.attach(SimpleNamespace(database=SimpleNamespace(path=path)))
        assert ipc.endpoint(path) == server.server_address
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        assert WriteClient(path, timeout=2).call()[0]["database"] == str(path)
        with pytest.raises(OSError):
            WriterServer(path)
        assert WriteClient(path, timeout=2).call()[0]["database"] == str(path)
    finally:
        if thread is not None:
            server.shutdown()
            thread.join(timeout=5)
        server.server_close()
    assert not ipc.port_path(path).exists()
    assert not ipc.token_path(path).exists()
    # The persistent lock file is reusable after the owner exits.
    with WriterServer(path):
        pass


def test_denied_port_with_existing_listener_does_not_start_second_writer(tmp_path, monkeypatch):
    from certificate_analyzer.runtime import ipc
    path = tmp_path / "legacy.db"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        address = listener.getsockname()
        monkeypatch.setattr(ipc, "_default_endpoint", lambda _: address)
        attempts = []

        def denied_bind(server):
            attempts.append(server.server_address)
            raise PermissionError(errno.EACCES, "Exclusive listener")

        monkeypatch.setattr(WriterServer, "server_bind", denied_bind)
        with pytest.raises(PermissionError):
            WriterServer(path)
        assert attempts == [address]
        assert not ipc.token_path(path).exists()


def test_ping_responds_while_writer_is_busy(tmp_path):
    path = tmp_path / "busy.db"
    started = threading.Event()
    release = threading.Event()

    def save_employee(value):
        started.set()
        assert release.wait(5)
        return value

    server = WriterServer(path)
    server.attach(SimpleNamespace(database=SimpleNamespace(path=path), employees=SimpleNamespace(save_employee=save_employee)))
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            write = pool.submit(WriteClient(path, timeout=5).call, "employees", "save_employee", ("employee",))
            assert started.wait(2)
            try:
                info, _ = WriteClient(path, timeout=0.5).call()
                assert info["database"] == str(path)
                assert not write.done()
            finally:
                release.set()
            assert write.result(timeout=5)[0] == "employee"
    finally:
        release.set()
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

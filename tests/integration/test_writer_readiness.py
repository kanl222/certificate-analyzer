from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import threading

from certificate_analyzer.runtime.ipc import WriteClient, WriterServer


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

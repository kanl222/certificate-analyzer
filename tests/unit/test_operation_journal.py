from uuid import uuid4

import pytest

from certificate_analyzer.runtime.operations import OperationJournal
from certificate_analyzer.runtime.ipc import WriteClient, WriterUnavailable


def test_receipts_survive_restart_and_reject_changed_arguments(tmp_path):
    path = tmp_path / "operations.sqlite"
    journal = OperationJournal(path)
    identifier = str(uuid4())
    request = {"service": "archive", "method": "backup", "args": ["copy.cat", "private-password"], "kwargs": {}}
    response = {"ok": True, "result": {"path": "copy.cat"}, "errors": {}}
    assert journal.begin(identifier, request) is None
    assert journal.status(identifier) == {"state": "running"}
    journal.finish(identifier, response)
    restarted = OperationJournal(path)
    assert restarted.begin(identifier, request) == response
    assert restarted.status(identifier) == {"state": "completed", "response": response}
    with pytest.raises(ValueError, match="другими параметрами"):
        restarted.begin(identifier, {**request, "args": ["different.cat", "private-password"]})
    assert b"private-password" not in path.read_bytes()


def test_interrupted_operation_is_never_replayed(tmp_path):
    path = tmp_path / "operations.sqlite"
    identifier = str(uuid4())
    request = {"service": "employees", "method": "save_employee", "args": [], "kwargs": {}}
    journal = OperationJournal(path)
    journal.begin(identifier, request)
    restarted = OperationJournal(path)
    assert restarted.status(identifier) == {"state": "unknown"}
    with pytest.raises(ValueError, match="повторное выполнение заблокировано"):
        restarted.begin(identifier, request)
    assert restarted.status(str(uuid4())) == {"state": "not_found"}


@pytest.mark.parametrize("state", ["running", "unknown", "not_found"])
def test_client_queries_status_without_repeating_command(tmp_path, monkeypatch, state):
    client = WriteClient(tmp_path / "db")
    calls = []

    def exchange(service, method, args, kwargs, operation_id=None):
        calls.append((service, method, operation_id))
        if service:
            raise WriterUnavailable("Connection lost")
        return {"ok": True, "result": {"state": state}, "errors": {}}

    monkeypatch.setattr(client, "_exchange", exchange)
    with pytest.raises(WriterUnavailable) as caught:
        client.call("employees", "save_employee")
    assert caught.value.operation_id == calls[0][2]
    assert [method for _, method, _ in calls] == ["save_employee", "operation_status"]

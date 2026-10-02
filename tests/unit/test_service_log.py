from certificate_analyzer.presentation.gui.views.service_log_view import read_log_tail


def test_missing_log_is_explained(tmp_path):
    assert "Журнал пока не создан" in read_log_tail(tmp_path / "application.log")


def test_log_tail_is_bounded_and_keeps_complete_utf8_lines(tmp_path):
    path = tmp_path / "application.log"
    path.write_text("Старая строка\n" * 100 + "Демон остановлен\n", encoding="utf-8")
    tail = read_log_tail(path, max_bytes=60)
    assert "Демон остановлен" in tail
    assert "�" not in tail
    assert len(tail.encode("utf-8")) <= 60

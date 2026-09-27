"""Тесты планировщика фоновых задач Scheduler."""

import time
import pytest

from certificate_analyzer.runtime.scheduler import Scheduler


def test_scheduler_validation():
    """Проверяет валидацию параметров инициализации планировщика."""
    with pytest.raises(ValueError, match="Интервал планировщика должен быть положительным"):
        Scheduler(0, lambda: None)

    with pytest.raises(ValueError, match="Интервал планировщика должен быть положительным"):
        Scheduler(-5, lambda: None)


def test_scheduler_execution_and_stop():
    """Проверяет запуск, выполнение задачи и остановку планировщика."""
    counter = {"count": 0}

    def increment():
        counter["count"] += 1

    scheduler = Scheduler(interval_seconds=0.05, task=increment, name="TestSched")
    assert not scheduler.is_running

    scheduler.start()
    assert scheduler.is_running

    # Повторный старт не должен ломать состояние
    scheduler.start()

    time.sleep(0.18)
    scheduler.stop()

    assert not scheduler.is_running
    assert counter["count"] >= 2


def test_scheduler_context_manager():
    """Проверяет работу планировщика как контекстного менеджера."""
    counter = {"count": 0}

    def increment():
        counter["count"] += 1

    with Scheduler(interval_seconds=0.05, task=increment) as sched:
        assert sched.is_running
        time.sleep(0.12)

    assert not sched.is_running
    assert counter["count"] >= 1

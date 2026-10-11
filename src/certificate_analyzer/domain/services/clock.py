"""Метки времени UTC, используемые для значений по умолчанию в домене и адаптерах сохранения."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)

"""Доменная модель уведомления."""


from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class Notification:
    """Доменная модель уведомления."""

    title: str
    message: str
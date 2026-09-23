"""Доменная модель организации."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class Organization:
    """Доменная модель организации."""

"""Модуль интерфейса командной строки (CLI)."""

from certificate_analyzer.presentation.cli.commands import (
    build_parser,
    dispatch_command,
    query_from_args,
)
from certificate_analyzer.presentation.cli.formatter import (
    format_json,
    print_error,
    print_json,
)

__all__ = [
    "build_parser",
    "dispatch_command",
    "format_json",
    "print_error",
    "print_json",
    "query_from_args",
]

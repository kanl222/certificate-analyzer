"""Форматирование и вывод данных командной строки (CLI)."""

import json
import sys
from typing import Any


def format_json(value: Any, indent: int = 2) -> str:
    """Сериализует переданное значение в читаемую JSON-строку.

    Args:
        value: Данные для сериализации (словарь, список, примитивные типы).
        indent: Количество пробелов для отступа в JSON.

    Returns:
        str: JSON-строка в кодировке UTF-8 без экранирования кириллицы.
    """
    return json.dumps(value, ensure_ascii=False, indent=indent, default=str)


def print_json(value: Any, file=None) -> None:
    """Выводит данные в формате JSON в указанный поток (по умолчанию sys.stdout).

    Args:
        value: Данные для вывода.
        file: Целевой файловый поток (по умолчанию stdout).
    """
    target = file if file is not None else sys.stdout
    print(format_json(value), file=target)


def print_error(message: str, file=None) -> None:
    """Выводит сообщение об ошибке в поток ошибок (по умолчанию sys.stderr).

    Args:
        message: Текст сообщения об ошибке.
        file: Целевой файловый поток (по умолчанию stderr).
    """
    target = file if file is not None else sys.stderr
    print(f"Ошибка: {message}", file=target)

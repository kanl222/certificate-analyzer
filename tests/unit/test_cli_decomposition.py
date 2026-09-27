"""Тесты декомпозиции CLI (парсер, команды и форматирование)."""

import json
from pathlib import Path

from certificate_analyzer.presentation.cli.commands import build_parser, query_from_args
from certificate_analyzer.presentation.cli.formatter import format_json, print_error, print_json


def test_format_json_and_print(capsys):
    """Проверяет форматирование JSON и корректный вывод."""
    data = {"status": "OK", "name": "Иванов"}
    formatted = format_json(data)
    assert "Иванов" in formatted
    assert json.loads(formatted) == data

    print_json(data)
    out = capsys.readouterr().out
    assert "Иванов" in out
    assert json.loads(out) == data


def test_print_error(capsys):
    """Проверяет вывод ошибок в поток stderr."""
    print_error("Тестовая ошибка")
    captured = capsys.readouterr()
    assert "Ошибка: Тестовая ошибка" in captured.err


def test_build_parser_options():
    """Проверяет корректность разбора параметров командной строки."""
    parser = build_parser()
    args = parser.parse_args(["list", "--search", "Петров", "--limit", "50", "--offset", "10"])
    assert args.command == "list"
    assert args.search == "Петров"
    assert args.limit == 50
    assert args.offset == 10

    query = query_from_args(args)
    assert query.search == "Петров"
    assert query.limit == 50
    assert query.offset == 10


def test_parser_import_and_scan():
    """Проверяет аргументы команд import и scan."""
    parser = build_parser()
    args_import = parser.parse_args(["import", "file1.cer", "file2.crt", "--phonebook", "pb.docx"])
    assert args_import.command == "import"
    assert args_import.paths == [Path("file1.cer"), Path("file2.crt")]
    assert args_import.phonebook == Path("pb.docx")

    args_scan = parser.parse_args(["scan", "/incoming", "--output", "out.xlsx", "--mchd"])
    assert args_scan.command == "scan"
    assert args_scan.folder == Path("/incoming")
    assert args_scan.output == Path("out.xlsx")
    assert args_scan.mchd is True

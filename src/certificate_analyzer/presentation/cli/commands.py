"""Обработчики и парсер командной строки (CLI)."""

import argparse
from datetime import date
from pathlib import Path
from typing import Any

from certificate_analyzer.application.dto.certificate_dto import certificate_to_dict
from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus
from certificate_analyzer.presentation.cli.formatter import print_json


def build_parser() -> argparse.ArgumentParser:
    """Создает и настраивает парсер аргументов командной строки.

    Returns:
        argparse.ArgumentParser: Сконфигурированный парсер аргументов CLI.
    """
    parser = argparse.ArgumentParser(
        description="Хранилище записей сертификатов (SQLite)"
    )
    parser.add_argument("--config", type=Path, help="Файл настроек")
    parser.add_argument("--database", help="Файл SQLite")
    parser.add_argument("--storage-folder", help="Папка файлов сертификатов")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("gui", help="Открыть хранилище")

    importer = commands.add_parser(
        "import", help="Импортировать файлы/папки в хранилище"
    )
    importer.add_argument("paths", nargs="+", type=Path)
    importer.add_argument("--phonebook", type=Path)

    scan = commands.add_parser("scan", help="Импортировать папку сертификатов")
    scan.add_argument("folder", type=Path)
    scan.add_argument("--phonebook", type=Path)
    scan.add_argument("--output", type=Path)
    scan.add_argument("--mchd", action="store_true")

    for name in ("list", "export"):
        command = commands.add_parser(
            name, help="Записи хранилища" if name == "list" else "Отчёт из БД"
        )
        command.add_argument("--search", default="")
        command.add_argument("--status", choices=[s.value for s in CertificateStatus])
        command.add_argument("--from-date", type=date.fromisoformat)
        command.add_argument("--to-date", type=date.fromisoformat)
        command.add_argument(
            "--sort",
            default="subject",
            choices=[
                "subject",
                "valid_to",
                "valid_from",
                "issuer",
                "status",
                "department",
                "original_name",
                "serial_number",
            ],
        )
        command.add_argument("--descending", action="store_true")
        if name == "list":
            command.add_argument("--limit", type=int, default=100)
            command.add_argument("--offset", type=int, default=0)
        else:
            command.add_argument("output", type=Path)

    commands.add_parser("stats", help="Статистика БД по актуальным срокам")
    remove = commands.add_parser("delete", help="Удалить записи; файлы сохраняются")
    remove.add_argument("fingerprints", nargs="+")

    mchd = commands.add_parser("mchd", help="Анализ XML МЧД")
    mchd.add_argument("folder", type=Path)
    mchd.add_argument("--output", type=Path)

    merge = commands.add_parser("merge", help="Объединить полномочия МЧД")
    merge.add_argument("files", nargs="+", type=Path)
    merge.add_argument("--output", type=Path, required=True)

    worker = commands.add_parser("worker", help="Мониторинг записей SQLite")
    worker_mode = worker.add_mutually_exclusive_group()
    worker_mode.add_argument("--once", action="store_true")
    worker_mode.add_argument("--stop", action="store_true", help="Остановить пользовательский демон")
    autostart = commands.add_parser("autostart", help="Автозапуск демона при входе пользователя Windows/Linux")
    autostart.add_argument("action", choices=("enable", "disable"))

    return parser


def query_from_args(args: argparse.Namespace) -> CertificateQuery:
    """Формирует объект CertificateQuery на основе аргументов командной строки.

    Args:
        args: Распарсенные аргументы командной строки.

    Returns:
        CertificateQuery: Запрос фильтрации и пагинации сертификатов.
    """
    return CertificateQuery(
        search=args.search,
        status=CertificateStatus(args.status) if args.status else None,
        date_from=args.from_date,
        date_to=args.to_date,
        sort=args.sort,
        descending=args.descending,
        limit=getattr(args, "limit", None),
        offset=getattr(args, "offset", 0),
    )


def handle_stats(app: Any, _args: argparse.Namespace) -> int:
    """Выводит общую статистику распределения статусов сертификатов.

    Args:
        app: Контейнер приложения.
        _args: Аргументы командной строки.

    Returns:
        int: Код возврата процесса (0 - успех).
    """
    print_json(app.certificates.statistics())
    return 0


def handle_delete(app: Any, args: argparse.Namespace) -> int:
    """Удаляет записи сертификатов из базы данных.

    Args:
        app: Контейнер приложения.
        args: Аргументы командной строки.

    Returns:
        int: Код возврата процесса.
    """
    print_json({"deleted": app.certificates.delete_records(args.fingerprints)})
    return 0


def handle_list(app: Any, args: argparse.Namespace) -> int:
    """Выводит список сертификатов в соответствии с фильтрами в JSON.

    Args:
        app: Контейнер приложения.
        args: Аргументы командной строки.

    Returns:
        int: Код возврата процесса.
    """
    query = query_from_args(args)
    records = app.certificates.list(query)
    print_json(
        {
            "data": [certificate_to_dict(c) for c in records],
            "total": app.certificates.statistics(query)["total"],
        }
    )
    return 0


def handle_export(app: Any, args: argparse.Namespace) -> int:
    """Экспортирует выборку сертификатов в файл отчета.

    Args:
        app: Контейнер приложения.
        args: Аргументы командной строки.

    Returns:
        int: Код возврата процесса.
    """
    query = query_from_args(args)
    records = app.certificates.list(query)
    print_json(
        {
            "output": app.reports.export(
                args.output.suffix.lstrip(".").lower(),
                records,
                [],
                args.output,
            )
        }
    )
    return 0


def handle_mchd(app: Any, args: argparse.Namespace) -> int:
    """Сканирует и анализирует XML-файлы машиночитаемых доверенностей.

    Args:
        app: Контейнер приложения.
        args: Аргументы командной строки.

    Returns:
        int: Код возврата процесса (0 при отсутствии ошибок, 1 при наличии ошибок).
    """
    from certificate_analyzer.application.dto.mchd_dto import mchd_to_dict

    records = app.mchds.scan(args.folder)
    if args.output:
        app.reports.export(
            args.output.suffix.lstrip(".").lower(), [], records, args.output
        )
    print_json(
        {
            "data": [mchd_to_dict(m).to_dict() for m in records],
            "errors": app.mchds.errors,
        }
    )
    return 1 if app.mchds.errors else 0


def handle_import_or_scan(app: Any, args: argparse.Namespace) -> int:
    """Выполняет импорт файлов или рекурсивное сканирование папки сертификатов.

    Args:
        app: Контейнер приложения.
        args: Аргументы командной строки.

    Returns:
        int: Код возврата процесса.
    """
    paths, errors = [], {}
    from certificate_analyzer.infrastructure.certificates.scanner import (
        scan_files,
    )

    targets = args.paths if args.command == "import" else [args.folder]
    for path in targets:
        try:
            paths.extend(scan_files(path) if path.is_dir() else [path])
        except OSError as exc:
            errors[str(path)] = str(exc)

    result = app.certificates.import_files(paths, phonebook_path=args.phonebook)
    result.errors.update(errors)
    if getattr(args, "output", None):
        app.reports.export(
            args.output.suffix.lstrip(".").lower(),
            result.certificates,
            [],
            args.output,
        )
    print_json(
        {
            "data": [certificate_to_dict(c) for c in result.certificates],
            "errors": result.errors,
            "imported": result.imported,
            "updated": result.updated,
            "skipped": result.skipped,
        }
    )
    return 1 if result.errors else 0


def handle_merge(_app: Any, args: argparse.Namespace) -> int:
    """Объединяет полномочия выбранных XML-доверенностей МЧД.

    Args:
        _app: Контейнер приложения.
        args: Аргументы командной строки.

    Returns:
        int: Код возврата процесса.
    """
    from certificate_analyzer.infrastructure.mchd.merger import MCHDMerger

    print_json(
        {
            "output": MCHDMerger.merge_mchd_files(
                [{"file_name": str(p)} for p in args.files], args.output
            )
        }
    )
    return 0


def handle_worker(app: Any, args: argparse.Namespace) -> int:
    """Запускает процесс мониторинга записей в консольном режиме.

    Args:
        app: Контейнер приложения.
        args: Аргументы командной строки.

    Returns:
        int: Код возврата процесса.
    """
    from certificate_analyzer.runtime.worker import MonitoringWorker

    worker = MonitoringWorker(application=app)
    if args.once:
        worker.run_once()
        return 1 if worker.errors else 0
    from certificate_analyzer.runtime.linux_daemon import run

    run(worker=worker)
    return 0


def dispatch_command(app: Any, args: argparse.Namespace) -> int:
    """Диспетчеризует выполнение команды CLI соответствующему обработчику.

    Args:
        app: Контейнер приложения.
        args: Аргументы командной строки.

    Returns:
        int: Код возврата процесса.
    """
    if args.command in (None, "gui"):
        from certificate_analyzer.presentation.gui.app import run_as_gui

        run_as_gui(app, config_path=args.config)
        return 0
    if args.command == "stats":
        return handle_stats(app, args)
    if args.command == "delete":
        return handle_delete(app, args)
    if args.command == "list":
        return handle_list(app, args)
    if args.command == "export":
        return handle_export(app, args)
    if args.command == "mchd" or (args.command == "scan" and getattr(args, "mchd", False)):
        return handle_mchd(app, args)
    if args.command in ("import", "scan"):
        return handle_import_or_scan(app, args)
    if args.command == "merge":
        return handle_merge(app, args)
    if args.command == "worker":
        return handle_worker(app, args)
    return 0

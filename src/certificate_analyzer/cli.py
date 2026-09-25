import argparse
import json
import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from certificate_analyzer.application.dto.certificate_dto import certificate_to_dict
from certificate_analyzer.application.dto.certificate_query import CertificateQuery
from certificate_analyzer.bootstrap import create_application
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus


def build_parser():
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
    worker.add_argument("--once", action="store_true")
    service = commands.add_parser("service", help="Служба Windows")
    service.add_argument("service_args", nargs="*")
    return parser


def query_from_args(args):
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


def print_json(value):
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main(argv=None):
    args = build_parser().parse_args(argv)
    from certificate_analyzer.logging_config import setup_logging

    setup_logging()
    try:
        if args.command == "service":
            from certificate_analyzer.runtime.windows_service import run_as_service

            run_as_service(args.service_args)
            return 0
        from certificate_analyzer.infrastructure.config.config_loader import (
            load_settings,
        )

        settings = load_settings(args.config)
        if args.database:
            settings = replace(settings, database_path=args.database)
        if args.storage_folder:
            settings = replace(settings, storage_folder=args.storage_folder)
        with create_application(settings=settings) as app:
            if args.command in (None, "gui"):
                from certificate_analyzer.presentation.gui.app import run_as_gui

                run_as_gui(app, config_path=args.config)
                return 0
            if args.command == "stats":
                print_json(app.certificates.statistics())
            elif args.command == "delete":
                print_json(
                    {"deleted": app.certificates.delete_records(args.fingerprints)}
                )
            elif args.command in ("list", "export"):
                query = query_from_args(args)
                records = app.certificates.list(query)
                if args.command == "export":
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
                else:
                    print_json(
                        {
                            "data": [certificate_to_dict(c) for c in records],
                            "total": app.certificates.statistics(query)["total"],
                        }
                    )
            elif args.command == "mchd" or args.command == "scan" and args.mchd:
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
            elif args.command in ("import", "scan"):
                paths, errors = [], {}
                from certificate_analyzer.infrastructure.certificates.scanner import (
                    scan_files,
                )

                for path in args.paths if args.command == "import" else [args.folder]:
                    try:
                        paths.extend(scan_files(path) if path.is_dir() else [path])
                    except OSError as exc:
                        errors[str(path)] = str(exc)
                result = app.certificates.import_files(
                    paths, phonebook_path=args.phonebook
                )
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
            elif args.command == "merge":
                from certificate_analyzer.infrastructure.mchd.merger import MCHDMerger

                print_json(
                    {
                        "output": MCHDMerger.merge_mchd_files(
                            [{"file_name": str(p)} for p in args.files], args.output
                        )
                    }
                )
            elif args.command == "worker":
                from certificate_analyzer.runtime.worker import MonitoringWorker

                worker = MonitoringWorker(application=app)
                if args.once:
                    worker.run_once()
                    return 1 if worker.errors else 0
                from certificate_analyzer.runtime.linux_daemon import run

                run(worker=worker)
        return 0
    except (OSError, ValueError, RuntimeError, ImportError, SQLAlchemyError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

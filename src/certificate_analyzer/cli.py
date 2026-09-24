import argparse
import json
import logging
import sys
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Анализатор сертификатов и МЧД")
    parser.add_argument("--config", help="Путь к settings.json")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("gui", help="Открыть графический интерфейс")
    scan = commands.add_parser("scan", help="Анализ сертификатов или МЧД")
    scan.add_argument("folder")
    scan.add_argument("--mchd", action="store_true")
    scan.add_argument("--phonebook")
    scan.add_argument("--output", type=Path, help="Отчет .xlsx или .pdf")
    merge = commands.add_parser(
        "merge", help="Создать неподписанный XML с объединёнными полномочиями"
    )
    merge.add_argument("files", nargs="+")
    merge.add_argument("--output", required=True)
    worker = commands.add_parser("worker", help="Фоновый мониторинг")
    worker.add_argument("--once", action="store_true")
    service = commands.add_parser("service", help="Управление службой Windows")
    service.add_argument("service_args", nargs="*")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        if args.command in (None, "gui"):
            if args.config:
                parser.error(
                    "Для GUI используйте CERTIFICATE_ANALYZER_HOME вместо --config"
                )
            from certificate_analyzer.presentation.gui.app import run_as_gui

            run_as_gui()
            return 0
        if args.command == "service":
            from certificate_analyzer.runtime.windows_service import run_as_service

            run_as_service(args.service_args)
            return 0
        from certificate_analyzer.bootstrap import create_application

        app = create_application(args.config)
        if args.command == "worker":
            from certificate_analyzer.runtime.worker import MonitoringWorker

            if args.once:
                worker = MonitoringWorker(app.settings)
                worker.run_once()
                return 1 if worker.errors else 0
            from certificate_analyzer.runtime.linux_daemon import run

            run(app.settings)
            return 0
        if args.command == "merge":
            from certificate_analyzer.infrastructure.mchd.merger import MCHDMerger

            print(
                MCHDMerger.merge_mchd_files(
                    [{"file_name": p} for p in args.files], args.output
                )
            )
            return 0
        certificates, mchds = [], []
        if args.mchd:
            from certificate_analyzer.application.services.mchd_service import (
                MchdService,
            )
            from certificate_analyzer.application.dto.mchd_dto import mchd_to_dict

            service = MchdService()
            mchds = service.scan(args.folder)
            rows = [mchd_to_dict(m) for m in mchds]
            errors = service.errors
        else:
            if args.phonebook:
                app.certificates.load_phonebook(args.phonebook)
            app.certificates.scan_certificates(args.folder)
            rows = app.certificates.parse_certificates()
            certificates = app.certificates.certificates
            errors = app.certificates.errors
        if args.output:
            from certificate_analyzer.application.services.report_service import (
                ReportService,
            )

            ReportService().export(
                args.output.suffix.lstrip(".").lower(), certificates, mchds, args.output
            )
        print(
            json.dumps({"data": rows, "errors": errors}, ensure_ascii=False, indent=2)
        )
        return 1 if errors else 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

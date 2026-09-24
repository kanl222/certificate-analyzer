import argparse
import json
import logging
import sys
from pathlib import Path

from certificate_analyzer.bootstrap import create_application


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Анализатор сертификатов и МЧД",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Путь к файлу конфигурации",
    )

    commands = parser.add_subparsers(
        dest="command",
    )

    commands.add_parser(
        "gui",
        help="Открыть графический интерфейс",
    )

    scan = commands.add_parser(
        "scan",
        help="Анализ сертификатов",
    )

    scan.add_argument(
        "folder",
        type=Path,
    )

    scan.add_argument(
        "--phonebook",
        type=Path,
    )

    scan.add_argument(
        "--output",
        type=Path,
    )

    mchd = commands.add_parser(
        "mchd",
        help="Анализ МЧД",
    )

    mchd.add_argument(
        "folder",
        type=Path,
    )

    mchd.add_argument(
        "--output",
        type=Path,
    )

    merge = commands.add_parser(
        "merge",
        help="Объединить полномочия МЧД",
    )

    merge.add_argument(
        "files",
        nargs="+",
        type=Path,
    )

    merge.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    worker = commands.add_parser(
        "worker",
        help="Фоновый мониторинг",
    )

    worker.add_argument(
        "--once",
        action="store_true",
    )

    service = commands.add_parser(
        "service",
        help="Управление Windows Service",
    )

    service.add_argument(
        "service_args",
        nargs="*",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    from certificate_analyzer.logging_config import setup_logging
    setup_logging()

    try:
        if args.command in (None, "gui"):
            return run_gui(args)

        if args.command == "service":
            return run_windows_service(args)

        app = create_application(args.config)

        match args.command:
            case "scan":
                return run_certificate_scan(app, args)

            case "mchd":
                return run_mchd_scan(app, args)

            case "merge":
                return run_mchd_merge(app, args)

            case "worker":
                return run_worker(app, args)

            case _:
                parser.error(
                    f"Неизвестная команда: {args.command}"
                )

    except (
        OSError,
        ValueError,
        RuntimeError,
        ImportError,
    ) as exc:
        logging.exception(
            "Ошибка выполнения команды"
        )

        print(
            f"Ошибка: {exc}",
            file=sys.stderr,
        )

        return 2


def run_gui(args) -> int:
    if args.config:
        raise ValueError(
            "--config пока не поддерживается GUI"
        )

    from certificate_analyzer.presentation.gui.app import run_as_gui

    run_as_gui()

    return 0


def run_windows_service(args) -> int:
    if sys.platform != "win32":
        raise RuntimeError(
            "Команда service доступна только в Windows"
        )

    from certificate_analyzer.runtime.windows_service import run_as_service

    run_as_service(args.service_args)

    return 0


def run_certificate_scan(
    app,
    args,
) -> int:
    result = app.certificate_service.scan(
        folder=args.folder,
        phonebook_path=args.phonebook,
    )

    if args.output:
        app.report_service.export_certificates(
            certificates=result.certificates,
            output=args.output,
        )

    print_json(
        data=[
            item.to_dict()
            for item in result.certificates
        ],
        errors=result.errors,
    )

    return 1 if result.errors else 0


def run_mchd_scan(
    app,
    args,
) -> int:
    result = app.mchd_service.scan(
        args.folder
    )

    if args.output:
        app.report_service.export_mchd(
            mchds=result.items,
            output=args.output,
        )

    print_json(
        data=[
            item.to_dict()
            for item in result.items
        ],
        errors=result.errors,
    )

    return 1 if result.errors else 0


def run_mchd_merge(
    app,
    args,
) -> int:
    output = app.mchd_service.merge(
        files=args.files,
        output=args.output,
    )

    print(
        json.dumps(
            {
                "output": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


def run_worker(
    app,
    args,
) -> int:
    if args.once:
        result = app.monitoring_service.run_once()

        return 1 if result.errors else 0

    app.monitoring_service.run_forever()

    return 0


def print_json(
    *,
    data,
    errors,
) -> None:
    print(
        json.dumps(
            {
                "data": data,
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
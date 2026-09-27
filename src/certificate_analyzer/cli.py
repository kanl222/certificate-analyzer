"""Точка входа командной строки (CLI) приложения Certificate Analyzer."""

from dataclasses import replace

from sqlalchemy.exc import SQLAlchemyError

from certificate_analyzer.bootstrap import create_application
from certificate_analyzer.exceptions import CertificateAnalyzerError
from certificate_analyzer.logging_config import setup_logging
from certificate_analyzer.presentation.cli.commands import (
    build_parser,
    dispatch_command,
    query_from_args,
)
from certificate_analyzer.presentation.cli.formatter import print_error, print_json

__all__ = ["build_parser", "dispatch_command", "main", "print_json", "query_from_args"]


def main(argv=None) -> int:
    """Главная функция обработки консольных команд приложения.

    Args:
        argv: Аргументы командной строки (по умолчанию sys.argv[1:]).

    Returns:
        int: Код возврата процесса (0 - успех, 1 - частичные ошибки, 2 - критический сбой).
    """
    args = build_parser().parse_args(argv)
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
            return dispatch_command(app, args)

    except (
        OSError,
        ValueError,
        RuntimeError,
        ImportError,
        SQLAlchemyError,
        CertificateAnalyzerError,
    ) as exc:
        print_error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

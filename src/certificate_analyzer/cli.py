"""Точка входа командной строки (CLI) приложения Certificate Analyzer."""

from dataclasses import replace
import json
import os
import logging

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
        if args.command == "autostart":
            from certificate_analyzer.runtime.user_daemon import set_autostart
            set_autostart(args.action == "enable", args.config)
            return 0

        from certificate_analyzer.infrastructure.config.config_loader import (
            load_settings,
        )

        settings = load_settings(args.config)
        inherited = os.environ.pop("CERTIFICATE_ANALYZER_DAEMON_SETTINGS", None)
        if args.command == "worker" and inherited:
            from certificate_analyzer.infrastructure.config.settings import Settings
            settings = Settings(**json.loads(inherited))
        if args.database:
            settings = replace(settings, database_path=args.database)
        if args.storage_folder:
            settings = replace(settings, storage_folder=args.storage_folder)

        from certificate_analyzer.runtime.user_daemon import ensure_writer, run_writer
        if args.command == "worker" and args.stop:
            from certificate_analyzer.runtime.ipc import WriteClient
            from certificate_analyzer.infrastructure.database.session import get_database_path
            WriteClient(get_database_path(settings)).call(method="stop")
            return 0
        if args.command == "worker" and not args.once:
            run_writer(settings)
            return 0
        ensure_writer(settings)
        with create_application(settings=settings, read_only=True) as app:
            return dispatch_command(app, args)

    except (
        OSError,
        ValueError,
        RuntimeError,
        ImportError,
        SQLAlchemyError,
        CertificateAnalyzerError,
    ) as exc:
        logging.getLogger(__name__).exception("Ошибка запуска или выполнения команды приложения")
        if args.command in (None, "gui"):
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Не удалось открыть приложение", str(exc), parent=root)
            root.destroy()
        print_error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

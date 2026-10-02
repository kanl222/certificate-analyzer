# Единственный writer и пользовательский демон

Дата: 2026-10-02. Проект: certificate-analyzer.

## Файлы этой задачи

Изменены (не включает ранее существовавшие изменения пользователя):

- `src/certificate_analyzer/bootstrap.py` — сборка контейнера только для чтения и подключение API команд.
- `src/certificate_analyzer/cli.py` — запуск демона до подключения клиентов, команды автозапуска/остановки, ошибка запуска GUI.
- `src/certificate_analyzer/infrastructure/database/session.py` — SQLite URI `mode=ro`, `query_only`, миграции/WAL только у writer.
- `src/certificate_analyzer/logging_config.py` — общий ConcurrentRotatingFileHandler.
- `src/certificate_analyzer/presentation/cli/commands.py` — autostart, worker --stop.
- `src/certificate_analyzer/presentation/gui/app.py` — исключение пишущего контейнера из запуска GUI, диалоги ошибок IPC.
- `src/certificate_analyzer/presentation/gui/main_window.py` — статус демона для текущей БД.
- `src/certificate_analyzer/presentation/gui/views/settings_view.py` — инструкция перезапуска демона после изменения настроек.
- `src/certificate_analyzer/runtime/worker.py` — standalone-клиент не открывает пишущую БД.
- Устаревший `runtime/windows_service.py` удалён; команда `service` исключена из CLI.
- `src/certificate_analyzer/runtime/service_status.py` — статус через IPC вместо SCM.
- `packaging/windows/certificate-analyzer.iss` — установка для пользователя и HKCU Run.
- `packaging/windows/install-service.ps1`, `uninstall-service.ps1` — совместимые имена сценариев, теперь управляют пользовательским демоном.
- `packaging/windows/install.ps1`, `uninstall.ps1` — описание нового поведения.
- `pyproject.toml`, `uv.lock` — зависимость concurrent-log-handler.
- `README.md` — эксплуатация, переход со службы и описание IPC.
- `tests/conftest.py` — остановка демонов, запущенных CLI-тестами.
- `tests/unit/test_security_hardening.py` — проверка запрета установки службы вместо проверки LocalService.

Добавлены:

- `src/certificate_analyzer/runtime/write_api.py` — разрешённые команды, JSON-кодек доменных данных, клиентские адаптеры.
- `src/certificate_analyzer/runtime/ipc.py` — сервер/клиент, аутентификация, эксклюзивное владение адресом, структурированные ответы.
- `src/certificate_analyzer/runtime/user_daemon.py` — жизненный цикл writer, автозапуск, мониторинг.
- `tests/integration/test_single_writer.py` — реальные отдельные процессы, CRUD, импорт, аудит, WAL, ошибки, перезапуск.
- `docs/single-writer-architecture.md` — этот отчёт.

## Какие записи из GUI устранены

Прямого SQL в актуальных представлениях GUI не было: они вызывали локальные сервисы, открывавшие пишущие репозитории. Эти пути перенаправлены в IPC на уровне сборки контейнера, без массового изменения обработчиков.

| Исходный GUI | Путь записи, перенесённый в демон |
|---|---|
| certificates_view.py | import_files, import_folder, load_phonebook, delete_records, delete_file |
| certificates_view.py, CertificateService | аудит FILE_OPENED / FILE_REVEALED при открытии/показе файла |
| employees_view.py | save_employee, delete_employee, create_request |
| requests_view.py | create_request, update_status (включая PROCESSED), link_certificate, delete_request |
| mchd_view.py | scan(save_to_db=True), import_files(save_to_db=True), delete |
| bootstrap.py / Database | migrate, create_all, включение WAL при запуске GUI |

Дополнительно API покрывает get_or_create сотрудника, save МЧД и log_event аудита. GUI-физически не может выполнить INSERT/UPDATE/DELETE даже через ошибочно вызванный локальный репозиторий. Схема и бизнес-логика сервисов сохранены.

## Поток данных

1. GUI вызывает прежний публичный метод сервиса.
2. CommandService отправляет разрешённую команду JSON с аргументами и токеном.
3. Демон проверяет версию/токен/список команд и последовательно вызывает прежний бизнес-сервис.
4. Репозитории демона фиксируют изменения SQLite. Мониторинг синхронизирован с командами внутрипроцессной блокировкой.
5. Ответ содержит `ok`, `result` (включая ID, модели, счётчики), `errors` отдельных файлов либо `error`/`error_type`.
6. GUI получает результат; существующие обработчики обновляют таблицы из своей БД только для чтения.

## IPC и единственность writer

Выбран JSON через loopback TCP (`127.0.0.1`): одинаковый транспорт Windows/Linux, стандартная библиотека, явные таймауты, без pickle. Адрес вычисляется из нормализованного абсолютного пути БД. Демон эксклюзивно занимает адрес **до открытия SQLite**, поэтому второй штатный writer не выполняет миграции и записи. Коллизия порта приводит к безопасному отказу запуска. Клиенты и демон должны использовать один абсолютный путь БД.

Токен публикуется атомарно; на Windows DACL разрешает доступ только владельцу процесса, на Unix выставляется 0600. Сокет недоступен через внешний сетевой интерфейс. Допускаются только явно перечисленные команды и типы. Максимальный пакет 16 MiB, подключение до 2 секунд, ожидание команды до 120 секунд.

SQLite WAL позволяет читать параллельно с записью. Filelock для обычных операций БД не используется. ConcurrentLogHandler применяет свою синхронизацию исключительно для общего журнала.

Низкоуровневая фабрика `create_application(read_only=False)` сохранена для демона и изолированных тестов. Штатные CLI/GUI сценарии используют только `read_only=True`.

## Ошибки и запуск

GUI запускает user-space daemon при первом открытии и не останавливает его при закрытии окна. HKCU Run запускает worker при входе текущего пользователя. Установка не требует администратора и не использует LocalService. Каталог пользовательских данных сохранён: `~/.certificate-analyzer` либо `CERTIFICATE_ANALYZER_HOME`.

При недоступности/таймауте клиент выбрасывает WriterUnavailable; ошибки выполнения — WriteCommandError. GUI показывает сообщение через существующие обработчики либо обработчик исключений Tk. Записи самостоятельно не выполняются. После обрыва соединения клиент не повторяет команду автоматически: она могла завершиться; пользователь должен проверить данные перед повтором. При перезапуске демона существующий GUI перечитывает токен для следующей команды.

Изменённые настройки требуют остановить демон (`worker --stop`) и перезапустить приложение. Старую установленную службу администратор должен остановить и удалить: `sc.exe stop CertificateAnalyzerService`, `sc.exe delete CertificateAnalyzerService`. Эти команды в рамках задачи на машине пользователя не выполнялись.

## Проверка

Проверены отдельный процесс writer, сохранение/изменение/удаление сотрудников, возвращаемые ID заявок, изменение статуса, импорт сертификатов и МЧД, аудит открытия файла, ошибки импорта, отказ прямого DELETE из GUI, отказ второго writer и неверного токена, несколько IPC-клиентов при открытом снимке WAL, недоступность и восстановление после перезапуска.

Устаревший тест отсутствующего модуля Gemini удалён. Проверка миграции сравнивает версию с актуальной SCHEMA_VERSION и сохраняет проверку переноса полномочий. Полный набор запускается без исключений. Итоговые результаты повторной проверки приведены ниже.

Установщик и GUI вручную не запускались; проверки GUI, требующие доступного Tk, могут пропускаться. Linux-autostart проверен с подменой systemd на Windows; нужен дополнительный запуск на Linux. Компилятор Inno Setup не найден, установщик не собирался.

После очистки: полный набор — 153 passed, 17 skipped, без исключений; Ruff по src/tests проходит.

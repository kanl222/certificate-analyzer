# Анализатор сертификатов и МЧД

Приложение для просмотра сертификатов X.509 и машиночитаемых доверенностей. Код перенесён из `legacy/certificate_analyzer_old.py` в пакет `src/certificate_analyzer`; установленное приложение не зависит от каталога `legacy`.

## Установка и запуск

Python 3.11 или новее, менеджер пакетов `uv`:

```sh
uv sync --extra gui
uv run certificate-analyzer
```

GUI использует Tkinter/Tk, который должен быть установлен в системе. Для PDF с кириллицей нужен Arial, DejaVu Sans или Noto Sans. На Windows дополнительно установите платформенные зависимости: `uv sync --extra gui --extra windows`.

Без GUI: `uv sync`. Пакет также устанавливается через `pip install .` или `pip install '.[gui]'`.

```sh
uv run certificate-analyzer scan /path/to/certificates
uv run certificate-analyzer scan /path/to/certificates --phonebook phones.docx --output report.xlsx
uv run certificate-analyzer scan /path/to/mchd --mchd --output report.pdf
uv run certificate-analyzer merge first.xml second.xml --output draft.xml
uv run certificate-analyzer worker --once
uv run certificate-analyzer --config /path/to/settings.json worker
```

`scan` выводит JSON с `data` и `errors`. Код выхода: 0 — успешно, 1 — часть файлов или папок не обработана, 2 — ошибка запуска/настроек. GUI запускается без аргументов или командой `gui`.

## Возможности

- Рекурсивный поиск CER/CRT/DER/PEM, чтение X.509, ФИО, email, кабинета и подразделения. Повреждённые файлы не останавливают обработку остальных.
- Статусы по UTC: просрочен, истекает в течение 60 дней, активен; сертификат с будущей датой начала считается недействительным на момент проверки. Проверяется срок, а не цепочка доверия или отзыв через OCSP/CRL.
- МЧД: номер, даты, доверитель, представитель, персональные данные и полномочия. Поддержаны формы полей из legacy и пространства имён XML. Неизвестная дата считается ошибкой, а не заменяется сегодняшней.
- Объединение полномочий МЧД в отдельный неподписанный XML-черновик. Требуются одинаковые доверитель, представитель и сроки; исходные документы не перезаписываются. Иные UUID и namespace сохраняются. Результат не является подписанной действующей доверенностью; XSD-валидация и проверка электронной подписи не выполняются.
- Справочник TXT с колонками через `|` и таблицы DOCX: подразделение, ФИО, кабинет, до трёх телефонных колонок. Поиск по кабинету, полному имени, подразделению; email не выдаётся за телефон.
- Excel и PDF с русским текстом, контактами и полномочиями, PDF с графиком из GUI.
- GUI: таблицы, поиск, сортировка, календарь, фильтр дат, графики, избранные папки, просмотр МЧД и полномочий, история уведомлений, настройки и справочные окна.
- Фоновый мониторинг сертификатов, отчёт `monitoring.xlsx`, уведомления и остановка по сигналу. Linux — `notify-send`, Windows — `win10toast` при наличии.

## Настройки и данные

По умолчанию: `~/.certificate-analyzer/settings.json`. Каталог можно изменить переменной `CERTIFICATE_ANALYZER_HOME`. В нём же находятся `notification_config.json` и `notification_history.json`. CLI/worker принимают `--config` перед подкомандой; GUI использует пользовательский каталог.

```json
{
  "folders": {"📁 Сотрудники": "/data/certificates"},
  "mchd_folder": "/data/mchd",
  "export_folder": "/data/reports",
  "phonebook_path": null,
  "warning_days": 60,
  "check_interval": 604800
}
```

Если новой конфигурации нет, читается старый `~/cert_analyzer_config.json`. История также подхватывается из старого `~/notification_history.json`. Старые `notification_config.json` и `service_config.json`, которые лежали рядом со скриптом, автоматически не импортируются: задайте интервалы в GUI и пути в новой конфигурации. Ошибочный JSON не перезаписывается автоматически.

GUI сохраняет путь справочника и папку МЧД. Настройки всплывающих уведомлений GUI независимы от расписания worker. Сохранение основной конфигурации и истории атомарное.

## Фоновая служба

Linux: после установки пакета выполните `bash packaging/linux/install.sh` из окружения, где доступна команда `certificate-analyzer`. Это установит и запустит пользовательский systemd-сервис; удаление — `bash packaging/linux/uninstall.sh`. Файл `packaging/linux/cert-analyzer.service` — пример для установки исполняемого файла в `~/.local/bin`.

Windows: из административного терминала с установленным пакетом и extra `windows` выполните `python -m certificate_analyzer service install`, затем `python -m certificate_analyzer service start`. Удаление: `python -m certificate_analyzer service remove`. Служба читает настройки профиля своей учётной записи: задайте для неё `CERTIFICATE_ANALYZER_HOME` или подготовьте конфигурацию в этом профиле. Установка/запуск системных служб не выполняются автоматически при установке пакета.

## Разработка

```sh
uv run pytest
uv run ruff check src tests --select F
uv build
```

Слои: `domain` — модели и статусы; `application` — сервисы и DTO; `infrastructure` — парсеры, хранение, отчёты и платформенные адаптеры; `presentation/gui` — окна и контроллеры; `runtime` — worker и службы. Часть пустых файлов исходного каркаса оставлена под дальнейшее развитие.

Решения, прогресс переноса и результаты проверок записаны в [MEMORY.md](MEMORY.md). Windows Service требует проверки на Windows; автоматическая проверка на Linux не подтверждает работу Windows API.

GUI smoke-test запускается отдельно в графической сессии:

```sh
CERTIFICATE_ANALYZER_GUI_TEST=1 uv run --extra gui pytest tests/integration/test_gui.py -q
```

Он использует временную конфигурацию и синтетические файлы, проверяет окна, поиск, сохранение настроек и восемь типов графиков, затем закрывает окна.

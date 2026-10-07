# SQLCipher — реализация без внедрения

`infrastructure/database/sqlcipher.py` — отдельный адаптер. Он не подключён
к `Database`, bootstrap, GUI, демону, архиву переноса или миграциям приложения.
Текущая база остаётся обычной SQLite, зависимости и установщики не изменены.

## Возможности

- `create_database(path, key)` создаёт новую зашифрованную базу.
- `connect(path, key, read_only=True)` открывает существующую базу.
  Чтение ограничено режимом `mode=ro` и `query_only`; writer включает WAL.
- `encrypt_copy(source, destination, key)` создаёт SQLite backup с учётом WAL
  и преобразует его через `sqlcipher_export`, сохраняя исходник.
- `rotate_key_copy(source, destination, old_key, new_key)` меняет ключ
  через новую копию, без изменения исходной зашифрованной БД.
- `create_sqlalchemy_engine(...)` создаёт отдельный engine без миграций.

Ключ — случайные 32 байта. Используйте `DataCipher.generate_key()` либо
`secrets.token_bytes(32)`. Пароль напрямую не принимается: его преобразование
в ключ и хранение ключа нужно проектировать отдельно. Ключ нельзя помещать
в URI подключения, settings.json, журнал или рядом с базой.

```python
from contextlib import closing
from pathlib import Path
from secrets import token_bytes
from certificate_analyzer.infrastructure.database.sqlcipher import encrypt_copy, connect

key = token_bytes(32)  # Сохранить отдельно в защищённом хранилище.
encrypted = encrypt_copy(Path("original.db"), Path("encrypted.db"), key)
with closing(connect(encrypted, key)) as connection:
    rows = connection.execute("SELECT subject FROM certificates").fetchall()
```

## Драйвер и проверки

Нужен DB-API драйвер `sqlcipher3`, содержащий SQLCipher ветки 4, версии 4.2+.
Он импортируется только при явном вызове адаптера. Обычный SQLite не используется
как запасной вариант: отсутствие `cipher_version` приводит к ошибке.
Установка для отдельного эксперимента: `uv pip install sqlcipher3`.
Перед включением в релиз нужно закрепить проверенную версию и проверить
доступность сборок на каждой платформе.

Ключ устанавливается до чтения таблиц. Проверяются доступность схемы,
`cipher_integrity_check` и обычный `integrity_check` при создании/преобразовании.
Обычное открытие проверяет доступность схемы без полного сканирования базы.
Для формата задаётся `cipher_compatibility=4`. При переносе сохраняются
`user_version` и `application_id`, которые `sqlcipher_export` не переносит
автоматически. Несуществующие базы не создаются операцией открытия.

Перед преобразованием или сменой ключа остановите демон и закройте GUI.
Проверка IPC-токена не заменяет защиту от конкурентного запуска. Существующая
целевая база и её журналы не перезаписываются; при ошибке новая копия удаляется.
Временный SQLite backup содержит открытые данные, штатно удаляется после операции;
гарантированное стирание носителя не обеспечивается. POSIX-права не заменяют ACL
Windows, поэтому используйте приватную папку своего профиля.

## Будущее подключение

Нужно отдельно адаптировать миграции и backup, выдачу ключа, восстановление
и защищённый архив переноса. Текущий архив использует обычный sqlite3 и не умеет
открывать SQLCipher. Преобразованная база пока не открывается обычным запуском
приложения. Сам адаптер не реализует правило единственного writer-процесса:
при интеграции запись разрешается демону, GUI получает только read-only engine
либо чтение через IPC. SQLCipher не шифрует внешние CER/XML-файлы.

Официальное описание: [SQLCipher API](https://www.zetetic.net/sqlcipher/sqlcipher-api/)
и [преобразование SQLite](https://www.zetetic.net/sqlcipher/encrypting-plaintext-databases/).

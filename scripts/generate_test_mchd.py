"""Генератор тестовых файлов машиночитаемых доверенностей (МЧД) в формате XML.

Создает набор демонстрационных XML-файлов с различными статусами
(действующие, истекающие, просроченные, объединяемые, дубликаты представителей,
форматы ФНС и Минцифры, а также файл с ошибкой парсинга).
"""

from __future__ import annotations

from datetime import datetime, timedelta
import html
from pathlib import Path
import sys


def _esc(value: str) -> str:
    """Экранирует специальные символы для безопасной вставки в атрибуты XML.

    Args:
        value: Исходная строка.

    Returns:
        str: Экранированная строка.
    """
    return html.escape(str(value), quote=True)


def create_fns_mchd_xml(
    doc_uuid: str,
    internal_number: str,
    issue_date: datetime,
    expiry_date: datetime,
    principal_name: str,
    principal_inn: str,
    principal_kpp: str,
    principal_ogrn: str,
    rep_fio: tuple[str, str, str],  # Фамилия, Имя, Отчество
    rep_inn: str,
    rep_snils: str,
    authorities: list[tuple[str, str]],  # (Код, Наименование)
) -> str:
    """Генерирует XML машиночитаемой доверенности в формате ФНС.

    Args:
        doc_uuid: Уникальный идентификатор (GUID) доверенности.
        internal_number: Внутренний номер документа в организации.
        issue_date: Дата выдачи доверенности.
        expiry_date: Дата окончания срока действия доверенности.
        principal_name: Наименование организации-доверителя.
        principal_inn: ИНН организации (10 цифр).
        principal_kpp: КПП организации (9 цифр).
        principal_ogrn: ОГРН организации (13 цифр).
        rep_fio: Кортеж (Фамилия, Имя, Отчество) уполномоченного представителя.
        rep_inn: ИНН физического лица - представителя (12 цифр).
        rep_snils: СНИЛС представителя (11 цифр).
        authorities: Список кортежей полномочий вида (Код, Наименование).

    Returns:
        str: Содержимое XML-документа МЧД в кодировке UTF-8.
    """
    last_name, first_name, middle_name = rep_fio
    dt_from_str = issue_date.strftime("%d.%m.%Y")
    dt_to_str = expiry_date.strftime("%d.%m.%Y")

    auth_xml_elements = "\n".join(
        f'      <МашПолн КодПолн="{_esc(code)}" НаимПолн="{_esc(name)}"/>'
        for code, name in authorities
    )

    return f"""<?xml version="1.0" encoding="utf-8"?>
<Доверенность xmlns="urn:fns:mchd:002" ИдФайл="ON_EMCHD_{datetime.now():%Y%m%d}_{doc_uuid}">
  <СвДов НомДовер="{doc_uuid}" ИдДовер="{doc_uuid}" ВнНомДовер="{_esc(internal_number)}" ДатаВыдДовер="{dt_from_str}" ДатаВыд="{dt_from_str}" СрокДейст="{dt_to_str}" ДатаКон="{dt_to_str}"/>
  <СвРосОрг НаимОрг="{_esc(principal_name)}" ИННЮЛ="{principal_inn}" КПП="{principal_kpp}" ОГРН="{principal_ogrn}"/>
  <СвУпПред ТипПред="3">
    <СведФизЛ СНИЛС="{rep_snils}" ИННФЛ="{rep_inn}"/>
    <ФИО Фамилия="{_esc(last_name)}" Имя="{_esc(first_name)}" Отчество="{_esc(middle_name)}"/>
  </СвУпПред>
  <ЛицоБезДов>
    <СвФЛ ИННФЛ="770199999999"/>
    <ФИО Фамилия="Руководитель" Имя="Алексей" Отчество="Владимирович"/>
  </ЛицоБезДов>
  <СвПолн>
{auth_xml_elements}
  </СвПолн>
  <СведСист>https://m4d.nalog.gov.ru/emchd/check-status?guid={doc_uuid}</СведСист>
</Доверенность>
"""


def create_mincifry_mchd_xml(
    doc_uuid: str,
    internal_number: str,
    issue_date: datetime,
    expiry_date: datetime,
    principal_name: str,
    principal_inn: str,
    principal_kpp: str,
    principal_ogrn: str,
    rep_fio: tuple[str, str, str],
    rep_inn: str,
    rep_snils: str,
    authorities: list[tuple[str, str]],
) -> str:
    """Генерирует XML МЧД единого формата Минцифры (Формат 003).

    Args:
        doc_uuid: Уникальный идентификатор (GUID) доверенности.
        internal_number: Внутренний номер документа.
        issue_date: Дата выдачи.
        expiry_date: Дата окончания.
        principal_name: Наименование организации-доверителя.
        principal_inn: ИНН организации.
        principal_kpp: КПП организации.
        principal_ogrn: ОГРН организации.
        rep_fio: Кортеж (Фамилия, Имя, Отчество) представителя.
        rep_inn: ИНН представителя.
        rep_snils: СНИЛС представителя.
        authorities: Список полномочий.

    Returns:
        str: Содержимое XML-документа МЧД.
    """
    last_name, first_name, middle_name = rep_fio
    dt_from_str = issue_date.strftime("%Y-%m-%d")
    dt_to_str = expiry_date.strftime("%Y-%m-%d")

    auth_elements = "\n".join(
        f'        <МашПолн КодПолн="{_esc(code)}" НаимПолн="{_esc(name)}"/>'
        for code, name in authorities
    )

    return f"""<?xml version="1.0" encoding="utf-8"?>
<Доверенность xmlns="urn:mincifry:emchd:003" ИдФайл="EMCHD_{doc_uuid}">
  <СвДов НомДовер="{doc_uuid}" DocumentId="{doc_uuid}" ВнНомДовер="{_esc(internal_number)}" ДатаВыдДовер="{dt_from_str}" IssueDate="{dt_from_str}" СрокДейст="{dt_to_str}" ExpiryDate="{dt_to_str}"/>
  <СвРосОрг НаимОрг="{_esc(principal_name)}" ИННЮЛ="{principal_inn}" КПП="{principal_kpp}" ОГРН="{principal_ogrn}"/>
  <СвУпПред ТипПред="3">
    <СведФизЛ СНИЛС="{rep_snils}" ИННФЛ="{rep_inn}"/>
    <ФИО Фамилия="{_esc(last_name)}" Имя="{_esc(first_name)}" Отчество="{_esc(middle_name)}"/>
  </СвУпПред>
  <СвПолн>
{auth_elements}
  </СвПолн>
</Доверенность>
"""


def generate_all_test_mchds(output_dir: Path | str) -> list[Path]:
    """Создает полный комплект тестовых файлов МЧД в целевой директории.

    Включает следующие сценарии:
    1. Действующая доверенность (ACTIVE).
    2. Вторая доверенность того же представителя и доверителя с идентичным сроком (для проверки MCHDMerger).
    3. Истекающая в ближайшие 25 дней доверенность (EXPIRING_SOON).
    4. Просроченная доверенность (EXPIRED).
    5. Доверенность от другой организации на того же представителя (проверка дубликатов).
    6. Доверенность формата 003 Минцифры.
    7. Документ с некорректной датой (проверка статуса "Ошибка парсинга").

    Args:
        output_dir: Директория для сохранения созданных XML-файлов.

    Returns:
        list[Path]: Список путей к созданным файлам.
    """
    target_path = Path(output_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    today = datetime.now()
    generated_files: list[Path] = []

    # Общие даты для объединяемых доверенностей 1 и 2
    merge_from = today - timedelta(days=90)
    merge_to = today + timedelta(days=275)

    # 1. Действующая МЧД № 1 (Северные Технологии -> Иванов)
    uuid_1 = "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
    content_1 = create_fns_mchd_xml(
        doc_uuid=uuid_1,
        internal_number="МЧД-2026/001",
        issue_date=merge_from,
        expiry_date=merge_to,
        principal_name='ООО "Северные Технологии"',
        principal_inn="7701234567",
        principal_kpp="770101001",
        principal_ogrn="1027700132195",
        rep_fio=("Иванов", "Иван", "Иванович"),
        rep_inn="770198765432",
        rep_snils="123-456-789 01",
        authorities=[
            ("BUN_001", "Подписание бухгалтерской и налоговой отчетности"),
            ("BUN_002", "Взаимодействие с налоговыми органами и фондами"),
            ("STAT_001", "Предоставление статистической отчетности"),
        ],
    )
    p1 = target_path / "mchd_active_01.xml"
    p1.write_text(content_1, encoding="utf-8")
    generated_files.append(p1)

    # 2. Действующая МЧД № 2 для того же доверителя и представителя (для слияния)
    uuid_2 = "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e"
    content_2 = create_fns_mchd_xml(
        doc_uuid=uuid_2,
        internal_number="МЧД-2026/002-ФИН",
        issue_date=merge_from,
        expiry_date=merge_to,
        principal_name='ООО "Северные Технологии"',
        principal_inn="7701234567",
        principal_kpp="770101001",
        principal_ogrn="1027700132195",
        rep_fio=("Иванов", "Иван", "Иванович"),
        rep_inn="770198765432",
        rep_snils="123-456-789 01",
        authorities=[
            ("FIN_001", "Подписание договоров поставки и соглашений"),
            ("BANK_005", "Распоряжение банковскими счетами и платежными поручениями"),
        ],
    )
    p2 = target_path / "mchd_active_02_mergeable.xml"
    p2.write_text(content_2, encoding="utf-8")
    generated_files.append(p2)

    # 3. Истекающая МЧД (срок через 25 дней, EXPIRING_SOON)
    uuid_3 = "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f"
    content_3 = create_fns_mchd_xml(
        doc_uuid=uuid_3,
        internal_number="МЧД-КДР-44",
        issue_date=today - timedelta(days=150),
        expiry_date=today + timedelta(days=25),
        principal_name='АО "ПромИнвестХолдинг"',
        principal_inn="7725987654",
        principal_kpp="772501001",
        principal_ogrn="1157746123456",
        rep_fio=("Смирнова", "Елена", "Сергеевна"),
        rep_inn="772512345678",
        rep_snils="234-567-890 12",
        authorities=[
            ("KDR_001", "Кадровый документооборот"),
            ("KDR_002", "Подписание трудовых договоров и приказов"),
        ],
    )
    p3 = target_path / "mchd_expiring_soon.xml"
    p3.write_text(content_3, encoding="utf-8")
    generated_files.append(p3)

    # 4. Просроченная МЧД (срок истек 45 дней назад, EXPIRED)
    uuid_4 = "4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a"
    content_4 = create_fns_mchd_xml(
        doc_uuid=uuid_4,
        internal_number="АРХИВ-2025/99",
        issue_date=today - timedelta(days=400),
        expiry_date=today - timedelta(days=45),
        principal_name='ПАО "ГазНефтьСервис"',
        principal_inn="7802112233",
        principal_kpp="780201001",
        principal_ogrn="1037800045678",
        rep_fio=("Кузнецов", "Алексей", "Петрович"),
        rep_inn="780287654321",
        rep_snils="345-678-901 23",
        authorities=[
            ("LOG_001", "Таможенное декларирование грузов"),
        ],
    )
    p4 = target_path / "mchd_expired.xml"
    p4.write_text(content_4, encoding="utf-8")
    generated_files.append(p4)

    # 5. МЧД на того же представителя (Кузнецов), но от другой компании (для проверки поиска дубликатов)
    uuid_5 = "5e6f7a8b-9c0d-1e2f-3a4b-5c6d7e8f9a0b"
    content_5 = create_fns_mchd_xml(
        doc_uuid=uuid_5,
        internal_number="ТЛ-2026/07",
        issue_date=today - timedelta(days=30),
        expiry_date=today + timedelta(days=335),
        principal_name='ООО "ТрансЛогистик"',
        principal_inn="7733445566",
        principal_kpp="773301001",
        principal_ogrn="1187746789012",
        rep_fio=("Кузнецов", "Алексей", "Петрович"),
        rep_inn="780287654321",
        rep_snils="345-678-901 23",
        authorities=[
            ("LOG_002", "Подписание товарно-транспортных накладных (ТТН)"),
            ("EXP_001", "Экспедирование и сопровождение грузов"),
        ],
    )
    p5 = target_path / "mchd_duplicate_representative.xml"
    p5.write_text(content_5, encoding="utf-8")
    generated_files.append(p5)

    # 6. МЧД единого формата Минцифры 003
    uuid_6 = "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c"
    content_6 = create_mincifry_mchd_xml(
        doc_uuid=uuid_6,
        internal_number="МИНЦ-2026/10",
        issue_date=today - timedelta(days=20),
        expiry_date=today + timedelta(days=400),
        principal_name='ООО "Инновационные Цифровые Системы"',
        principal_inn="7709876543",
        principal_kpp="770901001",
        principal_ogrn="1197746554433",
        rep_fio=("Васильев", "Дмитрий", "Николаевич"),
        rep_inn="770912345678",
        rep_snils="456-789-012 34",
        authorities=[
            ("FED_GOS_01", "Взаимодействие с государственными системами (ЕИС, Госуслуги)"),
            ("FED_SIGN_02", "Право электронной подписи первичных документов"),
        ],
    )
    p6 = target_path / "mchd_mincifry_format_003.xml"
    p6.write_text(content_6, encoding="utf-8")
    generated_files.append(p6)

    # 7. Некорректный файл (для тестирования отображения ошибок парсинга)
    p7 = target_path / "mchd_invalid_error.xml"
    p7.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<Доверенность xmlns="urn:test:broken">
  <СвДов НомДовер="BROKEN-UUID-999" ДатаВыдДовер="не_дата" СрокДейст="ошибка_даты"/>
  <СвРосОрг НаимОрг="ООО &quot;Некорректный Файл&quot;" ИННЮЛ="123"/>
</Доверенность>
""",
        encoding="utf-8",
    )
    generated_files.append(p7)

    return generated_files


if __name__ == "__main__":
    out_dir = Path("test_mchd") if len(sys.argv) < 2 else Path(sys.argv[1])
    created = generate_all_test_mchds(out_dir)
    print(f"Успешно создано {len(created)} тестовых МЧД в каталоге: {out_dir.resolve()}")
    for f in created:
        print(f"  • {f.name}")

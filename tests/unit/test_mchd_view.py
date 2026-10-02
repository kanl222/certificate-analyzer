"""Тесты для представления вкладки МЧД MchdView и сопутствующих диалоговых окон."""

import os
from types import SimpleNamespace
from typing import Any
import pytest

from certificate_analyzer.presentation.gui.views.mchd_view import (
    MchdPersonalDataWindow,
    MchdView,
)
from certificate_analyzer.presentation.gui.styles import TEXT_COLOR, WARNING_TEXT


def _sample_mchd_records() -> list[dict[str, Any]]:
    """Возвращает пример набора записей МЧД для тестирования интерфейса.

    Returns:
        Список словарей с атрибутами доверенностей.
    """
    return [
        {
            "doc_number": "MCHD-001-A",
            "issue_date": "2025-01-10",
            "expiry_date": "2026-01-10",
            "full_name": "Иванов Иван Иванович",
            "principal_name": "ООО Ромашка",
            "status": "Действует",
            "authority_codes": ["SIGN_DOC", "SEND_RPT"],
            "principal_inn": "7701000001",
            "principal_ogrn": "1027700000001",
            "representative_inn": "770200000001",
            "representative_snils": "123-456-789 01",
            "authority_limitations": "Без ограничений",
            "xml_path": "C:/mchd/doc1.xml",
        },
        {
            "doc_number": "MCHD-002-B",
            "issue_date": "2024-05-01",
            "expiry_date": "2025-05-01",
            "full_name": "Петров Петр Петрович",
            "principal_name": "ООО Василек",
            "status": "Просрочен",
            "authority_codes": ["VIEW_ALL"],
            "principal_inn": "7702000002",
            "principal_ogrn": "1027700000002",
            "representative_inn": "770300000002",
            "representative_snils": "987-654-321 02",
            "authority_limitations": "Только чтение",
            "xml_path": "C:/mchd/doc2.xml",
        },
        {
            "doc_number": "MCHD-003-C",
            "issue_date": "2025-01-15",
            "expiry_date": "2026-01-15",
            "full_name": "Иванов Иван Иванович",
            "principal_name": "ООО Ромашка",
            "status": "Действует",
            "authority_codes": ["SIGN_DOC"],
            "principal_inn": "7701000001",
            "principal_ogrn": "1027700000001",
            "representative_inn": "770200000001",
            "representative_snils": "123-456-789 01",
            "authority_limitations": "Без ограничений",
            "xml_path": "C:/mchd/doc3.xml",
        },
    ]


def test_mchd_view_status_tag():
    """Проверяет сопоставление статуса доверенности с тегом цветового оформления."""
    assert MchdView._get_status_tag("Просрочен") == "expired"
    assert MchdView._get_status_tag("Отозвана") == "expired"
    assert MchdView._get_status_tag("Истекает через 5 дней") == "warning"
    assert MchdView._get_status_tag("Действует") == "normal"


def test_mchd_warning_text_uses_readable_dark_color():
    """Текст предупреждения на жёлтом фоне должен оставаться контрастным."""
    assert WARNING_TEXT == TEXT_COLOR


def test_mchd_double_click_ignores_empty_table_space():
    """Двойной щелчок вне строки не должен пытаться открыть карточку."""
    opened: list[bool] = []
    tree = SimpleNamespace(identify_row=lambda _y: "")
    view = SimpleNamespace(
        tree=tree,
        view_personal_data=lambda: opened.append(True),
    )

    MchdView.on_double_click(view, SimpleNamespace(y=500))

    assert opened == []


def test_mchd_double_click_opens_row_under_pointer():
    """Двойной щелчок по строке открывает именно эту МЧД."""
    opened: list[bool] = []
    selected: list[str] = []
    focused: list[str] = []
    tree = SimpleNamespace(
        identify_row=lambda _y: "row-2",
        selection_set=selected.append,
        focus=focused.append,
    )
    view = SimpleNamespace(
        tree=tree,
        view_personal_data=lambda: opened.append(True),
    )

    MchdView.on_double_click(view, SimpleNamespace(y=120))

    assert selected == ["row-2"]
    assert focused == ["row-2"]
    assert opened == [True]


@pytest.mark.skipif(
    not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"),
    reason="GUI-тест отключен без флага окружения",
)
def test_mchd_view_population_and_filtering():
    """Проверяет инициализацию MchdView, фильтрацию по поисковому запросу и статусу."""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        messages: list[str] = []
        data = _sample_mchd_records()
        view = MchdView(
            root,
            application=None,
            on_message=messages.append,
            mchd_data=data,
        )
        view.pack()

        # Все три записи загружены
        assert len(view.mchd_data) == 3
        assert len(view.tree.get_children()) == 3

        # Фильтрация по поисковой строке (ФИО)
        view.search_var.set("Петров")
        view.apply_filters()
        assert len(view.filtered_data) == 1
        assert view.filtered_data[0]["doc_number"] == "MCHD-002-B"
        assert len(view.tree.get_children()) == 1

        # Очистка поиска
        view.clear_search()
        assert len(view.tree.get_children()) == 3

        # Фильтрация по статусу "Просрочен"
        view.status_var.set("Просрочен")
        view.apply_filters()
        assert len(view.filtered_data) == 1
        assert view.filtered_data[0]["status"] == "Просрочен"

        # Сброс статуса
        view.status_var.set("Все статусы")
        view.apply_filters()
        assert len(view.filtered_data) == 3
    finally:
        root.destroy()


@pytest.mark.skipif(
    not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"),
    reason="GUI-тест отключен без флага окружения",
)
def test_mchd_view_duplicate_detection():
    """Проверяет отображение баннера дубликатов при наличии одинаковых представителей."""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        data = _sample_mchd_records()
        view = MchdView(
            root,
            application=None,
            mchd_data=data,
        )
        view.pack()

        # Должен быть обнаружен дубликат по Иванову (2 действующие МЧД)
        assert len(view.duplicate_frame.winfo_children()) > 0

        # Фильтруем только уникального представителя Петрова
        view.search_var.set("Петров")
        view.apply_filters()
        # В баннере остается общий подсчет, либо при очистке
        assert len(view.filtered_data) == 1
    finally:
        root.destroy()


@pytest.mark.skipif(
    not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"),
    reason="GUI-тест отключен без флага окружения",
)
def test_mchd_personal_data_window():
    """Проверяет создание карточки персональных данных доверенности MchdPersonalDataWindow."""
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        data = _sample_mchd_records()[0]
        card = MchdPersonalDataWindow(root, data)
        assert card.window is not None
        assert card.window.title() == "Персональные данные МЧД: MCHD-001-A"
        assert card.window.winfo_exists()
    finally:
        root.destroy()

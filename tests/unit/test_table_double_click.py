"""Регрессии двойного щелчка по пустому месту основных таблиц."""

from types import SimpleNamespace

import pytest

from certificate_analyzer.presentation.gui.views.certificates_view import (
    CertificatesView,
)
from certificate_analyzer.presentation.gui.views.employees_view import EmployeesView
from certificate_analyzer.presentation.gui.views.requests_view import RequestsView


@pytest.mark.parametrize(
    ("view_class", "action_name"),
    (
        (CertificatesView, "open_certificate"),
        (RequestsView, "show_status_dialog"),
        (EmployeesView, "edit_selected"),
    ),
)
def test_main_table_double_click_ignores_empty_space(view_class, action_name):
    """Пустая область таблицы не должна запускать действие вкладки."""
    actions: list[bool] = []
    view = SimpleNamespace(
        tree=SimpleNamespace(identify_row=lambda _y: ""),
        **{action_name: lambda: actions.append(True)},
    )

    view_class.on_double_click(view, SimpleNamespace(y=500))

    assert actions == []


@pytest.mark.parametrize(
    ("view_class", "action_name"),
    (
        (CertificatesView, "open_certificate"),
        (RequestsView, "show_status_dialog"),
        (EmployeesView, "edit_selected"),
    ),
)
def test_main_table_double_click_uses_row_under_pointer(view_class, action_name):
    """Действие выполняется для строки непосредственно под курсором."""
    actions: list[bool] = []
    selected: list[str] = []
    focused: list[str] = []
    view = SimpleNamespace(
        tree=SimpleNamespace(
            identify_row=lambda _y: "row-2",
            selection_set=selected.append,
            focus=focused.append,
        ),
        **{action_name: lambda: actions.append(True)},
    )

    view_class.on_double_click(view, SimpleNamespace(y=120))

    assert selected == ["row-2"]
    assert focused == ["row-2"]
    assert actions == [True]

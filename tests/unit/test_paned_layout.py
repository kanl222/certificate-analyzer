"""Регрессионные тесты раскладки списка и панели свойств."""

from types import SimpleNamespace

import pytest

from certificate_analyzer.presentation.gui.views.certificates_view import (
    CertificatesView,
)
from certificate_analyzer.presentation.gui.views.mchd_view import MchdView


class FakePanedWindow:
    """Минимальная модель Panedwindow с ограничением позиции его шириной."""

    def __init__(self) -> None:
        self.width = 1
        self.position = 0

    def winfo_width(self) -> int:
        return self.width

    def sashpos(self, _index: int, position: int) -> None:
        self.position = max(0, min(position, self.width - 1))


@pytest.mark.parametrize(
    ("resize_method", "apply_method"),
    (
        (
            CertificatesView._resize_content_pane,
            CertificatesView._apply_content_pane_layout,
        ),
        (MchdView._resize_content_pane, MchdView._apply_content_pane_layout),
    ),
)
def test_content_pane_waits_for_real_geometry(resize_method, apply_method):
    """Список не схлопывается, если первое событие пришло до расчёта геометрии."""
    pane = FakePanedWindow()
    idle_callbacks = []
    view = SimpleNamespace(
        _last_layout_width=0,
        _pane_layout_after=None,
        content_pane=pane,
        after_idle=lambda callback: idle_callbacks.append(callback) or "after-idle",
        after=lambda _delay, callback: idle_callbacks.append(callback) or "after-delay",
        after_cancel=lambda _callback_id: None,
    )
    view._apply_content_pane_layout = lambda: apply_method(view)
    event = SimpleNamespace(widget=view, width=1400)

    resize_method(view, event)
    pane.width = 1380
    for callback in idle_callbacks:
        callback()

    assert pane.position > 700
    assert pane.position < pane.width

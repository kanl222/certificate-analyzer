"""Тесты окна нормативных документов NormativeWindow."""

import os
from unittest.mock import MagicMock
import pytest


@pytest.mark.skipif(
    not os.environ.get("CERTIFICATE_ANALYZER_GUI_TEST"),
    reason="GUI-тест отключен без флага окружения",
)
def test_normative_window_lifecycle_and_scroll():
    """Проверяет создание, прокрутку и безопасное закрытие NormativeWindow без ошибок TclError."""
    import tkinter as tk
    from certificate_analyzer.presentation.gui.views.normative_view import (
        NormativeWindow,
    )

    root = tk.Tk()
    root.withdraw()
    try:
        norm_window = NormativeWindow(root)
        assert norm_window.window is not None
        assert norm_window.window.winfo_exists()

        # Имитируем прокрутку колесом мыши до закрытия
        event = MagicMock()
        event.delta = -120
        event.num = 0
        norm_window.window.event_generate("<MouseWheel>", delta=-120)

        # Закрываем окно
        norm_window._on_close()
        assert norm_window.window is None

        # Проверяем, что глобальное событие колеса мыши после закрытия не выбрасывает TclError
        root.event_generate("<MouseWheel>", delta=-120)
        root.update()
    finally:
        root.destroy()

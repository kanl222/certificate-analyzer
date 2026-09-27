"""Виджет отображения статусной карточки сертификатов и метрик."""

from typing import Any

from certificate_analyzer.presentation.gui.widgets.stat_card import StatCard



class StatusCard(StatCard):
    """Информационная карточка для отображения статуса и количества записей."""

    def __init__(
        self,
        parent: Any,
        title: str,
        value: int | str = 0,
        color: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Инициализирует статусную карточку.

        Args:
            parent: Родительский контейнер Tkinter.
            title: Заголовок статуса (например, «Истекающие», «Просроченные»).
            value: Числовое или текстовое значение счетчика.
            color: Цветовой акцент для значения (HEX или имя цвета).
            **kwargs: Дополнительные параметры для ttk.Frame.
        """
        super().__init__(parent, title=title, value=str(value), color=color, **kwargs)

    def update_count(self, count: int) -> None:
        """Обновляет значение счетчика карточки.

        Args:
            count: Новое числовое значение.
        """
        self.set_value(str(count))

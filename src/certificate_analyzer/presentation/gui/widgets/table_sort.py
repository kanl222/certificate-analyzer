"""Persistent sorting for tables whose rows are loaded in memory."""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from certificate_analyzer.presentation.gui.widgets.table_state import sort_heading_text


def sort_value(value, kind="text"):
    text = str(value or "").strip()
    if text in ("", "—", "Не найдена", "Не найдено", "Не найден"):
        return (0, "")
    if kind == "date":
        for pattern in (
            "%d.%m.%Y",
            "%d.%m.%Y %H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%H:%M:%S",
        ):
            try:
                return (1, datetime.strptime(text, pattern))
            except ValueError:
                continue
    elif kind == "number":
        try:
            number = Decimal(text)
            if number.is_finite():
                return (1, number)
        except InvalidOperation:
            pass
    return (2, text.casefold())


class TreeviewSorter:
    def __init__(self, tree, *, kinds=None):
        self.tree = tree
        self.kinds = kinds or {}
        self.column = None
        self.descending = False
        self.titles = {
            column: tree.heading(column, "text") for column in tree["columns"]
        }
        for column in self.titles:
            tree.heading(column, command=lambda column=column: self.toggle(column))

    def toggle(self, column):
        self.descending = not self.descending if self.column == column else False
        self.column = column
        self.apply()

    def apply(self):
        if self.column is None:
            return
        rows = sorted(
            self.tree.get_children(""),
            key=lambda row: sort_value(
                self.tree.set(row, self.column), self.kinds.get(self.column, "text")
            ),
            reverse=self.descending,
        )
        for index, row in enumerate(rows):
            self.tree.move(row, "", index)
        for column, title in self.titles.items():
            self.tree.heading(
                column,
                text=sort_heading_text(title, column == self.column, self.descending),
            )

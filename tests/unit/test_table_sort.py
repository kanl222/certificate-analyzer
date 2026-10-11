from certificate_analyzer.presentation.gui.widgets.table_sort import TreeviewSorter


class Table:
    def __init__(self, rows):
        self.rows = rows
        self.order = list(rows)
        self.headings = {key: {"text": key} for key in ("name", "date", "number")}

    def __getitem__(self, key):
        return tuple(self.headings)

    def heading(self, column, option=None, **kwargs):
        self.headings[column].update(kwargs)
        if option:
            return self.headings[column][option]

    def get_children(self, parent=""):
        return list(self.order)

    def set(self, row, column):
        return self.rows[row][column]

    def move(self, row, parent, index):
        self.order.remove(row)
        self.order.insert(index, row)


def test_heading_click_sorts_text_and_toggles_direction():
    table = Table({"first": {"name": "Яков"}, "second": {"name": "Анна"}})
    TreeviewSorter(table)
    table.heading("name", "command")()
    assert table.order == ["second", "first"]
    assert table.heading("name", "text") != "name"
    table.heading("name", "command")()
    assert table.order == ["first", "second"]
    assert set(table.rows) == set(table.order)


def test_date_sort_is_chronological_and_accepts_empty_values():
    table = Table(
        {
            "later": {"date": "01.01.2027"},
            "earlier": {"date": "31.12.2026"},
            "missing": {"date": "—"},
        }
    )
    TreeviewSorter(table, kinds={"date": "date"})
    table.heading("date", "command")()
    assert table.order == ["missing", "earlier", "later"]


def test_numeric_sort_and_reapply_after_refresh():
    table = Table(
        {"ten": {"number": "10"}, "two": {"number": "2"}, "expired": {"number": "-1"}}
    )
    sorter = TreeviewSorter(table, kinds={"number": "number"})
    table.heading("number", "command")()
    assert table.order == ["expired", "two", "ten"]
    table.order = ["ten", "expired", "two"]
    sorter.apply()
    assert table.order == ["expired", "two", "ten"]

"""Проверки корректного разделения параметров виджетов и геометрии Tkinter."""

import ast
from pathlib import Path


GUI_ROOT = Path(__file__).parents[2] / "src" / "certificate_analyzer" / "presentation" / "gui"


def test_widget_style_is_not_passed_to_geometry_managers() -> None:
    """Параметр ``style`` должен передаваться виджету, а не pack/grid/place."""
    violations: list[str] = []

    for path in GUI_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"pack", "grid", "place"}:
                continue
            if any(keyword.arg == "style" for keyword in node.keywords):
                violations.append(f"{path.relative_to(GUI_ROOT)}:{node.lineno}")

    assert not violations, "style передан менеджеру геометрии: " + ", ".join(violations)

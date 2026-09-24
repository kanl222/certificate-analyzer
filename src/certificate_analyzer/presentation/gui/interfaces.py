from typing import Any, Protocol


class ICertificateView(Protocol):
    """View interface for Certificate operations in MVP architecture."""

    def show_notification(self, message: str, type_: str = "info", duration: int = 4000) -> None:
        """Display a toast notification."""
        ...

    def show_message(self, title: str, message: str) -> None:
        """Display an informational popup."""
        ...

    def show_warning(self, title: str, message: str) -> None:
        """Display a warning popup."""
        ...

    def show_error(self, title: str, message: str) -> None:
        """Display an error popup."""
        ...

    def ask_yes_no(self, title: str, message: str) -> bool:
        """Ask user for confirmation."""
        ...

    def display_certificates(self, data_list: list[dict[str, Any]]) -> None:
        """Render certificate rows into the table/treeview."""
        ...

    def set_loaded_files(self, file_paths: list[str]) -> None:
        """Update file list in the sidebar."""
        ...

    def update_stats_view(self, total: int, expired: int, warning: int, normal: int) -> None:
        """Update statistics cards and status indicators."""
        ...

    def set_search_result_text(self, text: str) -> None:
        """Update search status label."""
        ...

    def get_search_query(self) -> str:
        """Return the current search query."""
        ...

    def clear_search_input(self) -> None:
        """Clear search entry."""
        ...

    def get_selected_rows(self) -> list[tuple[Any, dict[str, Any]]]:
        """Return currently selected rows in the table."""
        ...

    def remove_tree_items(self, item_ids: list[Any]) -> None:
        """Remove specified items from treeview."""
        ...

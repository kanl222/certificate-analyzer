"""Представления и диалоговые окна графического интерфейса."""

from certificate_analyzer.presentation.gui.views.audit_view import (
    AuditWindow,
)
from certificate_analyzer.presentation.gui.views.history_view import (
    NotificationHistory,
)
from certificate_analyzer.presentation.gui.views.mchd_view import MCHDTableWindow
from certificate_analyzer.presentation.gui.views.normative_view import (
    NormativeWindow,
)
from certificate_analyzer.presentation.gui.views.phonebook_view import (
    PhoneBookView,
)
from certificate_analyzer.presentation.gui.views.requests_view import (
    RequestsView,
)
from certificate_analyzer.presentation.gui.views.settings_view import (
    SettingsView,
)

__all__ = [
    "AuditWindow",
    "MCHDTableWindow",
    "NotificationHistory",
    "NormativeWindow",
    "PhoneBookView",
    "RequestsView",
    "SettingsView",
]

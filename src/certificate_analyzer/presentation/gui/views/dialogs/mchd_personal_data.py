"""Представление вкладки машиночитаемых доверенностей (МЧД) и диалоговые окна."""

from datetime import timezone
import os
import tkinter as tk
from tkinter import ttk
from typing import Any


from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    CARD_BG_COLOR,
    CARD_BORDER_COLOR,
    MCHD_COLOR,
    TEXT_COLOR,
    UI_FONT,
)


UTC = timezone.utc

class MchdPersonalDataWindow:
    """Окно карточки персональных данных и реквизитов МЧД."""

    def __init__(self, parent: tk.Widget, mchd: dict[str, Any]) -> None:
        """Инициализирует карточку доверенности.

        Args:
            parent: Родительский виджет.
            mchd: Словарь с атрибутами МЧД.
        """
        self.parent = parent
        self.mchd = mchd
        self.window: tk.Toplevel | None = None
        self._unbind_scroll = None
        self._create_window()

    def _create_window(self) -> None:
        """Создает Toplevel диалог просмотра реквизитов."""
        has_issuer = (
            self.mchd.get("issuer_org_name", "Не найдено") != "Не найдено"
            or self.mchd.get("issuer_person_fullname", "Не найдено")
            != "Не найдено"
        )
        width = 900 if has_issuer else 760
        height = 760 if has_issuer else 620

        self.window = tk.Toplevel(self.parent)
        file_name = os.path.basename(self.mchd.get("file_name", ""))
        self.window.title(f"Карточка МЧД — {file_name}")
        self.window.geometry(f"{width}x{height}")
        self.window.configure(bg=BG_COLOR)
        self.window.minsize(700, 550)

        self._setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Безопасно закрывает карточку и снимает биндинги мыши."""
        if self._unbind_scroll:
            self._unbind_scroll()
            self._unbind_scroll = None
        if self.window:
            self.window.destroy()
            self.window = None

    def _setup_ui(self) -> None:
        """Создает скроллируемые карточки с реквизитами МЧД."""
        if not self.window:
            return

        main_frame = tk.Frame(self.window, bg=BG_COLOR, padx=16, pady=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = tk.Frame(main_frame, bg=BG_COLOR)
        title_frame.pack(fill=tk.X, pady=(0, 15))

        title_text_frame = tk.Frame(title_frame, bg=BG_COLOR)
        title_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            title_text_frame,
            text="Карточка машиночитаемой доверенности",
            font=(UI_FONT, 16, "bold"),
            bg=BG_COLOR,
            fg=MCHD_COLOR,
        ).pack(anchor=tk.W)

        file_path = self.mchd.get("file_name", "—")
        tk.Label(
            title_text_frame,
            text=f"Файл: {os.path.basename(file_path)}",
            font=(UI_FONT, 9),
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
        ).pack(anchor=tk.W)

        canvas_frame = tk.Frame(main_frame, bg=BG_COLOR)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=canvas.yview
        )
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind(
            "<Configure>",
            lambda _: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def add_info_card(
            title: str, items: list[tuple[str, Any]]
        ) -> None:
            card = tk.Frame(
                scrollable_frame,
                bg=CARD_BG_COLOR,
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground=CARD_BORDER_COLOR,
            )
            card.pack(fill=tk.X, pady=(0, 12))
            hdr = tk.Frame(card, bg=MCHD_COLOR, height=36)
            hdr.pack(fill=tk.X)
            hdr.pack_propagate(False)

            tk.Label(
                hdr,
                text=title,
                font=(UI_FONT, 10, "bold"),
                fg="white",
                bg=MCHD_COLOR,
            ).pack(side=tk.LEFT, padx=12, pady=6)

            body = tk.Frame(card, bg=CARD_BG_COLOR, padx=12, pady=8)
            body.pack(fill=tk.X)

            for label, value in items:
                row = tk.Frame(body, bg=CARD_BG_COLOR)
                row.pack(fill=tk.X, pady=3)
                tk.Label(
                    row,
                    text=f"{label}:",
                    font=(UI_FONT, 9, "bold"),
                    fg=MCHD_COLOR,
                    bg=CARD_BG_COLOR,
                    width=22,
                    anchor="w",
                ).pack(side=tk.LEFT, padx=(0, 8))

                val_str = str(value) if value else "—"
                lbl_val = tk.Label(
                    row,
                    text=val_str,
                    font=(UI_FONT, 9),
                    bg=CARD_BG_COLOR,
                    fg=TEXT_COLOR,
                    anchor="w",
                    justify="left",
                )
                lbl_val.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 1. Основные реквизиты
        add_info_card(
            "Реквизиты документа",
            [
                (
                    "Номер доверенности",
                    self.mchd.get("doc_number", "Не найдено"),
                ),
                ("Дата выдачи", self.mchd.get("issue_date", "Не найдена")),
                (
                    "Срок действия",
                    self.mchd.get("expiry_date", "Не найдена"),
                ),
                ("Статус срока", self.mchd.get("status", "Не определен")),
                ("Проверка подлинности", "Не проверена (подпись, доверие, отзыв)"),
            ],
        )

        # 2. Доверитель (организация)
        org_name = self.mchd.get(
            "issuer_org_name", self.mchd.get("principal_name", "Не найдено")
        )
        org_inn = self.mchd.get(
            "issuer_org_inn", self.mchd.get("principal_inn", "Не найден")
        )
        add_info_card(
            "Сведения о доверителе",
            [
                ("Наименование организации", org_name),
                ("ИНН организации", org_inn),
                ("КПП", self.mchd.get("issuer_org_kpp", "—")),
                ("ОГРН", self.mchd.get("issuer_org_ogrn", "—")),
            ],
        )

        # 3. Представитель (физическое лицо)
        rep_name = self.mchd.get(
            "full_name", self.mchd.get("representative_fio", "Не найдено")
        )
        rep_inn = self.mchd.get(
            "inn", self.mchd.get("representative_inn", "Не найден")
        )
        rep_snils = self.mchd.get(
            "snils", self.mchd.get("representative_snils", "Не найден")
        )
        add_info_card(
            "Сведения о представителе",
            [
                ("ФИО представителя", rep_name),
                ("ИНН представителя", rep_inn),
                ("СНИЛС представителя", rep_snils),
                (
                    "Дата рождения",
                    self.mchd.get("representative_birthdate", "—"),
                ),
            ],
        )

        # 4. Полномочия
        codes = self.mchd.get("authority_codes", [])
        names = self.mchd.get("authority_names", [])
        auth_items = []
        if codes:
            for i, c in enumerate(codes):
                c_name = names[i] if i < len(names) and names[i] else ""
                val = f"{c} ({c_name})" if c_name else c
                auth_items.append((f"Полномочие #{i + 1}", val))
        else:
            auth_items.append(("Полномочия", "Нет кодов"))
        add_info_card("Полномочия", auth_items)

        # Кнопки управления
        btn_bar = ttk.Frame(main_frame)
        btn_bar.pack(fill=tk.X, pady=(12, 0))

        ttk.Button(
            btn_bar, text="Закрыть", command=self._on_close, style="Accent.TButton"
        ).pack(side="right")

        # Безопасный скроллинг мыши
        def _on_mousewheel(event: tk.Event) -> None:
            try:
                if not canvas.winfo_exists():
                    return
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
                elif getattr(event, "delta", 0):
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except (tk.TclError, RuntimeError):
                pass

        def _bind(_event=None):
            try:
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
                canvas.bind_all("<Button-4>", _on_mousewheel)
                canvas.bind_all("<Button-5>", _on_mousewheel)
            except (tk.TclError, RuntimeError):
                pass

        def _unbind(_event=None):
            try:
                canvas.unbind_all("<MouseWheel>")
                canvas.unbind_all("<Button-4>")
                canvas.unbind_all("<Button-5>")
            except (tk.TclError, RuntimeError):
                pass

        self._unbind_scroll = _unbind
        canvas.bind("<Enter>", _bind)
        canvas.bind("<Leave>", _unbind)
        scrollable_frame.bind("<Enter>", _bind)
        scrollable_frame.bind("<Leave>", _unbind)
        self.window.bind("<MouseWheel>", _on_mousewheel)


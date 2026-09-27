"""Окно отображения нормативных документов по электронной подписи и МЧД."""

import tkinter as tk
import webbrowser
from tkinter import ttk
from typing import Any

from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    BUTTON_COLOR,
    UI_FONT,
)


class NormativeWindow:
    """Диалоговое окно со справочником нормативных документов и стандартов."""

    def __init__(self, parent: Any) -> None:
        """Инициализирует и открывает окно нормативных документов.

        Args:
            parent: Родительский виджет Tkinter.
        """
        self.parent = parent
        self.window: tk.Toplevel | None = None
        self._unbind_mousewheel = None
        self._create_window()

    def _create_window(self) -> None:
        """Создает Toplevel окно или переводит фокус на существующее."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Нормативные документы")
        self.window.geometry("750x550")
        self.window.configure(bg=BG_COLOR)
        self.setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        """Безопасно закрывает окно и освобождает глобальные обработчики событий."""
        if self._unbind_mousewheel:
            self._unbind_mousewheel()
            self._unbind_mousewheel = None

        if self.window:
            try:
                self.window.unbind("<MouseWheel>")
                self.window.unbind("<Button-4>")
                self.window.unbind("<Button-5>")
            except (tk.TclError, RuntimeError):
                pass
            self.window.destroy()
            self.window = None

    def setup_ui(self) -> None:
        """Формирует интерфейс окна нормативных документов со скроллингом."""
        if not self.window:
            return

        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            frame,
            text="Нормативные документы по электронной подписи и МЧД",
            font=(UI_FONT, 14, "bold"),
        ).pack(pady=(0, 20))
        canvas_frame = ttk.Frame(frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=canvas.yview
        )
        scrollable_frame = ttk.Frame(canvas, style="TFrame")
        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        normative_items = [
            (
                "ФЕДЕРАЛЬНЫЙ ЗАКОН № 63-ФЗ от 06.04.2011 'Об электронной подписи'",
                "http://www.consultant.ru/document/cons_doc_LAW_112701/",
                "Основной закон об электронной подписи",
            ),
            (
                "ФЕДЕРАЛЬНЫЙ ЗАКОН № 152-ФЗ от 27.07.2006 'О персональных данных'",
                "http://www.consultant.ru/document/cons_doc_LAW_61801/",
                "Закон о защите персональных данных",
            ),
            (
                "ПРИКАЗ МИНЦИФРЫ РОССИИ № 857 от 18.10.2021 'Об утверждении формата МЧД'",
                "http://publication.pravo.gov.ru/Document/View/0001202112200010",
                "Формат машиночитаемой доверенности",
            ),
            (
                "ПОСТАНОВЛЕНИЕ ПРАВИТЕЛЬСТВА РФ № 223 от 21.02.2022 'О порядке применения МЧД'",
                "http://publication.pravo.gov.ru/Document/View/0001202202240017",
                "Порядок применения машиночитаемой доверенности",
            ),
            (
                "ФЕДЕРАЛЬНЫЙ ЗАКОН № 149-ФЗ от 27.07.2006 'Об информации и защите информации'",
                "http://www.consultant.ru/document/cons_doc_LAW_61798/",
                "Закон об информации",
            ),
            (
                "ГОСТ Р 34.10-2012 - Процессы формирования и проверки ЭП",
                "https://protect.gost.ru/document.aspx?control=7&id=190331",
                "Стандарт электронной подписи",
            ),
            (
                "ГОСТ Р 34.11-2012 - Функция хэширования",
                "https://protect.gost.ru/document.aspx?control=7&id=190378",
                "Стандарт хэширования",
            ),
            (
                "Приказ ФНС России от 30.04.2021 № ЕД-7-26/445@ - Формат МЧД для ФНС",
                "https://www.nalog.gov.ru/rn77/about_fts/docs/11631597/",
                "Формат МЧД для налоговой службы",
            ),
        ]
        link_style = {
            "font": (UI_FONT, 10, "underline"),
            "foreground": BUTTON_COLOR,
            "cursor": "hand2",
            "bg": BG_COLOR,
            "borderwidth": 0,
            "anchor": "w",
            "justify": "left",
        }
        for title, url, description in normative_items:
            doc_frame = ttk.Frame(scrollable_frame, style="Card.TFrame", padding=10)
            doc_frame.pack(fill=tk.X, pady=5)
            link_btn = tk.Button(
                doc_frame,
                text=title,
                command=lambda u=url: webbrowser.open(u),
                **link_style,
            )
            link_btn.pack(anchor=tk.W)
            desc_label = ttk.Label(
                doc_frame,
                text=description,
                font=(UI_FONT, 9),
                foreground=ACCENT_COLOR,
            )
            desc_label.pack(anchor=tk.W, pady=(2, 0))
        info_label = ttk.Label(
            scrollable_frame,
            text="\nДля открытия документа нажмите на название выше.\nСсылки открываются в браузере по умолчанию.",
            font=(UI_FONT, 9, "italic"),
            foreground=ACCENT_COLOR,
        )
        info_label.pack(pady=(15, 5))
        ttk.Button(
            frame, text="Закрыть", command=self._on_close, style="Accent.TButton"
        ).pack(pady=(10, 0))

        def _on_mousewheel(event: tk.Event) -> None:
            """Прокручивает содержимое холста при событии колеса мыши."""
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

        def _bind_mousewheel(_event: tk.Event | None = None) -> None:
            """Активирует прокрутку колесом мыши при наведении курсора на холст."""
            try:
                canvas.bind_all("<MouseWheel>", _on_mousewheel)
                canvas.bind_all("<Button-4>", _on_mousewheel)
                canvas.bind_all("<Button-5>", _on_mousewheel)
            except (tk.TclError, RuntimeError):
                pass

        def _unbind_mousewheel(_event: tk.Event | None = None) -> None:
            """Деактивирует глобальные привязки прокрутки колесом мыши."""
            try:
                canvas.unbind_all("<MouseWheel>")
                canvas.unbind_all("<Button-4>")
                canvas.unbind_all("<Button-5>")
            except (tk.TclError, RuntimeError):
                pass

        self._unbind_mousewheel = _unbind_mousewheel

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        scrollable_frame.bind("<Enter>", _bind_mousewheel)
        scrollable_frame.bind("<Leave>", _unbind_mousewheel)
        self.window.bind("<MouseWheel>", _on_mousewheel)
        self.window.bind("<Button-4>", _on_mousewheel)
        self.window.bind("<Button-5>", _on_mousewheel)

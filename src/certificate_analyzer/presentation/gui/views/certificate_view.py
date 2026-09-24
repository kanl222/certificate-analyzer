import tkinter as tk
from datetime import UTC, datetime, timezone
from tkinter import messagebox, ttk

from tkcalendar import DateEntry

from certificate_analyzer.presentation.gui.styles import (
    ACCENT_COLOR,
    BG_COLOR,
    BUTTON_COLOR,
    EXPIRED_COLOR,
    EXPIRED_TEXT,
    NORMAL_COLOR,
    NORMAL_TEXT,
    UI_FONT,
    WARNING_COLOR,
    WARNING_TEXT,
)


class CertificateView:
    def on_chart_type_change(self, event=None):
        chart_map = {
            "Круговая": "pie",
            "Столбчатая": "bar",
            "Линейная": "line",
            "С областями": "area",
            "Кольцевая": "doughnut",
            "Точечная": "scatter",
            "Пузырьковая": "bubble",
            "Гистограмма с накоплением": "stacked_bar",
        }
        self.chart_type = chart_map.get(self.chart_type_var.get(), "pie")
        self.update_stats()

    def update_calendar_colors(self):
        if not hasattr(self, "cal") or self.cal is None:
            return
        try:
            self.clear_calendar_events()
            current_date = self.cal.get_date()
            current = datetime.strptime(current_date, "%d.%m.%Y")
            current_month = current.month
            current_year = current.year
            day_priority = {}
            for cert in self.cert_data_cache:
                try:
                    cert_date_str = cert.get("valid_to", "")
                    if cert_date_str and cert_date_str not in (
                        "—",
                        "Не найден",
                        "Ошибка",
                    ):
                        cert_date = datetime.strptime(cert_date_str, "%d.%m.%Y")
                        if (
                            cert_date.month == current_month
                            and cert_date.year == current_year
                        ):
                            day = cert_date.day
                            status = cert.get("status", "")
                            if status == "Просрочен":
                                priority = 3
                            elif "Истекает" in status:
                                priority = 2
                            else:
                                priority = 1
                            if day not in day_priority or day_priority[day] < priority:
                                day_priority[day] = priority
                except Exception:
                    continue
            for day, priority in day_priority.items():
                date_obj = datetime(current_year, current_month, day, tzinfo=UTC).date()
                if priority == 3:
                    self.cal.calevent_create(date_obj, "Просрочен", "expired")
                    self.cal.tag_config(
                        "expired", background=EXPIRED_COLOR, foreground=EXPIRED_TEXT
                    )
                elif priority == 2:
                    self.cal.calevent_create(date_obj, "Истекает", "warning")
                    self.cal.tag_config(
                        "warning", background=WARNING_COLOR, foreground=WARNING_TEXT
                    )
                elif priority == 1:
                    self.cal.calevent_create(date_obj, "Активен", "normal")
                    self.cal.tag_config(
                        "normal", background=NORMAL_COLOR, foreground=NORMAL_TEXT
                    )
            today = datetime.now(UTC).date()
            if today.month == current_month and today.year == current_year:
                self.cal.calevent_create(today, "Сегодня", "today")
                self.cal.tag_config("today", background="#3498db", foreground="white")
        except Exception as e:
            print(f"Ошибка при обновлении календаря: {e}")

    def clear_calendar_events(self):
        if not hasattr(self, "cal") or self.cal is None:
            return
        try:
            self.cal.calevent_remove("all")
        except Exception:
            pass

    def on_month_change(self, event):
        self.update_calendar_colors()

    def on_window_resize(self, event):
        if event.widget == self.root:
            window_width = self.root.winfo_width()
            base_width = 1600
            scale_factor = max(0.7, min(1.5, window_width / base_width))
            base_widths = [50, 150, 85, 85, 160, 110, 110, 85, 110, 120, 110]
            scaled_widths = [int(width * scale_factor) for width in base_widths]
            for col, width in zip(self.columns, scaled_widths):
                self.tree.column(col, width=max(40, width))

    def show_date_filter(self):
        filter_window = tk.Toplevel(self.root)
        filter_window.title("Фильтр по дате")
        filter_window.geometry("450x300")
        filter_window.configure(bg=BG_COLOR)
        filter_window.resizable(False, False)
        frame = ttk.Frame(filter_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(
            frame, text="Фильтр по дате окончания", font=(UI_FONT, 12, "bold")
        ).pack(pady=(0, 20))
        from_frame = ttk.Frame(frame)
        from_frame.pack(fill=tk.X, pady=5)
        ttk.Label(from_frame, text="С даты:", width=10).pack(side=tk.LEFT)
        from_date = DateEntry(
            from_frame,
            width=12,
            background=BUTTON_COLOR,
            foreground="white",
            borderwidth=2,
            date_pattern="dd.mm.yyyy",
        )
        from_date.pack(side=tk.LEFT, padx=5)
        to_frame = ttk.Frame(frame)
        to_frame.pack(fill=tk.X, pady=5)
        ttk.Label(to_frame, text="По дату:", width=10).pack(side=tk.LEFT)
        to_date = DateEntry(
            to_frame,
            width=12,
            background=BUTTON_COLOR,
            foreground="white",
            borderwidth=2,
            date_pattern="dd.mm.yyyy",
        )
        to_date.pack(side=tk.LEFT, padx=5)
        ttk.Label(
            frame,
            text="Будут показаны документы,\nсрок действия которых попадает в указанный диапазон",
            font=(UI_FONT, 9, "italic"),
            foreground=ACCENT_COLOR,
            justify=tk.CENTER,
        ).pack(pady=20)
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)

        def apply_filter():
            self.date_from = from_date.get_date()
            self.date_to = to_date.get_date()
            self.date_filter_active = True
            self.apply_date_filter()
            filter_window.destroy()

        def clear_filter():
            self.date_filter_active = False
            self.date_from = None
            self.date_to = None
            self.refresh_current_view()
            filter_window.destroy()

        ttk.Button(
            btn_frame, text="Применить", command=apply_filter, style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame, text="Сбросить", command=clear_filter, style="Accent.TButton"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            btn_frame,
            text="Отмена",
            command=filter_window.destroy,
            style="Accent.TButton",
        ).pack(side=tk.RIGHT, padx=5)

    def apply_date_filter(self):
        if hasattr(self, "certificate_presenter") and self.certificate_presenter:
            self.certificate_presenter.apply_date_filter(self.date_from, self.date_to)
        else:
            if not self.date_filter_active or not self.date_from or not self.date_to:
                return
            filtered_data = []
            for item in self.cert_data_cache:
                try:
                    date_str = item.get("valid_to", "")
                    if date_str and date_str not in ("—", "Не найден", "Ошибка"):
                        item_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                        if self.date_from <= item_date <= self.date_to:
                            filtered_data.append(item)
                except Exception:
                    continue
            for row in self.tree.get_children():
                self.tree.delete(row)
            self._insert_certificates_into_tree(filtered_data)
            self.search_result_label.config(text=f"Фильтр: {len(filtered_data)} записей")

    def on_date_select(self, event=None):
        date_str = self.cal.get_date()
        try:
            selected_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            docs_on_date = []
            for item in self.cert_data_cache:
                try:
                    date_field = item.get("valid_to", "")
                    if date_field and date_field not in ("—", "Не найден", "Ошибка"):
                        item_date = datetime.strptime(date_field, "%d.%m.%Y").date()
                        if item_date == selected_date:
                            docs_on_date.append(item)
                except Exception:
                    continue
            if docs_on_date:
                doc_list = []
                for doc in docs_on_date:
                    name = doc.get("subject_cn", "Неизвестно")
                    status = doc.get("status", "")
                    doc_list.append(f"- {name} ({status})")
                msg = f"Сертификаты, истекающие {date_str}:\n" + "\n".join(doc_list)
                messagebox.showinfo(f"Сертификаты на {date_str}", msg)
            else:
                messagebox.showinfo(
                    f"Дата {date_str}", "На эту дату нет истекающих сертификатов"
                )
        except Exception as e:
            print(f"Ошибка при обработке даты: {e}")

    def show_today(self):
        today = datetime.now(UTC).date()
        self.cal.selection_set(today)
        self.cal.see(today)
        self.update_calendar_colors()

    def prev_month(self):
        self.cal._prev_month()
        self.update_calendar_colors()

    def next_month(self):
        self.cal._next_month()
        self.update_calendar_colors()

    def _update_stats_legacy(self):
        current_data = self.cert_data_cache

        total = len(current_data)
        expired = 0
        warning = 0
        normal = 0

        for doc in current_data:
            status = doc.get("status", "")
            if status == "Просрочен":
                expired += 1
            elif "Истекает" in status:
                warning += 1
            else:
                normal += 1

        self.card_total.config(text=str(total))

        if total > 0:
            normal_percent = (normal / total) * 100
            warning_percent = (warning / total) * 100
            expired_percent = (expired / total) * 100
        else:
            normal_percent = warning_percent = expired_percent = 0

        self.card_normal.config(text=f"{normal} ({normal_percent:.1f}%)")
        self.card_warning.config(text=f"{warning} ({warning_percent:.1f}%)")
        self.card_expired.config(text=f"{expired} ({expired_percent:.1f}%)")

        self.figure_status.clear()

        labels = []
        sizes = []
        excel_colors = []

        EXCEL_GREEN = "#81c784"
        EXCEL_YELLOW = "#ffd54f"
        EXCEL_RED = "#e57373"
        EXCEL_BLUE = "#4472C4"

        if normal > 0:
            labels.append(f"Активные ({normal})")
            sizes.append(normal)
            excel_colors.append(EXCEL_GREEN)
        if warning > 0:
            labels.append(f"Истекают ({warning})")
            sizes.append(warning)
            excel_colors.append(EXCEL_YELLOW)
        if expired > 0:
            labels.append(f"Просрочены ({expired})")
            sizes.append(expired)
            excel_colors.append(EXCEL_RED)

        if sizes:
            try:
                chart_type = getattr(self, "chart_type", "pie")

                if chart_type == "pie":
                    self.ax_status = self.figure_status.add_subplot(111)
                    explode = [0.05] * len(sizes)
                    wedges, texts, autotexts = self.ax_status.pie(
                        sizes,
                        labels=labels,
                        colors=excel_colors,
                        autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
                        startangle=90,
                        explode=explode,
                        textprops={"fontsize": 9, "fontweight": "bold"},
                        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
                    )
                    for autotext in autotexts:
                        autotext.set_fontsize(9)
                        autotext.set_fontweight("bold")
                        autotext.set_color("#333333")
                    self.ax_status.set_title(
                        "Статус сертификатов", fontsize=11, fontweight="bold", pad=10
                    )

                elif chart_type == "bar":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    bars = self.ax_status.bar(
                        x,
                        sizes,
                        color=excel_colors,
                        width=0.6,
                        edgecolor="white",
                        linewidth=1,
                    )
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel("Количество", fontsize=9)
                    self.ax_status.set_title(
                        "Статус сертификатов", fontsize=11, fontweight="bold", pad=10
                    )
                    self.ax_status.spines["top"].set_visible(False)
                    self.ax_status.spines["right"].set_visible(False)

                    for bar, size in zip(bars, sizes):
                        height = bar.get_height()
                        self.ax_status.text(
                            bar.get_x() + bar.get_width() / 2.0,
                            height + 0.1,
                            str(size),
                            ha="center",
                            va="bottom",
                            fontsize=9,
                            fontweight="bold",
                        )
                    self.ax_status.set_ylim(0, max(sizes) * 1.15)

                elif chart_type == "line":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    self.ax_status.plot(
                        x,
                        sizes,
                        marker="o",
                        linewidth=2.5,
                        markersize=8,
                        color=EXCEL_BLUE,
                        markerfacecolor="white",
                        markeredgewidth=2,
                    )
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel("Количество", fontsize=9)
                    self.ax_status.set_title(
                        "Статус сертификатов", fontsize=11, fontweight="bold", pad=10
                    )
                    self.ax_status.spines["top"].set_visible(False)
                    self.ax_status.spines["right"].set_visible(False)
                    self.ax_status.set_ylim(0, max(sizes) * 1.15)

                    for i, size in enumerate(sizes):
                        self.ax_status.annotate(
                            str(size),
                            (i, size),
                            textcoords="offset points",
                            xytext=(0, 10),
                            ha="center",
                            fontsize=9,
                            fontweight="bold",
                        )

                elif chart_type == "area":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    self.ax_status.fill_between(x, sizes, alpha=0.4, color=EXCEL_BLUE)
                    self.ax_status.plot(
                        x,
                        sizes,
                        marker="o",
                        linewidth=2.5,
                        markersize=6,
                        color=EXCEL_BLUE,
                    )
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel("Количество", fontsize=9)
                    self.ax_status.set_title(
                        "Статус сертификатов", fontsize=11, fontweight="bold", pad=10
                    )
                    self.ax_status.spines["top"].set_visible(False)
                    self.ax_status.spines["right"].set_visible(False)
                    self.ax_status.set_ylim(0, max(sizes) * 1.15)

                    for i, size in enumerate(sizes):
                        self.ax_status.text(
                            i,
                            size + 0.1,
                            str(size),
                            ha="center",
                            fontsize=9,
                            fontweight="bold",
                        )

                elif chart_type == "doughnut":
                    self.ax_status = self.figure_status.add_subplot(111)
                    _, _, autotexts = self.ax_status.pie(
                        sizes,
                        labels=labels,
                        colors=excel_colors,
                        autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
                        startangle=90,
                        wedgeprops={
                            "edgecolor": "white",
                            "linewidth": 1.5,
                            "width": 0.5,
                        },
                        textprops={"fontsize": 9, "fontweight": "bold"},
                    )
                    for autotext in autotexts:
                        autotext.set_fontsize(9)
                        autotext.set_fontweight("bold")
                        autotext.set_color("#333333")
                    self.ax_status.set_title(
                        "Статус сертификатов", fontsize=11, fontweight="bold", pad=10
                    )

                elif chart_type == "scatter":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    point_sizes = [max(s * 60, 120) for s in sizes]
                    self.ax_status.scatter(
                        x,
                        sizes,
                        s=point_sizes,
                        c=excel_colors,
                        alpha=0.8,
                        edgecolors="white",
                        linewidth=1.5,
                    )
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel("Количество", fontsize=9)
                    self.ax_status.set_title(
                        "Статус сертификатов", fontsize=11, fontweight="bold", pad=10
                    )
                    self.ax_status.spines["top"].set_visible(False)
                    self.ax_status.spines["right"].set_visible(False)
                    self.ax_status.set_ylim(0, max(sizes) * 1.2)

                    for i, (xi, yi) in enumerate(zip(x, sizes)):
                        self.ax_status.annotate(
                            str(yi),
                            (xi, yi),
                            textcoords="offset points",
                            xytext=(0, 12),
                            ha="center",
                            fontsize=9,
                            fontweight="bold",
                        )

                elif chart_type == "bubble":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    bubble_sizes = [max(s * 150, 250) for s in sizes]
                    self.ax_status.scatter(
                        x,
                        sizes,
                        s=bubble_sizes,
                        c=excel_colors,
                        alpha=0.7,
                        edgecolors="white",
                        linewidth=1.5,
                    )
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel("Количество", fontsize=9)
                    self.ax_status.set_title(
                        "Статус сертификатов", fontsize=11, fontweight="bold", pad=10
                    )
                    self.ax_status.spines["top"].set_visible(False)
                    self.ax_status.spines["right"].set_visible(False)
                    self.ax_status.set_ylim(0, max(sizes) * 1.25)

                    for i, (xi, yi) in enumerate(zip(x, sizes)):
                        self.ax_status.annotate(
                            str(yi),
                            (xi, yi),
                            textcoords="offset points",
                            xytext=(0, 15),
                            ha="center",
                            fontsize=9,
                            fontweight="bold",
                        )

                elif chart_type == "stacked_bar":
                    self.ax_status = self.figure_status.add_subplot(111)
                    bottom = 0
                    bar_width = 0.5
                    for i, (size, color, label) in enumerate(
                        zip(sizes, excel_colors, labels)
                    ):
                        bar = self.ax_status.bar(
                            0,
                            size,
                            bottom=bottom,
                            label=label,
                            color=color,
                            width=bar_width,
                            edgecolor="white",
                            linewidth=1,
                        )
                        if size > 0:
                            self.ax_status.text(
                                0,
                                bottom + size / 2,
                                str(size),
                                ha="center",
                                va="center",
                                fontsize=10,
                                fontweight="bold",
                                color="#333333",
                            )
                        bottom += size
                    self.ax_status.set_xticks([0])
                    self.ax_status.set_xticklabels(["Всего"], fontsize=9)
                    self.ax_status.set_ylabel("Количество", fontsize=9)
                    self.ax_status.set_title(
                        "Статус сертификатов", fontsize=11, fontweight="bold", pad=10
                    )
                    self.ax_status.spines["top"].set_visible(False)
                    self.ax_status.spines["right"].set_visible(False)
                    self.ax_status.set_xlim(-0.5, 0.5)
                    self.ax_status.set_ylim(0, sum(sizes) * 1.1)
                    self.ax_status.legend(
                        loc="upper right", fontsize=8, frameon=True, fancybox=False
                    )

                else:
                    self.ax_status = self.figure_status.add_subplot(111)
                    self.ax_status.text(
                        0.5,
                        0.5,
                        "Выберите тип диаграммы",
                        ha="center",
                        va="center",
                        fontsize=10,
                    )

            except Exception as e:
                print(f"Ошибка построения диаграммы: {e}")
                self.ax_status = self.figure_status.add_subplot(111)
                self.ax_status.text(
                    0.5, 0.5, "Ошибка", ha="center", va="center", fontsize=10
                )
        else:
            self.ax_status = self.figure_status.add_subplot(111)
            self.ax_status.text(
                0.5, 0.5, "Нет данных", ha="center", va="center", fontsize=10
            )
            self.ax_status.set_title(
                "Статус сертификатов", fontsize=11, fontweight="bold", pad=10
            )

        try:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                self.figure_status.tight_layout(pad=1.5)
        except Exception:
            pass

        self.canvas_status.draw()
        self.update_calendar_colors()

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID
import os
import pyperclip
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import sys
import threading
import json
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import matplotlib
import pywintypes
import xml.etree.ElementTree as ET
import subprocess
import re
from xml.dom import minidom
import calendar
import uuid
import webbrowser
import docx
from docx import Document

matplotlib.use('Agg')

from collections import Counter

try:
    from tkcalendar import Calendar, DateEntry
except ImportError:
    messagebox.showerror("Ошибка", "Установите tkcalendar: pip install tkcalendar")
    sys.exit(1)

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:
    from win10toast import ToastNotifier
    TOAST_AVAILABLE = True
except ImportError:
    TOAST_AVAILABLE = False

try:
    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
    PDF_FONT = 'Arial'
except:
    try:
        pdfmetrics.registerFont(TTFont('Arial', 'DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('Arial-Bold', 'DejaVuSans-Bold.ttf'))
        PDF_FONT = 'Arial'
    except:
        PDF_FONT = 'Helvetica'

BG_COLOR = "#f0f2f5"
HEADER_COLOR = "#ffffff"
TEXT_COLOR = "#2c3e50"
ACCENT_COLOR = "#6c5ce7"
BUTTON_COLOR = "#6c5ce7"
BUTTON_HOVER = "#5b4bc4"

EXPIRED_COLOR = "#e57373"
WARNING_COLOR = "#ffd54f"
NORMAL_COLOR = "#81c784"
EXPIRED_TEXT = "#721c24"
WARNING_TEXT = "#856404"
NORMAL_TEXT = "#155724"

GRAPH_EXPIRED = "#f5c6cb"
GRAPH_WARNING = "#ffeeba"
GRAPH_NORMAL = "#27ae60"
SIDEBAR_COLOR = "#2c3e50"
SIDEBAR_TEXT_COLOR = "#ecf0f1"
CARD_BG_COLOR = "#ffffff"
CARD_BORDER_COLOR = "#e1e8ed"
CARD_TITLE_COLOR = "#7f8c8d"
CARD_VALUE_COLOR = "#2c3e50"
MCHD_COLOR = "#9b59b6"
MCHD_LIGHT_COLOR = "#f3e5f5"

CAL_EXPIRED_BG = "#e57373"
CAL_EXPIRED_FG = "#e57373"
CAL_WARNING_BG = "#ffd54f"
CAL_WARNING_FG = "#ffd54f"
CAL_NORMAL_BG = "#27ae60"
CAL_NORMAL_FG = "#ffffff"
CAL_TODAY_BG = "#155724"
CAL_TODAY_FG = "#ffffff"

SERVICE_NAME = "CertificateAnalyzerService"
SERVICE_DISPLAY_NAME = "Анализатор сертификатов и МЧД"
CHECK_INTERVAL = 604800
EXPORT_FOLDER = os.path.join(os.path.expanduser("~"), "CertificateReports")
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "cert_analyzer_config.json")

if not os.path.exists(EXPORT_FOLDER):
    os.makedirs(EXPORT_FOLDER)


def load_config():
    default_config = {
        "📁 Сотрудники": os.path.join(os.path.expanduser("~"), "Certs"),
        "📁 Руководство": os.path.join(os.path.expanduser("~"), "ImportantCerts")
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                for key in default_config:
                    if key in saved_config and os.path.exists(saved_config[key]):
                        default_config[key] = saved_config[key]
        except:
            pass
    return default_config


def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        return True
    except:
        return False


DEFAULT_FOLDERS = load_config()


class PhoneBook:
    def __init__(self):
        self.data = []
        self.index_name = {}
        self.index_department = {}
        self.index_cabinet = {}

    def load_from_docx(self, file_path):
        self.data = []
        self.index_name = {}
        self.index_department = {}
        self.index_cabinet = {}

        try:
            doc = Document(file_path)

            for table in doc.tables:
                for row in table.rows:
                    cells = row.cells
                    if len(cells) >= 3:
                        должность = self._clean_text(cells[0].text) if len(cells) > 0 else ''
                        фио = self._clean_text(cells[1].text) if len(cells) > 1 else ''
                        кабинет = self._clean_text(cells[2].text) if len(cells) > 2 else ''

                        телефон = ''

                        if len(cells) > 3:
                            phone_part = self._clean_text(cells[3].text)
                            if phone_part and phone_part not in ['-', '—', '####', '#',
                                                                 ''] and not phone_part.startswith('#'):
                                if not any(x in phone_part.lower() for x in ['@', 'mail', 'http']):
                                    телефон = phone_part

                        if len(cells) > 4:
                            phone_part = self._clean_text(cells[4].text)
                            if phone_part and phone_part not in ['-', '—', '####', '#',
                                                                 ''] and not phone_part.startswith('#'):
                                if not any(x in phone_part.lower() for x in ['@', 'mail', 'http']):
                                    if телефон:
                                        телефон += ', ' + phone_part
                                    else:
                                        телефон = phone_part

                        if len(cells) > 5:
                            phone_part = self._clean_text(cells[5].text)
                            if phone_part and phone_part not in ['-', '—', '####', '#',
                                                                 ''] and not phone_part.startswith('#'):
                                if not any(x in phone_part.lower() for x in ['@', 'mail', 'http']):
                                    if телефон:
                                        телефон += ', ' + phone_part
                                    else:
                                        телефон = phone_part

                        name = фио
                        department = должность
                        cabinet = self._normalize_cabinet(кабинет)

                        if name or department or cabinet:
                            if not телефон:
                                телефон = '—'

                            if name and name != '—' and any(x in name.lower() for x in ['@', 'mail', 'http']):
                                name = '—'
                            if department and department != '—' and any(
                                    x in department.lower() for x in ['@', 'mail', 'http']):
                                department = '—'

                            record = {
                                'name': name if name else '—',
                                'department': department if department else '—',
                                'cabinet': cabinet if cabinet else '—',
                                'phone': телефон
                            }
                            self.data.append(record)

                            if name and name != '—' and len(name) > 2:
                                name_lower = name.lower()
                                if name_lower not in self.index_name:
                                    self.index_name[name_lower] = []
                                self.index_name[name_lower].append(record)

                            if department and department != '—' and len(department) > 2:
                                dept_clean = re.sub(r'^[#\-\s]+', '', department).lower()
                                dept_clean = re.sub(r'[^а-яa-z\s]', '', dept_clean)
                                if dept_clean and len(dept_clean) > 2:
                                    if dept_clean not in self.index_department:
                                        self.index_department[dept_clean] = []
                                    self.index_department[dept_clean].append(record)

                            if cabinet and cabinet != '—' and len(cabinet) > 0:
                                cabinet_norm = cabinet.lower()
                                if cabinet_norm not in self.index_cabinet:
                                    self.index_cabinet[cabinet_norm] = []
                                self.index_cabinet[cabinet_norm].append(record)

            print(f"Загружено {len(self.data)} записей из справочника")
            print(f"Индексов по кабинетам: {len(self.index_cabinet)}")
            print(f"Индексов по ФИО: {len(self.index_name)}")
            print(f"Индексов по отделам: {len(self.index_department)}")
            return True

        except Exception as e:
            print(f"Ошибка загрузки справочника: {e}")
            return False

    def load_from_txt(self, file_path):
        self.data = []
        self.index_name = {}
        self.index_department = {}
        self.index_cabinet = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')

            for line in lines:
                line = line.strip()
                if not line or line.startswith('+') or line.startswith('|==') or line.startswith('|--'):
                    continue

                if line.startswith('|'):
                    parts = line.split('|')
                    if len(parts) >= 3:
                        должность = self._clean_text(parts[1]) if len(parts) > 1 else ''
                        фио = self._clean_text(parts[2]) if len(parts) > 2 else ''
                        кабинет = self._clean_text(parts[3]) if len(parts) > 3 else ''

                        телефон = ''

                        if len(parts) > 4:
                            phone_part = self._clean_text(parts[4])
                            if phone_part and phone_part not in ['-', '—', '####', '#',
                                                                 ''] and not phone_part.startswith('#'):
                                if not any(x in phone_part.lower() for x in ['@', 'mail', 'http']):
                                    телефон = phone_part

                        if len(parts) > 5:
                            phone_part = self._clean_text(parts[5])
                            if phone_part and phone_part not in ['-', '—', '####', '#',
                                                                 ''] and not phone_part.startswith('#'):
                                if not any(x in phone_part.lower() for x in ['@', 'mail', 'http']):
                                    if телефон:
                                        телефон += ', ' + phone_part
                                    else:
                                        телефон = phone_part

                        if len(parts) > 6:
                            phone_part = self._clean_text(parts[6])
                            if phone_part and phone_part not in ['-', '—', '####', '#',
                                                                 ''] and not phone_part.startswith('#'):
                                if not any(x in phone_part.lower() for x in ['@', 'mail', 'http']):
                                    if телефон:
                                        телефон += ', ' + phone_part
                                    else:
                                        телефон = phone_part

                        name = фио
                        department = должность
                        cabinet = self._normalize_cabinet(кабинет)

                        if name or department or cabinet:
                            if not телефон:
                                телефон = '—'

                            if name and name != '—' and any(x in name.lower() for x in ['@', 'mail', 'http']):
                                name = '—'
                            if department and department != '—' and any(
                                    x in department.lower() for x in ['@', 'mail', 'http']):
                                department = '—'

                            record = {
                                'name': name if name else '—',
                                'department': department if department else '—',
                                'cabinet': cabinet if cabinet else '—',
                                'phone': телефон
                            }
                            self.data.append(record)

                            if name and name != '—' and len(name) > 2:
                                name_lower = name.lower()
                                if name_lower not in self.index_name:
                                    self.index_name[name_lower] = []
                                self.index_name[name_lower].append(record)

                            if department and department != '—' and len(department) > 2:
                                dept_clean = re.sub(r'^[#\-\s]+', '', department).lower()
                                dept_clean = re.sub(r'[^а-яa-z\s]', '', dept_clean)
                                if dept_clean and len(dept_clean) > 2:
                                    if dept_clean not in self.index_department:
                                        self.index_department[dept_clean] = []
                                    self.index_department[dept_clean].append(record)

                            if cabinet and cabinet != '—' and len(cabinet) > 0:
                                cabinet_norm = cabinet.lower()
                                if cabinet_norm not in self.index_cabinet:
                                    self.index_cabinet[cabinet_norm] = []
                                self.index_cabinet[cabinet_norm].append(record)

            print(f"Загружено {len(self.data)} записей из справочника")
            print(f"Индексов по кабинетам: {len(self.index_cabinet)}")
            print(f"Индексов по ФИО: {len(self.index_name)}")
            print(f"Индексов по отделам: {len(self.index_department)}")
            return True

        except Exception as e:
            print(f"Ошибка загрузки TXT: {e}")
            return False

    def _clean_text(self, text):
        if not text:
            return ''
        text = re.sub(r'[•▪▫◦▪▸►]', '', text)
        text = ' '.join(text.split())
        return text.strip()

    def _normalize_cabinet(self, cabinet):
        if not cabinet or cabinet == '—' or cabinet == '-':
            return ''
        cabinet = re.sub(r'[^\d\w]', '', cabinet)
        return cabinet.strip()

    def _normalize_name(self, name):
        if not name:
            return ''
        name = ' '.join(name.lower().split())
        parts = name.split()
        if len(parts) >= 2:
            return ' '.join(parts[:2])
        return name

    def find_phone(self, cert_info):
        office = cert_info.get('office_number', '')
        if office and office != '—':
            office_norm = self._normalize_cabinet(office)
            if office_norm and office_norm in self.index_cabinet:
                records = self.index_cabinet[office_norm]
                if records:
                    phone = records[0].get('phone', '—')
                    if phone and phone != '—' and not any(x in phone.lower() for x in ['@', 'mail', 'http']):
                        if re.search(r'\d', phone):
                            return phone

        name = cert_info.get('subject_cn', '')
        if name and name != '—' and name != 'Не найдено':
            name_variants = [
                name.lower(),
                self._normalize_name(name),
                name.split()[0] if name.split() else ''
            ]
            for nv in name_variants:
                if nv and nv in self.index_name:
                    records = self.index_name[nv]
                    if records:
                        phone = records[0].get('phone', '—')
                        if phone and phone != '—' and not any(x in phone.lower() for x in ['@', 'mail', 'http']):
                            if re.search(r'\d', phone):
                                return phone

        department = cert_info.get('department', '')
        if department and department != '—' and len(department) > 3:
            dept_lower = department.lower()
            dept_clean = re.sub(r'[^а-яa-z\s]', '', dept_lower)
            if len(dept_clean) > 3:
                for key, records in self.index_department.items():
                    if key and len(key) > 2:
                        if key in dept_clean or dept_clean in key:
                            if records:
                                phone = records[0].get('phone', '—')
                                if phone and phone != '—' and not any(
                                        x in phone.lower() for x in ['@', 'mail', 'http']):
                                    if re.search(r'\d', phone):
                                        return phone

        return '—'

    def get_phone_for_cert(self, cert_info):
        return self.find_phone(cert_info)

class ToastNotification:
    _active_toasts = []

    def __init__(self, parent, message, duration=4000, notification_type="info"):
        self.parent = parent
        self.message = message
        self.duration = duration
        self.notification_type = notification_type
        self.toast = None

        colors_config = {
            "info": {"bg": BUTTON_COLOR, "fg": "white"},
            "warning": {"bg": WARNING_COLOR, "fg": WARNING_TEXT},
            "error": {"bg": EXPIRED_COLOR, "fg": EXPIRED_TEXT},
            "success": {"bg": NORMAL_COLOR, "fg": NORMAL_TEXT}
        }

        self.bg_color = colors_config.get(notification_type, colors_config["info"])["bg"]
        self.fg_color = colors_config.get(notification_type, colors_config["info"])["fg"]
        self.parent.after(50, self._show)

    def _show(self):
        try:
            for toast in ToastNotification._active_toasts:
                if toast and toast.winfo_exists():
                    try:
                        if hasattr(toast, 'message_text') and toast.message_text == self.message:
                            return
                    except:
                        pass

            self.toast = tk.Toplevel(self.parent)
            self.toast.message_text = self.message
            self.toast.overrideredirect(True)
            self.toast.configure(bg=self.bg_color, bd=0, highlightthickness=0)
            self.toast.attributes('-topmost', True)

            icons = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅"}
            icon = icons.get(self.notification_type, "ℹ️")

            titles = {"info": "Информация", "warning": "Внимание", "error": "Ошибка", "success": "Успех"}
            title_text = titles.get(self.notification_type, "Информация")

            main_frame = tk.Frame(self.toast, bg=self.bg_color, bd=1, relief='solid')
            main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

            header_frame = tk.Frame(main_frame, bg=self.bg_color)
            header_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

            tk.Label(header_frame, text=icon, font=('Segoe UI', 16),
                     bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(header_frame, text=title_text, font=('Segoe UI', 11, 'bold'),
                     bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)

            close_btn = tk.Label(header_frame, text="✕", font=('Segoe UI', 12, 'bold'),
                                 bg=self.bg_color, fg=self.fg_color, cursor='hand2')
            close_btn.pack(side=tk.RIGHT)
            close_btn.bind("<Button-1>", lambda e: self._close())

            body_frame = tk.Frame(main_frame, bg=self.bg_color)
            body_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 10))

            tk.Label(body_frame, text=self.message, font=('Segoe UI', 10),
                     bg=self.bg_color, fg=self.fg_color, wraplength=350,
                     justify=tk.LEFT).pack(anchor=tk.W)

            self.toast.update_idletasks()

            screen_width = self.toast.winfo_screenwidth()
            screen_height = self.toast.winfo_screenheight()

            toast_width = 380
            toast_height = 120

            x = screen_width - toast_width - 20
            y = screen_height - toast_height - 50

            self.toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")

            ToastNotification._active_toasts.append(self.toast)
            ToastNotification._active_toasts = [t for t in ToastNotification._active_toasts
                                                if t and t.winfo_exists()]

            self.toast.attributes('-alpha', 0)
            self._fade_in()
            self.toast.after(self.duration, self._fade_out)

        except Exception as e:
            print(f"Ошибка при создании уведомления: {e}")

    def _fade_in(self, alpha=0):
        if self.toast and self.toast.winfo_exists() and alpha <= 0.95:
            alpha += 0.05
            try:
                self.toast.attributes('-alpha', alpha)
                self.toast.after(20, lambda: self._fade_in(alpha))
            except:
                pass

    def _fade_out(self, alpha=0.95):
        if self.toast and self.toast.winfo_exists() and alpha >= 0.05:
            alpha -= 0.05
            try:
                self.toast.attributes('-alpha', alpha)
                self.toast.after(20, lambda: self._fade_out(alpha))
            except:
                pass
        else:
            self._close()

    def _close(self):
        try:
            if self.toast and self.toast.winfo_exists():
                if self.toast in ToastNotification._active_toasts:
                    ToastNotification._active_toasts.remove(self.toast)
                self.toast.destroy()
                self.toast = None
        except:
            pass


class NotificationHistory:
    def __init__(self, parent):
        self.parent = parent
        self.notifications = []
        self.history_window = None
        self.load_history()

    def add_notification(self, message, notification_type="info"):
        notification = {
            'time': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'message': message,
            'type': notification_type
        }
        self.notifications.insert(0, notification)
        if len(self.notifications) > 100:
            self.notifications = self.notifications[:100]
        self.save_history()

    def save_history(self):
        try:
            history_file = os.path.join(os.path.expanduser("~"), "notification_history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.notifications, f, indent=4, ensure_ascii=False)
        except:
            pass

    def load_history(self):
        try:
            history_file = os.path.join(os.path.expanduser("~"), "notification_history.json")
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    self.notifications = json.load(f)
        except:
            self.notifications = []

    def show_history_window(self):
        if self.history_window and self.history_window.winfo_exists():
            self.history_window.lift()
            self.history_window.focus_force()
            return

        self.history_window = tk.Toplevel(self.parent)
        self.history_window.title("История уведомлений")
        self.history_window.geometry("700x500")
        self.history_window.configure(bg=BG_COLOR)
        self.history_window.minsize(600, 400)

        self.history_window.update_idletasks()
        x = (self.history_window.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.history_window.winfo_screenheight() // 2) - (500 // 2)
        self.history_window.geometry(f"700x500+{x}+{y}")

        main_frame = ttk.Frame(self.history_window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(title_frame, text=" История уведомлений",
                  font=('Segoe UI', 14, 'bold')).pack(side=tk.LEFT)

        ttk.Label(title_frame, text=f"Всего: {len(self.notifications)}",
                  font=('Segoe UI', 10), foreground=ACCENT_COLOR).pack(side=tk.RIGHT)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(btn_frame, text="🗑 Очистить историю",
                   command=self.clear_history, style='Accent.TButton').pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="🔄Обновить",
                   command=self.refresh_history_display, style='Accent.TButton').pack(side=tk.LEFT, padx=5)

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Время", "Тип", "Сообщение")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        self.history_tree.heading("Время", text="Время")
        self.history_tree.heading("Тип", text="Тип")
        self.history_tree.heading("Сообщение", text="Сообщение")

        self.history_tree.column("Время", width=140, anchor=tk.W)
        self.history_tree.column("Тип", width=100, anchor=tk.CENTER)
        self.history_tree.column("Сообщение", width=420, anchor=tk.W)

        scroll_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_tree.configure(yscrollcommand=scroll_y.set)
        self.history_tree.pack(fill=tk.BOTH, expand=True)

        self.history_tree.tag_configure('error', background=EXPIRED_COLOR, foreground=EXPIRED_TEXT)
        self.history_tree.tag_configure('warning', background=WARNING_COLOR, foreground=WARNING_TEXT)
        self.history_tree.tag_configure('success', background=NORMAL_COLOR, foreground=NORMAL_TEXT)
        self.history_tree.tag_configure('info', background=BUTTON_COLOR, foreground='white')

        self.refresh_history_display()

        close_btn = ttk.Button(main_frame, text="Закрыть",
                               command=self.history_window.destroy, style='Accent.TButton')
        close_btn.pack(pady=(10, 0))

        self.history_window.protocol("WM_DELETE_WINDOW", self._on_history_window_close)

    def _on_history_window_close(self):
        if self.history_window:
            self.history_window.destroy()
            self.history_window = None

    def refresh_history_display(self):
        if not self.history_window or not self.history_window.winfo_exists():
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        types = {"error": "❌ Ошибка", "warning": "⚠️ Внимание", "success": "✅ Успех", "info": "ℹ️ Информация"}

        for notif in self.notifications:
            notif_type = notif.get('type', 'info')
            display_type = types.get(notif_type, "ℹ️ Информация")
            tag = notif_type

            self.history_tree.insert("", tk.END, values=(
                notif.get('time', ''),
                display_type,
                notif.get('message', '')
            ), tags=(tag,))

    def clear_history(self):
        if messagebox.askyesno("Подтверждение", "Очистить всю историю уведомлений?"):
            self.notifications = []
            self.save_history()
            self.refresh_history_display()
            ToastNotification(self.parent, "История уведомлений очищена", 2000, "success")


class PushNotificationManager:
    def __init__(self):
        self.toaster = None
        if TOAST_AVAILABLE:
            try:
                self.toaster = ToastNotifier()
            except:
                self.toaster = None
        self.notification_interval = 3600
        self.last_notification_time = {}
        self.running = False
        self.thread = None
        self._last_messages = {}

    def set_interval(self, hours):
        self.notification_interval = hours * 3600

    def send_notification(self, title, message, duration=10):
        if self.toaster:
            try:
                msg_key = f"{title}:{message}"
                current_time = time.time()
                if msg_key in self._last_messages:
                    if current_time - self._last_messages[msg_key] < 300:
                        return True

                self.toaster.show_toast(title, message, duration=duration, threaded=True)
                self._last_messages[msg_key] = current_time
                self._last_messages = {k: v for k, v in self._last_messages.items()
                                       if current_time - v < 3600}
                return True
            except Exception as e:
                print(f"Ошибка уведомления: {e}")
                return False
        return False

    def check_and_notify_expired(self, expired_count, warning_count, total_count):
        current_time = time.time()
        last_check = self.last_notification_time.get('expired', 0)

        if current_time - last_check >= self.notification_interval:
            if expired_count > 0:
                self.send_notification(
                    "⚠️ Критическое уведомление",
                    f"Обнаружено {expired_count} просроченных сертификатов!\n"
                    f"Истекающих: {warning_count}\nВсего: {total_count}",
                    duration=15
                )
                self.last_notification_time['expired'] = current_time
                return True
            elif warning_count > 0:
                self.send_notification(
                    "⚡ Внимание",
                    f"{warning_count} сертификатов истекают в ближайшее время!\nВсего: {total_count}",
                    duration=10
                )
                self.last_notification_time['expired'] = current_time
                return True
        return False

    def start_background_monitoring(self, callback, interval_seconds=3600):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop,
                                       args=(callback, interval_seconds), daemon=True)
        self.thread.start()

    def _monitoring_loop(self, callback, interval_seconds):
        while self.running:
            try:
                callback()
                for _ in range(interval_seconds):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"Ошибка мониторинга: {e}")
                time.sleep(60)

    def stop_monitoring(self):
        self.running = False


class MCHDParser:
    def __init__(self):
        pass

    @staticmethod
    def parse_file(file_path):
        result = {
            'file_name': file_path,
            'file_type': 'МЧД',
            'doc_number': 'Не найден',
            'issue_date': 'Не найдена',
            'expiry_date': 'Не найден',
            'full_name': 'Не найдено',
            'inn': 'Не найден',
            'snils': 'Не найден',
            'birth_date': 'Не найдена',
            'authority_codes': [],
            'authority_names': [],
            'xml_content': None,
            'status': 'Не определен',
            'color': MCHD_COLOR,
            'issuer_org_name': 'Не найдено',
            'issuer_org_inn': 'Не найден',
            'issuer_org_kpp': 'Не найден',
            'issuer_org_ogrn': 'Не найден',
            'issuer_org_address': 'Не найден',
            'issuer_person_fullname': 'Не найдено',
            'issuer_person_inn': 'Не найден',
            'issuer_person_snils': 'Не найден',
            'issuer_person_position': 'Не найдена',
            'issuer_person_birthdate': 'Не найдена'
        }
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                result['xml_content'] = content
            try:
                parser = ET.XMLParser(encoding='utf-8')
                tree = ET.parse(file_path, parser=parser)
                root = tree.getroot()
                result['xml_tree'] = tree
                result['xml_root'] = root
            except:
                pass

            patterns = [
                r'НомДовер="([^"]+)"',
                r'<НомДовер[^>]*>(.*?)</НомДовер',
                r'DocumentId[^>]*>([^<]+)',
                r'№\s*([^<\s]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    result['doc_number'] = match.group(1).strip()
                    break

            patterns = [
                r'ДатаВыдДовер="([^"]+)"',
                r'<ДатаВыдДовер[^>]*>(.*?)</ДатаВыдДовер',
                r'IssueDate[^>]*>([^<]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    result['issue_date'] = MCHDParser._format_date(match.group(1).strip())
                    break

            patterns = [
                r'СрокДейст="([^"]+)"',
                r'<СрокДейст[^>]*>(.*?)</СрокДейст',
                r'ExpiryDate[^>]*>([^<]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    result['expiry_date'] = MCHDParser._format_date(match.group(1).strip())
                    break

            match = re.search(r'<СвУпПред\s+ТипПред="3">(.*?)</СвУпПред>', content, re.DOTALL)
            if match:
                section = match.group(1)
                pattern = r'<ФИО\s+Фамилия="([^"]*)"\s+Имя="([^"]*)"\s+Отчество="([^"]*)"'
                match_fio = re.search(pattern, section)
                if match_fio:
                    last_name = match_fio.group(1).strip()
                    first_name = match_fio.group(2).strip()
                    middle_name = match_fio.group(3).strip()
                    name_parts = []
                    if last_name:
                        name_parts.append(last_name)
                    if first_name:
                        name_parts.append(first_name)
                    if middle_name:
                        name_parts.append(middle_name)
                    if name_parts:
                        result['full_name'] = ' '.join(name_parts)

                match_inn = re.search(r'<СведФизЛ\s+ИННФЛ="([^"]*)"', section)
                if match_inn and match_inn.group(1).strip():
                    result['inn'] = match_inn.group(1).strip()

                match_snils = re.search(r'СНИЛС="([^"]*)"', section)
                if match_snils and match_snils.group(1).strip():
                    result['snils'] = match_snils.group(1).strip()

                match_birth = re.search(r'<СведФЛ\s+ДатаРожд="([^"]*)"', section)
                if match_birth and match_birth.group(1).strip():
                    result['birth_date'] = MCHDParser._format_date(match_birth.group(1).strip())

            person_match = re.search(r'<ЛицоБезДов[^>]*>(.*?)</ЛицоБезДов>', content, re.DOTALL)
            if person_match:
                person_section = person_match.group(1)
                svfl_match = re.search(r'<СвФЛ\s+ИННФЛ="([^"]*)"\s+СНИЛС="([^"]*)"\s+Должность="([^"]*)"',
                                       person_section)
                if svfl_match:
                    result['issuer_person_inn'] = svfl_match.group(1).strip() if svfl_match.group(1) else 'Не найден'
                    result['issuer_person_snils'] = svfl_match.group(2).strip() if svfl_match.group(2) else 'Не найден'
                    result['issuer_person_position'] = svfl_match.group(3).strip() if svfl_match.group(
                        3) else 'Не найдена'

                fio_match = re.search(r'<ФИО\s+Фамилия="([^"]*)"\s+Имя="([^"]*)"\s+Отчество="([^"]*)"', person_section)
                if fio_match:
                    last_name = fio_match.group(1).strip()
                    first_name = fio_match.group(2).strip()
                    middle_name = fio_match.group(3).strip()
                    name_parts = []
                    if last_name:
                        name_parts.append(last_name)
                    if first_name:
                        name_parts.append(first_name)
                    if middle_name:
                        name_parts.append(middle_name)
                    if name_parts:
                        result['issuer_person_fullname'] = ' '.join(name_parts)

                birth_match = re.search(r'<СведФЛ\s+ДатаРожд="([^"]*)"', person_section)
                if birth_match and birth_match.group(1).strip():
                    result['issuer_person_birthdate'] = MCHDParser._format_date(birth_match.group(1).strip())

            org_match = re.search(r'<СвРосОрг\s+НаимОрг="([^"]*)"\s+ИННЮЛ="([^"]*)"\s+КПП="([^"]*)"\s+ОГРН="([^"]*)"',
                                  content)
            if org_match:
                result['issuer_org_name'] = org_match.group(1).strip() if org_match.group(1) else 'Не найдено'
                result['issuer_org_inn'] = org_match.group(2).strip() if org_match.group(2) else 'Не найден'
                result['issuer_org_kpp'] = org_match.group(3).strip() if org_match.group(3) else 'Не найден'
                result['issuer_org_ogrn'] = org_match.group(4).strip() if org_match.group(4) else 'Не найден'

            addr_match = re.search(r'<АдрРФ>([^<]+)</АдрРФ>', content)
            if addr_match:
                result['issuer_org_address'] = addr_match.group(1).strip()

            auth_codes = set()
            matches = re.findall(r'КодПолн="([^"]+)"', content)
            for code in matches:
                if code:
                    auth_codes.add(code)
            result['authority_codes'] = list(auth_codes)

            if result['expiry_date'] and result['expiry_date'] != 'Не найден':
                try:
                    exp_date = None
                    for fmt in ['%d.%m.%Y', '%Y-%m-%d', '%d.%m.%y']:
                        try:
                            exp_date = datetime.strptime(result['expiry_date'], fmt)
                            break
                        except:
                            continue
                    if exp_date:
                        today = datetime.now()
                        days_left = (exp_date - today).days
                        if exp_date < today:
                            result['status'] = "Просрочен"
                            result['color'] = EXPIRED_COLOR
                        elif days_left <= 60:
                            result['status'] = f"Истекает ({days_left} дн.)"
                            result['color'] = WARNING_COLOR
                        else:
                            result['status'] = "Действует"
                            result['color'] = MCHD_COLOR
                except:
                    pass
        except Exception as e:
            result['status'] = 'Ошибка парсинга'
        return result

    @staticmethod
    def _format_date(date_str):
        if not date_str:
            return 'Не найдена'
        date_str = str(date_str).strip()
        if re.match(r'\d{2}\.\d{2}\.\d{4}', date_str):
            return date_str
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            parts = date_str.split('-')
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
        if re.match(r'\d{2}\.\d{2}\.\d{2}', date_str):
            parts = date_str.split('.')
            year = '20' + parts[2]
            return f"{parts[0]}.{parts[1]}.{year}"
        return date_str


class MCHDMerger:
    @staticmethod
    def get_merged_authorities(mchd_list):
        if not mchd_list:
            return None
        all_codes = set()
        for mchd in mchd_list:
            codes = mchd.get('authority_codes', [])
            all_codes.update(codes)
        result = {
            'person_name': mchd_list[0].get('full_name', 'Неизвестно'),
            'total_files': len(mchd_list),
            'unique_codes_count': len(all_codes),
            'codes': sorted(list(all_codes)),
            'file_names': [os.path.basename(m.get('file_name', '')) for m in mchd_list]
        }
        return result

    @staticmethod
    def merge_mchd_files(mchd_list, output_path=None):
        if not mchd_list or len(mchd_list) < 2:
            return None
        temp_file = None
        try:
            base_mchd = mchd_list[0]
            base_file = base_mchd.get('file_name')
            if not base_file or not os.path.exists(base_file):
                return None
            with open(base_file, 'r', encoding='utf-8') as f:
                content = f.read()
            vn_nom_dover = None
            vn_match = re.search(r'ВнНомДовер="([^"]+)"', content)
            if vn_match:
                vn_nom_dover = vn_match.group(1)
            new_uuid = str(uuid.uuid4()).lower()
            today = datetime.now()
            id_file_prefix = f"ON_EMCHD_{today.strftime('%Y%m%d')}"
            new_id_file = f"{id_file_prefix}_{new_uuid}"
            old_id_file_match = re.search(r'ИдФайл="([^"]+)"', content)
            if old_id_file_match:
                old_id_file = old_id_file_match.group(1)
                content = content.replace(old_id_file, new_id_file)
            uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
            old_uuids = re.findall(uuid_pattern, content, re.IGNORECASE)
            if old_uuids:
                for old_uuid in set(old_uuids):
                    if old_uuid != new_uuid:
                        content = content.replace(old_uuid, new_uuid)
            if vn_nom_dover:
                content = re.sub(r'ВнНомДовер="[^"]*"', f'ВнНомДовер="{vn_nom_dover}"', content)
            parser = ET.XMLParser(encoding='utf-8')
            temp_file = base_file + ".temp.xml"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            tree = ET.parse(temp_file, parser=parser)
            root = tree.getroot()
            for elem in root.iter():
                if elem.tag.endswith('Доверенность'):
                    elem.set('ИдФайл', new_id_file)
                    break
            for elem in root.iter():
                if elem.tag.endswith('СвДов'):
                    elem.set('НомДовер', new_uuid)
                    if vn_nom_dover:
                        elem.set('ВнНомДовер', vn_nom_dover)
                    break
            for elem in root.iter():
                if elem.tag.endswith('СведСист'):
                    new_url = f"https://m4d.nalog.gov.ru/emchd/check-status?guid={new_uuid}"
                    elem.text = new_url
                    break
            all_codes = set()
            code_to_name = {}
            for mchd in mchd_list:
                codes = mchd.get('authority_codes', [])
                names = mchd.get('authority_names', [])
                all_codes.update(codes)
                for i, code in enumerate(codes):
                    if i < len(names) and names[i]:
                        code_to_name[code] = names[i]
            svpoln = None
            for elem in root.iter():
                if elem.tag.endswith('СвПолн'):
                    svpoln = elem
                    break
            if svpoln is None:
                parent_elem = None
                for elem in root.iter():
                    if elem.tag.endswith('СвДов') or elem.tag.endswith('Довер'):
                        parent_elem = elem
                        break
                if parent_elem is not None:
                    svpoln = ET.SubElement(parent_elem, 'СвПолн')
                    svpoln.set('ТипПолн', '1')
                    svpoln.set('ПрСовмПолн', '1')
                else:
                    svpoln = ET.SubElement(root, 'СвПолн')
                    svpoln.set('ТипПолн', '1')
                    svpoln.set('ПрСовмПолн', '1')
            for elem in list(svpoln):
                if elem.tag.endswith('МашПолн'):
                    svpoln.remove(elem)
            for code in sorted(all_codes):
                mashpoln = ET.SubElement(svpoln, 'МашПолн')
                mashpoln.set('КодПолн', code)
                name = code_to_name.get(code, '')
                if name:
                    mashpoln.set('НаимПолн', name[:250])
            xml_str = ET.tostring(root, encoding='unicode')
            xml_str = re.sub(r'ns0:', '', xml_str)
            xml_str = re.sub(r'\s+=\s+', '=', xml_str)
            try:
                dom = minidom.parseString(xml_str.encode('utf-8'))
                pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8')
                pretty_xml = b'\n'.join(line for line in pretty_xml.split(b'\n') if line.strip())
            except:
                pretty_xml = xml_str.encode('utf-8')
            if not output_path:
                person_name = base_mchd.get('full_name', 'Unknown').replace(' ', '_')
                output_path = os.path.join(
                    os.path.dirname(base_file),
                    f"Объединенная_МЧД_{person_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
                )
            with open(output_path, 'wb') as f:
                if isinstance(pretty_xml, bytes):
                    f.write(pretty_xml)
                else:
                    f.write(pretty_xml.encode('utf-8'))
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            return output_path
        except Exception as e:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return None


class AuthoritiesViewWindow:
    def __init__(self, parent, merged_data):
        self.parent = parent
        self.merged_data = merged_data
        self.window = None
        self._create_window()

    def _create_window(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Объединенные полномочия МЧД")
        self.window.geometry("600x500")
        self.window.configure(bg=BG_COLOR)
        self.setup_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self.window:
            self.window.destroy()
            self.window = None

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(title_frame, text=f"Объединенные полномочия",
                  font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W)
        ttk.Label(title_frame, text=f"ФИО: {self.merged_data.get('person_name', 'Неизвестно')}",
                  font=('Segoe UI', 11), foreground=ACCENT_COLOR).pack(anchor=tk.W)
        info_frame = ttk.LabelFrame(main_frame, text=" Исходные файлы ", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        files_text = "\n".join([f"• {f}" for f in self.merged_data.get('file_names', [])])
        ttk.Label(info_frame, text=files_text, font=('Segoe UI', 9)).pack(anchor=tk.W)
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        stats_text = f"Всего файлов: {self.merged_data.get('total_files', 0)} | Уникальных кодов: {self.merged_data.get('unique_codes_count', 0)}"
        ttk.Label(stats_frame, text=stats_text, font=('Segoe UI', 10, 'bold')).pack()
        codes_frame = ttk.LabelFrame(main_frame, text=" Коды полномочий ", padding=10)
        codes_frame.pack(fill=tk.BOTH, expand=True)
        listbox_frame = ttk.Frame(codes_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.codes_listbox = tk.Listbox(listbox_frame, height=12, selectmode=tk.EXTENDED,
                                        font=('Courier New', 10))
        self.codes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.codes_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.codes_listbox.configure(yscrollcommand=scrollbar.set)
        for code in self.merged_data.get('codes', []):
            self.codes_listbox.insert(tk.END, code)
        self.codes_listbox.bind("<Control-c>", self.copy_selected_codes_event)
        self.codes_listbox.bind("<Control-C>", self.copy_selected_codes_event)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        ttk.Button(btn_frame, text="📋 Копировать все коды",
                   command=self.copy_all_codes, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📋 Копировать выбранные",
                   command=self.copy_selected_codes, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Закрыть",
                   command=self._on_close, style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

    def copy_all_codes(self):
        codes = self.merged_data.get('codes', [])
        if codes:
            pyperclip.copy("\n".join(codes))
            messagebox.showinfo("Успех", f"Скопировано {len(codes)} кодов")

    def copy_selected_codes(self):
        selected = self.codes_listbox.curselection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите коды для копирования")
            return
        codes = [self.codes_listbox.get(i) for i in selected]
        pyperclip.copy("\n".join(codes))
        messagebox.showinfo("Успех", f"Скопировано {len(codes)} кодов")

    def copy_selected_codes_event(self, event):
        selected = self.codes_listbox.curselection()
        if selected:
            codes = [self.codes_listbox.get(i) for i in selected]
            pyperclip.copy("\n".join(codes))
            self.window.title(f"Скопировано {len(codes)} кодов")
            self.window.after(2000, lambda: self.window.title("Объединенные полномочия МЧД"))
            return "break"
        return None


class NormativeWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self._create_window()

    def _create_window(self):
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

    def _on_close(self):
        if self.window:
            self.window.destroy()
            self.window = None

    def setup_ui(self):
        frame = ttk.Frame(self.window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Нормативные документы по электронной подписи и МЧД",
                  font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))
        canvas_frame = ttk.Frame(frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='TFrame')
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        normative_items = [
            ("ФЕДЕРАЛЬНЫЙ ЗАКОН № 63-ФЗ от 06.04.2011 'Об электронной подписи'",
             "http://www.consultant.ru/document/cons_doc_LAW_112701/",
             "Основной закон об электронной подписи"),
            ("ФЕДЕРАЛЬНЫЙ ЗАКОН № 152-ФЗ от 27.07.2006 'О персональных данных'",
             "http://www.consultant.ru/document/cons_doc_LAW_61801/",
             "Закон о защите персональных данных"),
            ("ПРИКАЗ МИНЦИФРЫ РОССИИ № 857 от 18.10.2021 'Об утверждении формата МЧД'",
             "http://publication.pravo.gov.ru/Document/View/0001202112200010",
             "Формат машиночитаемой доверенности"),
            ("ПОСТАНОВЛЕНИЕ ПРАВИТЕЛЬСТВА РФ № 223 от 21.02.2022 'О порядке применения МЧД'",
             "http://publication.pravo.gov.ru/Document/View/0001202202240017",
             "Порядок применения машиночитаемой доверенности"),
            ("ФЕДЕРАЛЬНЫЙ ЗАКОН № 149-ФЗ от 27.07.2006 'Об информации и защите информации'",
             "http://www.consultant.ru/document/cons_doc_LAW_61798/",
             "Закон об информации"),
            ("ГОСТ Р 34.10-2012 - Процессы формирования и проверки ЭП",
             "https://protect.gost.ru/document.aspx?control=7&id=190331",
             "Стандарт электронной подписи"),
            ("ГОСТ Р 34.11-2012 - Функция хэширования",
             "https://protect.gost.ru/document.aspx?control=7&id=190378",
             "Стандарт хэширования"),
            ("Приказ ФНС России от 30.04.2021 № ЕД-7-26/445@ - Формат МЧД для ФНС",
             "https://www.nalog.gov.ru/rn77/about_fts/docs/11631597/",
             "Формат МЧД для налоговой службы"),
        ]
        link_style = {
            'font': ('Segoe UI', 10, 'underline'),
            'foreground': BUTTON_COLOR,
            'cursor': 'hand2',
            'bg': BG_COLOR,
            'borderwidth': 0,
            'anchor': 'w',
            'justify': 'left'
        }
        for title, url, description in normative_items:
            doc_frame = ttk.Frame(scrollable_frame, style='Card.TFrame', padding=10)
            doc_frame.pack(fill=tk.X, pady=5)
            link_btn = tk.Button(
                doc_frame,
                text=title,
                command=lambda u=url: webbrowser.open(u),
                **link_style
            )
            link_btn.pack(anchor=tk.W)
            desc_label = ttk.Label(
                doc_frame,
                text=description,
                font=('Segoe UI', 9),
                foreground=ACCENT_COLOR
            )
            desc_label.pack(anchor=tk.W, pady=(2, 0))
        info_label = ttk.Label(
            scrollable_frame,
            text="\n💡 Для открытия документа нажмите на название выше.\nСсылки открываются в браузере по умолчанию.",
            font=('Segoe UI', 9, 'italic'),
            foreground=ACCENT_COLOR
        )
        info_label.pack(pady=(15, 5))
        ttk.Button(frame, text="Закрыть", command=self._on_close,
                   style='Accent.TButton').pack(pady=(10, 0))

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)


class MCHDTableWindow:
    def __init__(self, parent, mchd_data):
        self.parent = parent
        self.mchd_data = mchd_data
        self.filtered_data = mchd_data.copy()
        self.window = None
        self.selected_items = []
        self.sort_reverse = {}
        self._create_window()

    def _create_window(self):
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("Анализ МЧД - Машиночитаемые доверенности")
        self.window.geometry("1400x800")
        self.window.configure(bg=BG_COLOR)
        self.setup_ui()
        self.check_for_duplicates()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        if self.window:
            self.window.destroy()
            self.window = None

    def setup_ui(self):
        main_frame = ttk.Frame(self.window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(title_frame, text="Машиночитаемые доверенности (МЧД)",
                  font=('Segoe UI', 16, 'bold')).pack(side=tk.LEFT)
        ttk.Label(title_frame, text=f"Всего: {len(self.mchd_data)}",
                  font=('Segoe UI', 12), foreground=ACCENT_COLOR).pack(side=tk.RIGHT, padx=10)
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="🔍 Поиск по фамилии:", font=('Segoe UI', 10)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(5, 10))
        ttk.Button(search_frame, text="✖ Сбросить",
                   command=self.clear_search, style='Accent.TButton', width=12).pack(side=tk.LEFT)
        self.search_result_label = ttk.Label(search_frame, text="",
                                             font=('Segoe UI', 9, 'italic'),
                                             foreground=ACCENT_COLOR)
        self.search_result_label.pack(side=tk.RIGHT, padx=(20, 0))
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        total = len(self.mchd_data)
        expired = sum(1 for m in self.mchd_data if m.get('status') == "Просрочен")
        warning = sum(1 for m in self.mchd_data if m.get('status') and "Истекает" in m.get('status', ''))
        valid = sum(1 for m in self.mchd_data if m.get('status') == "Действует")
        stats_text = f"Действуют: {valid} | Истекают: {warning} | Просрочены: {expired}"
        ttk.Label(stats_frame, text=stats_text,
                  font=('Segoe UI', 11, 'bold')).pack()
        self.duplicate_frame = ttk.Frame(main_frame)
        self.duplicate_frame.pack(fill=tk.X, pady=(0, 10))
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)
        self.columns = ("Файл", "Номер доверенности", "Дата выдачи", "Срок действия",
                        "ФИО", "Коды полномочий", "Статус")
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings",
                                 height=12, selectmode=tk.EXTENDED)
        col_widths = [150, 120, 90, 90, 200, 300, 100]
        for col, width in zip(self.columns, col_widths):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=width, anchor=tk.W, minwidth=50)
            self.sort_reverse[col] = False
        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.tag_configure('expired', background=EXPIRED_COLOR, foreground=EXPIRED_TEXT)
        self.tree.tag_configure('warning', background=WARNING_COLOR, foreground=WARNING_TEXT)
        self.tree.tag_configure('normal', background=MCHD_LIGHT_COLOR)
        self.tree.tag_configure('duplicate_name', background='#fff3cd')
        self.populate_table()
        info_frame = ttk.LabelFrame(main_frame, text=" Информация ", padding=10)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        info_columns_frame = ttk.Frame(info_frame)
        info_columns_frame.pack(fill=tk.X, expand=True)
        left_info = ttk.Frame(info_columns_frame)
        left_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.selected_info_label = ttk.Label(left_info, text="Выбрано: 0 МЧД",
                                             font=('Segoe UI', 10, 'bold'))
        self.selected_info_label.pack(anchor=tk.W)
        self.person_info_label = ttk.Label(left_info, text="",
                                           font=('Segoe UI', 9), foreground=ACCENT_COLOR)
        self.person_info_label.pack(anchor=tk.W)
        right_info = ttk.Frame(info_columns_frame)
        right_info.pack(side=tk.RIGHT, fill=tk.Y)
        self.view_auth_btn = ttk.Button(right_info, text="👁 Просмотр кодов",
                                        command=self.view_merged_authorities, style='Accent.TButton',
                                        state=tk.DISABLED)
        self.view_auth_btn.pack(side=tk.RIGHT, padx=5)
        self.view_personal_btn = ttk.Button(right_info, text="👤 Персональные данные",
                                            command=self.view_personal_data, style='Accent.TButton',
                                            state=tk.DISABLED)
        self.view_personal_btn.pack(side=tk.RIGHT, padx=5)
        self.merge_btn = ttk.Button(right_info, text="🔄 Объединить выбранные МЧД",
                                    command=self.merge_selected, style='Accent.TButton',
                                    state=tk.DISABLED)
        self.merge_btn.pack(side=tk.RIGHT, padx=5)
        ttk.Button(right_info, text="📋 Копировать коды",
                   command=self.copy_selected_codes, style='Accent.TButton').pack(side=tk.RIGHT, padx=5)
        codes_frame = ttk.LabelFrame(main_frame, text=" Коды полномочий выбранных МЧД ", padding=10)
        codes_frame.pack(fill=tk.X, pady=(10, 0))
        listbox_frame = ttk.Frame(codes_frame)
        listbox_frame.pack(fill=tk.X, expand=True)
        self.codes_listbox = tk.Listbox(listbox_frame, height=6, selectmode=tk.SINGLE,
                                        font=('Courier New', 9))
        self.codes_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_codes = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL,
                                     command=self.codes_listbox.yview)
        scroll_codes.pack(side=tk.RIGHT, fill=tk.Y)
        self.codes_listbox.configure(yscrollcommand=scroll_codes.set)
        self.codes_listbox.bind("<Control-c>", self.copy_from_listbox)
        self.codes_listbox.bind("<Control-C>", self.copy_from_listbox)
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="📊 Экспорт в Excel",
                   command=self.export_to_excel, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Закрыть",
                   command=self._on_close, style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

    def copy_from_listbox(self, event):
        selected = self.codes_listbox.curselection()
        if selected:
            codes = [self.codes_listbox.get(i) for i in selected]
            pyperclip.copy("\n".join(codes))
            self.window.title(f"Скопировано {len(codes)} кодов - Анализ МЧД")
            self.window.after(2000, lambda: self.window.title("Анализ МЧД - Машиночитаемые доверенности"))
            return "break"
        return None

    def view_personal_data(self):
        selected_mchd = self.get_selected_mchd_objects()
        if len(selected_mchd) != 1:
            messagebox.showwarning("Внимание", "Выберите ровно одну МЧД для просмотра персональных данных")
            return
        mchd = selected_mchd[0]
        has_issuer_data = (mchd.get('issuer_org_name', 'Не найдено') != 'Не найдено' or
                           mchd.get('issuer_person_fullname', 'Не найдено') != 'Не найдено')
        window_width = 900 if has_issuer_data else 750
        window_height = 750 if has_issuer_data else 600

        data_window = tk.Toplevel(self.window)
        data_window.title(f"Персональные данные МЧД - {os.path.basename(mchd.get('file_name', ''))}")
        data_window.geometry(f"{window_width}x{window_height}")
        data_window.configure(bg=BG_COLOR)
        data_window.minsize(750, 600)

        main_frame = tk.Frame(data_window, bg=BG_COLOR, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_frame = tk.Frame(main_frame, bg=BG_COLOR)
        title_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(title_frame, text="📄", font=('Segoe UI', 32), bg=BG_COLOR, fg=MCHD_COLOR).pack(side=tk.LEFT,
                                                                                                padx=(0, 15))
        title_text_frame = tk.Frame(title_frame, bg=BG_COLOR)
        title_text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(title_text_frame, text="Персональные данные",
                 font=('Segoe UI', 18, 'bold'), bg=BG_COLOR, fg=MCHD_COLOR).pack(anchor=tk.W)
        tk.Label(title_text_frame, text=f"Машиночитаемая доверенность",
                 font=('Segoe UI', 10), bg=BG_COLOR, fg=ACCENT_COLOR).pack(anchor=tk.W)

        file_frame = tk.Frame(main_frame, bg=CARD_BG_COLOR, relief='flat', bd=1, highlightthickness=1,
                              highlightbackground=CARD_BORDER_COLOR)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        file_inner = tk.Frame(file_frame, bg=CARD_BG_COLOR, padx=15, pady=10)
        file_inner.pack(fill=tk.X)

        tk.Label(file_inner, text="📁", font=('Segoe UI', 14), bg=CARD_BG_COLOR, fg=ACCENT_COLOR).pack(side=tk.LEFT,
                                                                                                      padx=(0, 10))
        tk.Label(file_inner, text=os.path.basename(mchd.get('file_name', '')),
                 font=('Segoe UI', 10, 'italic'), bg=CARD_BG_COLOR, fg=ACCENT_COLOR).pack(side=tk.LEFT)

        canvas_frame = tk.Frame(main_frame, bg=BG_COLOR)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def create_info_card(parent, title, icon, data_list, color=MCHD_COLOR):
            card = tk.Frame(parent, bg=CARD_BG_COLOR, relief='flat', bd=0, highlightthickness=1,
                            highlightbackground=CARD_BORDER_COLOR)
            card.pack(fill=tk.X, pady=(0, 15))
            header = tk.Frame(card, bg=color, height=40)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            tk.Label(header, text=f" {icon} {title}", font=('Segoe UI', 11, 'bold'),
                     fg='white', bg=color).pack(side=tk.LEFT, padx=15, pady=8)
            body = tk.Frame(card, bg=CARD_BG_COLOR, padx=15, pady=10)
            body.pack(fill=tk.X)
            for label, value in data_list:
                row = tk.Frame(body, bg=CARD_BG_COLOR)
                row.pack(fill=tk.X, pady=5)
                tk.Label(row, text=f"{label}:", font=('Segoe UI', 9, 'bold'),
                         fg=color, bg=CARD_BG_COLOR, width=24, anchor='w').pack(side=tk.LEFT, padx=(0, 10))
                value_str = str(value) if value else '—'
                text_widget = tk.Text(row, height=1 if len(value_str) < 80 else 2, wrap=tk.WORD,
                                      font=('Segoe UI', 9), bg=CARD_BG_COLOR, fg=TEXT_COLOR, borderwidth=0,
                                      selectbackground=BUTTON_COLOR, selectforeground='white', highlightthickness=0)
                text_widget.insert('1.0', value_str)
                text_widget.config(state='disabled')
                text_widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            return card

        def create_codes_card(parent, title, icon, codes):
            card = tk.Frame(parent, bg=CARD_BG_COLOR, relief='flat', bd=0, highlightthickness=1,
                            highlightbackground=CARD_BORDER_COLOR)
            card.pack(fill=tk.X, pady=(0, 15))
            header = tk.Frame(card, bg=MCHD_COLOR, height=40)
            header.pack(fill=tk.X)
            header.pack_propagate(False)
            tk.Label(header, text=f" {icon} {title}", font=('Segoe UI', 11, 'bold'),
                     fg='white', bg=MCHD_COLOR).pack(side=tk.LEFT, padx=15, pady=8)
            body = tk.Frame(card, bg=CARD_BG_COLOR, padx=15, pady=10)
            body.pack(fill=tk.X)
            if codes:
                codes_frame = tk.Frame(body, bg='#f8f9fa', relief='solid', bd=1)
                codes_frame.pack(fill=tk.X, pady=5)
                codes_text = "\n".join([f"  {code}" for code in codes])
                text_widget = tk.Text(codes_frame, height=min(len(codes) + 1, 10), wrap=tk.WORD,
                                      font=('Courier New', 9), bg='#f8f9fa', fg=TEXT_COLOR,
                                      borderwidth=0, selectbackground=BUTTON_COLOR,
                                      selectforeground='white', padx=10, pady=8)
                text_widget.insert('1.0', codes_text)
                text_widget.config(state='disabled')
                text_widget.pack(fill=tk.BOTH, expand=True)
                counter_frame = tk.Frame(body, bg=CARD_BG_COLOR)
                counter_frame.pack(fill=tk.X, pady=(8, 0))
                tk.Label(counter_frame, text=f"📊 Всего кодов: {len(codes)}",
                         font=('Segoe UI', 9, 'italic'), fg=ACCENT_COLOR, bg=CARD_BG_COLOR).pack(side=tk.LEFT)

                def copy_codes():
                    pyperclip.copy("\n".join(codes))
                    messagebox.showinfo("Успех", f"Скопировано {len(codes)} кодов")

                tk.Button(counter_frame, text="📋 Копировать коды", command=copy_codes,
                          font=('Segoe UI', 8), bg=BUTTON_COLOR, fg='white',
                          cursor='hand2', padx=10, pady=2, relief='flat', bd=0).pack(side=tk.RIGHT)
            else:
                tk.Label(body, text="Нет данных о кодах полномочий",
                         font=('Segoe UI', 9, 'italic'), fg=ACCENT_COLOR, bg=CARD_BG_COLOR).pack(pady=10)
            return card

        personal_data = [
            ("📋 Номер доверенности", mchd.get('doc_number', 'Не найден')),
            ("📅 Дата выдачи", mchd.get('issue_date', 'Не найдена')),
            ("⏰ Срок действия", mchd.get('expiry_date', 'Не найден')),
            ("👤 ФИО представителя", mchd.get('full_name', 'Не найдено')),
            ("🆔 ИНН представителя", mchd.get('inn', 'Не найден')),
            ("🪪 СНИЛС представителя", mchd.get('snils', 'Не найден')),
            ("🎂 Дата рождения представителя", mchd.get('birth_date', 'Не найдена')),
            ("📊 Статус доверенности", mchd.get('status', 'Не определен')),
        ]

        issuer_data = [
            ("📛 Наименование организации", mchd.get('issuer_org_name', 'Не найдено')),
            ("🆔 ИНН организации", mchd.get('issuer_org_inn', 'Не найден')),
            ("🔢 КПП организации", mchd.get('issuer_org_kpp', 'Не найден')),
            ("📄 ОГРН организации", mchd.get('issuer_org_ogrn', 'Не найден')),
            ("📍 Адрес организации", mchd.get('issuer_org_address', 'Не найден')),
        ]

        authorized_data = [
            ("👤 ФИО уполномоченного лица", mchd.get('issuer_person_fullname', 'Не найдено')),
            ("💼 Должность", mchd.get('issuer_person_position', 'Не найдена')),
            ("🆔 ИНН уполномоченного лица", mchd.get('issuer_person_inn', 'Не найден')),
            ("🪪 СНИЛС уполномоченного лица", mchd.get('issuer_person_snils', 'Не найден')),
            ("🎂 Дата рождения уполномоченного лица", mchd.get('issuer_person_birthdate', 'Не найдена')),
        ]

        auth_codes = mchd.get('authority_codes', [])
        create_info_card(scrollable_frame, "ИНФОРМАЦИЯ О ПРЕДСТАВИТЕЛЕ", "👤", personal_data)
        if has_issuer_data:
            create_info_card(scrollable_frame, "ОРГАНИЗАЦИЯ-ДОВЕРИТЕЛЬ", "🏢", issuer_data, ACCENT_COLOR)
            create_info_card(scrollable_frame, "УПОЛНОМОЧЕННОЕ ЛИЦО", "👔", authorized_data, ACCENT_COLOR)
        create_codes_card(scrollable_frame, "КОДЫ ПОЛНОМОЧИЙ", "🔑", auth_codes)

        info_bar = tk.Frame(main_frame, bg='#e9ecef', height=35)
        info_bar.pack(fill=tk.X, pady=(10, 0))
        info_bar.pack_propagate(False)
        tk.Label(info_bar, text="💡 Выделите любой текст мышкой и нажмите Ctrl+C для копирования",
                 font=('Segoe UI', 8), fg=ACCENT_COLOR, bg='#e9ecef').pack(side=tk.LEFT, padx=15, pady=8)

        btn_frame = tk.Frame(main_frame, bg=BG_COLOR)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        def copy_all_data():
            copy_text = "=" * 50 + "\n"
            copy_text += "          ПЕРСОНАЛЬНЫЕ ДАННЫЕ МЧД\n"
            copy_text += "=" * 50 + "\n\n"
            copy_text += "📌 ИНФОРМАЦИЯ О ПРЕДСТАВИТЕЛЕ\n"
            copy_text += "-" * 40 + "\n"
            copy_text += f"Номер доверенности: {mchd.get('doc_number', 'Не найден')}\n"
            copy_text += f"Дата выдачи: {mchd.get('issue_date', 'Не найдена')}\n"
            copy_text += f"Срок действия: {mchd.get('expiry_date', 'Не найден')}\n"
            copy_text += f"ФИО представителя: {mchd.get('full_name', 'Не найдено')}\n"
            copy_text += f"ИНН представителя: {mchd.get('inn', 'Не найден')}\n"
            copy_text += f"СНИЛС представителя: {mchd.get('snils', 'Не найден')}\n"
            copy_text += f"Дата рождения представителя: {mchd.get('birth_date', 'Не найдена')}\n"
            copy_text += f"Статус: {mchd.get('status', 'Не определен')}\n\n"
            if has_issuer_data:
                copy_text += "📌 ОРГАНИЗАЦИЯ-ДОВЕРИТЕЛЬ\n"
                copy_text += "-" * 40 + "\n"
                copy_text += f"Наименование: {mchd.get('issuer_org_name', 'Не найдено')}\n"
                copy_text += f"ИНН: {mchd.get('issuer_org_inn', 'Не найден')}\n"
                copy_text += f"КПП: {mchd.get('issuer_org_kpp', 'Не найден')}\n"
                copy_text += f"ОГРН: {mchd.get('issuer_org_ogrn', 'Не найден')}\n"
                copy_text += f"Адрес: {mchd.get('issuer_org_address', 'Не найден')}\n\n"
                copy_text += "📌 УПОЛНОМОЧЕННОЕ ЛИЦО\n"
                copy_text += "-" * 40 + "\n"
                copy_text += f"ФИО: {mchd.get('issuer_person_fullname', 'Не найдено')}\n"
                copy_text += f"Должность: {mchd.get('issuer_person_position', 'Не найдена')}\n"
                copy_text += f"ИНН: {mchd.get('issuer_person_inn', 'Не найден')}\n"
                copy_text += f"СНИЛС: {mchd.get('issuer_person_snils', 'Не найден')}\n"
                copy_text += f"Дата рождения: {mchd.get('issuer_person_birthdate', 'Не найдена')}\n\n"
            copy_text += "📌 КОДЫ ПОЛНОМОЧИЙ\n"
            copy_text += "-" * 40 + "\n"
            if auth_codes:
                for code in auth_codes:
                    copy_text += f"  • {code}\n"
            else:
                copy_text += "Нет данных\n"
            copy_text += "\n" + "=" * 50 + "\n"
            copy_text += f"Дата выгрузки: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            pyperclip.copy(copy_text)
            messagebox.showinfo("Успех", "Все данные скопированы в буфер обмена")

        btn_copy = tk.Button(btn_frame, text="📋 КОПИРОВАТЬ ВСЕ ДАННЫЕ", command=copy_all_data,
                             font=('Segoe UI', 10, 'bold'), bg=BUTTON_COLOR, fg='white',
                             cursor='hand2', padx=20, pady=8, relief='flat', bd=0)
        btn_copy.pack(side=tk.LEFT, padx=5)

        btn_close = tk.Button(btn_frame, text="❌ ЗАКРЫТЬ", command=data_window.destroy,
                              font=('Segoe UI', 10), bg=ACCENT_COLOR, fg='white',
                              cursor='hand2', padx=20, pady=8, relief='flat', bd=0)
        btn_close.pack(side=tk.RIGHT, padx=5)

        def on_enter_btn(btn, color):
            btn.config(bg=color)

        def on_leave_btn(btn, color):
            btn.config(bg=color)

        btn_copy.bind("<Enter>", lambda e: on_enter_btn(btn_copy, BUTTON_HOVER))
        btn_copy.bind("<Leave>", lambda e: on_leave_btn(btn_copy, BUTTON_COLOR))
        btn_close.bind("<Enter>", lambda e: on_enter_btn(btn_close, '#5a6268'))
        btn_close.bind("<Leave>", lambda e: on_leave_btn(btn_close, ACCENT_COLOR))

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def on_destroy():
            canvas.unbind_all("<MouseWheel>")
            data_window.destroy()

        data_window.protocol("WM_DELETE_WINDOW", on_destroy)

    def on_search(self, *args):
        query = self.search_var.get().lower()
        if not query:
            self.filtered_data = self.mchd_data.copy()
            self.search_result_label.config(text="")
        else:
            self.filtered_data = []
            for mchd in self.mchd_data:
                full_name = mchd.get('full_name', '').lower()
                if query in full_name:
                    self.filtered_data.append(mchd)
            self.search_result_label.config(text=f"Найдено: {len(self.filtered_data)} из {len(self.mchd_data)}")
        self.refresh_table()

    def clear_search(self):
        self.search_var.set("")
        self.filtered_data = self.mchd_data.copy()
        self.search_result_label.config(text="")
        self.refresh_table()

    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.populate_table_with_data(self.filtered_data)

    def sort_column(self, col):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        if col in ("Дата выдачи", "Срок действия"):
            def parse_date(date_str):
                try:
                    if date_str and date_str not in ('Не найдена', 'Не найден', ''):
                        return datetime.strptime(date_str, '%d.%m.%Y')
                except:
                    pass
                return datetime.min

            data.sort(key=lambda x: parse_date(x[0]), reverse=self.sort_reverse[col])
        elif col == "ФИО":
            data.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse[col])
        elif col == "Коды полномочий":
            data.sort(key=lambda x: len(x[0]) if x[0] != 'Нет кодов' else 0, reverse=self.sort_reverse[col])
        else:
            data.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse[col])
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
        self.sort_reverse[col] = not self.sort_reverse[col]

    def check_for_duplicates(self):
        persons = {}
        for mchd in self.mchd_data:
            person = mchd.get('full_name', 'Неизвестно')
            if person not in persons:
                persons[person] = []
            persons[person].append(mchd)
        duplicates = {p: m for p, m in persons.items() if len(m) > 1 and p != 'Не найдено'}
        if duplicates:
            msg = "Найдены люди с несколькими МЧД:\n"
            for person, mchds in duplicates.items():
                msg += f"• {person} - {len(mchds)} МЧД\n"
            msg += "\nВы можете выделить их в таблице и нажать 'Объединить выбранные МЧД' или 'Просмотр кодов'"
            info_label = ttk.Label(self.duplicate_frame, text=msg,
                                   font=('Segoe UI', 9), foreground=MCHD_COLOR,
                                   wraplength=1300)
            info_label.pack()

    def populate_table(self):
        self.populate_table_with_data(self.mchd_data)

    def populate_table_with_data(self, data):
        persons = {}
        for mchd in self.mchd_data:
            person = mchd.get('full_name', 'Неизвестно')
            if person not in persons:
                persons[person] = []
            persons[person].append(mchd)
        duplicate_names = {p for p, m in persons.items() if len(m) > 1 and p != 'Не найдено'}
        for mchd in data:
            tags = []
            if mchd.get('status') == "Просрочен":
                tags.append('expired')
            elif mchd.get('status') and "Истекает" in mchd.get('status', ''):
                tags.append('warning')
            else:
                tags.append('normal')
            person = mchd.get('full_name', '')
            if person in duplicate_names:
                tags.append('duplicate_name')
            auth_codes = ', '.join(mchd.get('authority_codes', []))
            if len(auth_codes) > 50:
                auth_codes = auth_codes[:50] + '...'
            if not mchd.get('authority_codes'):
                auth_codes = 'Нет кодов'
            self.tree.insert("", tk.END, values=(
                os.path.basename(mchd.get('file_name', '')),
                mchd.get('doc_number', ''),
                mchd.get('issue_date', ''),
                mchd.get('expiry_date', ''),
                mchd.get('full_name', ''),
                auth_codes,
                mchd.get('status', '')
            ), tags=tuple(tags))

    def on_select(self, event):
        self.selected_items = self.tree.selection()
        count = len(self.selected_items)
        self.selected_info_label.config(text=f"Выбрано: {count} МЧД")
        selected_mchd = self.get_selected_mchd_objects()

        if count >= 1:
            persons = set(m.get('full_name', '') for m in selected_mchd)
            if count >= 2 and len(persons) == 1:
                self.merge_btn.config(state=tk.NORMAL)
                self.view_auth_btn.config(state=tk.NORMAL)
                self.view_personal_btn.config(state=tk.DISABLED)
                self.person_info_label.config(text=f"ФИО: {list(persons)[0]} (можно объединить)")
            elif count == 1:
                self.merge_btn.config(state=tk.DISABLED)
                self.view_auth_btn.config(state=tk.NORMAL)
                self.view_personal_btn.config(state=tk.NORMAL)
                self.person_info_label.config(text=f"ФИО: {list(persons)[0] if persons else ''}")
            else:
                self.merge_btn.config(state=tk.DISABLED)
                self.view_auth_btn.config(state=tk.NORMAL)
                self.view_personal_btn.config(state=tk.DISABLED)
                if len(persons) > 1:
                    self.person_info_label.config(text="Выбраны разные люди! Объединение невозможно")
                else:
                    self.person_info_label.config(text=f"ФИО: {list(persons)[0] if persons else ''}")
        else:
            self.merge_btn.config(state=tk.DISABLED)
            self.view_auth_btn.config(state=tk.DISABLED)
            self.view_personal_btn.config(state=tk.DISABLED)
            self.person_info_label.config(text="")
        self.update_codes_list()

    def get_selected_mchd_objects(self):
        selected_mchd = []
        for item in self.selected_items:
            values = self.tree.item(item)['values']
            if not values:
                continue
            file_name = values[0]
            for mchd in self.filtered_data:
                if os.path.basename(mchd.get('file_name', '')) == file_name:
                    selected_mchd.append(mchd)
                    break
        return selected_mchd

    def view_merged_authorities(self):
        selected_mchd = self.get_selected_mchd_objects()
        if not selected_mchd:
            messagebox.showwarning("Внимание", "Выберите МЧД для просмотра")
            return
        merged_data = MCHDMerger.get_merged_authorities(selected_mchd)
        if merged_data:
            AuthoritiesViewWindow(self.window, merged_data)
        else:
            messagebox.showerror("Ошибка", "Не удалось получить данные о полномочиях")

    def update_codes_list(self):
        self.codes_listbox.delete(0, tk.END)
        if not self.selected_items:
            self.codes_listbox.insert(tk.END, "Выберите МЧД в таблице")
            return
        selected_mchd = self.get_selected_mchd_objects()
        all_codes = set()
        for mchd in selected_mchd:
            codes = mchd.get('authority_codes', [])
            all_codes.update(codes)
        if all_codes:
            for code in sorted(all_codes):
                self.codes_listbox.insert(tk.END, code)
            self.codes_listbox.insert(tk.END, "")
            self.codes_listbox.insert(tk.END, f"ВСЕГО УНИКАЛЬНЫХ КОДОВ: {len(all_codes)}")
        else:
            self.codes_listbox.insert(tk.END, "Нет кодов полномочий")

    def merge_selected(self):
        if len(self.selected_items) < 2:
            messagebox.showwarning("Внимание", "Выберите минимум 2 МЧД для объединения")
            return
        selected_mchd = self.get_selected_mchd_objects()
        if len(selected_mchd) < 2:
            messagebox.showerror("Ошибка", "Не удалось найти выбранные файлы")
            return
        persons = set(m.get('full_name', '') for m in selected_mchd)
        if len(persons) > 1:
            messagebox.showerror("Ошибка", "Нельзя объединять МЧД разных людей!")
            return
        merged_data = MCHDMerger.get_merged_authorities(selected_mchd)
        response = messagebox.askyesnocancel("Объединение МЧД",
                                             f"Выбрано {len(selected_mchd)} МЧД для {list(persons)[0]}\n"
                                             f"Уникальных кодов: {merged_data.get('unique_codes_count', 0)}\n\n"
                                             "Нажмите 'Да' чтобы создать объединенный XML файл,\n"
                                             "'Нет' чтобы только просмотреть коды,\n"
                                             "'Отмена' для отмены.")
        if response is None:
            return
        if response:
            person_name = list(persons)[0].replace(' ', '_')
            default_name = f"Объединенная_МЧД_{person_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xml",
                filetypes=[("XML файлы", "*.xml"), ("Все файлы", "*.*")],
                initialdir=os.path.dirname(selected_mchd[0].get('file_name', '')),
                initialfile=default_name,
                title="Сохранить объединенную МЧД"
            )
            if not save_path:
                return
            result = MCHDMerger.merge_mchd_files(selected_mchd, save_path)
            if result and os.path.exists(result):
                messagebox.showinfo("Успех",
                                    f"МЧД успешно объединены!\n\n"
                                    f"ФИО: {list(persons)[0]}\n"
                                    f"Всего уникальных кодов: {merged_data.get('unique_codes_count', 0)}\n"
                                    f"Файл сохранен:\n{result}")
                if messagebox.askyesno("Открыть папку", "Открыть папку с объединенным файлом?"):
                    os.startfile(os.path.dirname(result))
            else:
                messagebox.showerror("Ошибка", "Не удалось объединить МЧД")
        else:
            if merged_data:
                AuthoritiesViewWindow(self.window, merged_data)

    def copy_selected_codes(self):
        codes = []
        for i in range(self.codes_listbox.size()):
            text = self.codes_listbox.get(i)
            if text and not text.startswith(
                    "ВСЕГО") and text != "Нет кодов полномочий" and text != "Выберите МЧД в таблице" and text != "":
                codes.append(text)
        if codes:
            pyperclip.copy("\n".join(codes))
            messagebox.showinfo("Успех", f"Скопировано {len(codes)} кодов")
        else:
            messagebox.showwarning("Внимание", "Нет кодов для копирования")

    def on_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item)['values']
        if not values:
            return
        file_name = values[0]
        for mchd in self.filtered_data:
            if os.path.basename(mchd.get('file_name', '')) == file_name:
                full_path = mchd.get('file_name')
                if full_path and os.path.exists(full_path):
                    try:
                        os.startfile(full_path)
                    except Exception as e:
                        messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
                break

    def export_to_excel(self):
        if not self.filtered_data:
            messagebox.showerror("Ошибка", "Нет данных для экспорта!")
            return
        try:
            default_name = f"mchd_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel файлы", "*.xlsx"), ("Все файлы", "*.*")],
                initialdir=EXPORT_FOLDER,
                initialfile=default_name,
                title="Сохранить отчет МЧД"
            )
            if not save_path:
                return
            wb = Workbook()
            ws = wb.active
            ws.title = "МЧД"
            ws.merge_cells('A1:G1')
            title_cell = ws.cell(row=1, column=1)
            title_cell.value = "Отчет по машиночитаемым доверенностям (МЧД)"
            title_cell.font = Font(size=14, bold=True, color="6c5ce7")
            title_cell.alignment = Alignment(horizontal='center', vertical='center')
            ws.merge_cells('A2:G2')
            date_cell = ws.cell(row=2, column=1)
            date_cell.value = f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            date_cell.font = Font(size=10, italic=True)
            date_cell.alignment = Alignment(horizontal='center', vertical='center')
            headers = ["Файл", "Номер доверенности", "Дата выдачи", "Срок действия",
                       "ФИО", "Коды полномочий", "Статус"]
            ws.append(headers)
            header_fill = PatternFill(start_color="6c5ce7", end_color="6c5ce7", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            alignment = Alignment(horizontal='left', vertical='center')
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                 top=Side(style='thin'), bottom=Side(style='thin'))
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=3, column=col)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = alignment
                cell.border = thin_border
            for mchd in self.filtered_data:
                auth_codes = ', '.join(mchd.get('authority_codes', [])) if mchd.get('authority_codes') else 'Нет'
                status = mchd.get('status', '')
                ws.append([
                    os.path.basename(mchd.get('file_name', '')),
                    mchd.get('doc_number', ''),
                    mchd.get('issue_date', ''),
                    mchd.get('expiry_date', ''),
                    mchd.get('full_name', ''),
                    auth_codes,
                    status
                ])
                row = ws.max_row
                for col in range(1, len(headers) + 1):
                    ws.cell(row=row, column=col).alignment = alignment
                    ws.cell(row=row, column=col).border = thin_border
                    if "Просрочен" in status:
                        ws.cell(row=row, column=col).fill = PatternFill(start_color="f5c6cb", end_color="f5c6cb",
                                                                        fill_type="solid")
                        ws.cell(row=row, column=col).font = Font(color="721c24")
                    elif "Истекает" in status:
                        ws.cell(row=row, column=col).fill = PatternFill(start_color="ffeeba", end_color="ffeeba",
                                                                        fill_type="solid")
                        ws.cell(row=row, column=col).font = Font(color="856404")
                    elif "Действует" in status:
                        ws.cell(row=row, column=col).fill = PatternFill(start_color="c3e6cb", end_color="c3e6cb",
                                                                        fill_type="solid")
                        ws.cell(row=row, column=col).font = Font(color="155724")
            for col in ws.columns:
                max_length = 0
                column_letter = get_column_letter(col[0].column)
                for cell in col:
                    try:
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            wb.save(save_path)
            messagebox.showinfo("Успех", f"Отчет сохранен:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать в Excel:\n{str(e)}")


class CertificateAnalyzerService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = SERVICE_DISPLAY_NAME

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        config_file = os.path.join(os.path.dirname(__file__), "service_config.json")
        if not os.path.exists(config_file):
            return
        with open(config_file, 'r') as f:
            config = json.load(f)
        scan_folder = config.get("scan_folder")
        export_path = config.get("export_path")
        core = CertificateAnalyzerCore()
        while self.is_running:
            try:
                files = core.scan_certificates(scan_folder)
                if files:
                    results = core.parse_certificates()
                    core.export_to_excel(results, export_path)
            except Exception as e:
                pass
            for i in range(0, CHECK_INTERVAL, 60):
                if not self.is_running:
                    break
                time.sleep(60)


class CertificateAnalyzerCore:
    def __init__(self):
        self.loaded_files = []
        self.current_folder = ""
        self.cert_stats = {'expired': 0, 'warning': 0, 'normal': 0}
        self.expired_certs = []
        self.warning_certs = []
        self.export_folder = EXPORT_FOLDER
        if not os.path.exists(self.export_folder):
            os.makedirs(self.export_folder)
        self.mchd_folder = os.path.join(os.path.expanduser("~"), "MCHD")
        self.phonebook = PhoneBook()

    def load_phonebook(self, file_path):
        if file_path.lower().endswith('.docx'):
            success = self.phonebook.load_from_docx(file_path)
        else:
            success = self.phonebook.load_from_txt(file_path)
        
        if success:
            return True
        return False

    def get_phone_for_cert(self, cert_info):
        return self.phonebook.get_phone_for_cert(cert_info)

    def scan_certificates(self, folder_path=None):
        cert_extensions = ('.cer', '.crt', '.der', '.pem')
        self.loaded_files = []
        folder_to_scan = folder_path if folder_path else os.path.join(os.path.expanduser("~"), "Certs")
        self.current_folder = folder_to_scan
        if not os.path.exists(folder_to_scan):
            raise FileNotFoundError(f"Папка с сертификатами не найдена: {folder_to_scan}")
        try:
            for root, _, files in os.walk(folder_to_scan):
                for file in files:
                    if file.lower().endswith(cert_extensions):
                        self.loaded_files.append(os.path.join(root, file))
        except Exception as e:
            raise Exception(f"Ошибка сканирования папки: {str(e)}")
        return self.loaded_files

    def scan_mchd_files(self, folder_path=None):
        mchd_extensions = ('.xml',)
        mchd_files = []
        folder_to_scan = folder_path if folder_path else self.mchd_folder
        if not os.path.exists(folder_to_scan):
            try:
                os.makedirs(folder_to_scan)
            except:
                pass
            return []
        try:
            for root, _, files in os.walk(folder_to_scan):
                for file in files:
                    if file.lower().endswith(mchd_extensions):
                        full_path = os.path.join(root, file)
                        mchd_files.append(full_path)
        except Exception as e:
            raise Exception(f"Ошибка сканирования папки МЧД: {str(e)}")
        return mchd_files

    def parse_certificates(self):
        if not self.loaded_files:
            raise Exception("Нет загруженных файлов для анализа")
        self.cert_stats = {'expired': 0, 'warning': 0, 'normal': 0}
        self.expired_certs = []
        self.warning_certs = []
        results = []
        for file_path in self.loaded_files:
            try:
                cert_info = self.extract_certificate_info(file_path)
                if "error" not in cert_info:
                    phone = self.get_phone_for_cert(cert_info)
                    cert_info['phone'] = phone
                    results.append(cert_info)
                    expiry_date = datetime.strptime(cert_info['valid_to'], '%d.%m.%Y')
                    today = datetime.now()
                    days_left = (expiry_date - today).days
                    cert_data = {
                        'name': os.path.basename(cert_info['file_name']),
                        'expiry_date': cert_info['valid_to'],
                        'subject': cert_info['subject_cn'],
                        'status': cert_info['status']
                    }
                    if expiry_date < today:
                        self.cert_stats['expired'] += 1
                        self.expired_certs.append(cert_data)
                    elif days_left <= 60:
                        self.cert_stats['warning'] += 1
                        self.warning_certs.append(cert_data)
                    else:
                        self.cert_stats['normal'] += 1
            except Exception as e:
                raise Exception(f"Ошибка обработки файла {file_path}: {str(e)}")
        return results

    def extract_certificate_info(self, cert_path):
        try:
            with open(cert_path, 'rb') as cert_file:
                cert_data = cert_file.read()
            try:
                cert = x509.load_der_x509_certificate(cert_data, default_backend())
            except:
                if b'-----BEGIN CERTIFICATE-----' in cert_data:
                    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                else:
                    raise ValueError("Неизвестный формат сертификата")
            subject_cn = ""
            email = ""
            office_numbers = []
            departments = []
            for attribute in cert.subject:
                if attribute.oid == NameOID.COMMON_NAME:
                    subject_cn = attribute.value
                elif attribute.oid == NameOID.EMAIL_ADDRESS:
                    email = attribute.value
                elif attribute.oid == NameOID.ORGANIZATIONAL_UNIT_NAME:
                    ou_value = attribute.value
                    if re.search(r'\d+', ou_value):
                        office_numbers.append(ou_value)
                    else:
                        departments.append(ou_value)
            office_number = ', '.join(office_numbers) if office_numbers else '—'
            department = ', '.join(departments) if departments else '—'
            valid_from = cert.not_valid_before_utc.replace(tzinfo=None)
            valid_to = cert.not_valid_after_utc.replace(tzinfo=None)
            today = datetime.now()
            days_left = (valid_to - today).days
            if valid_to < today:
                status = "Просрочен"
                color = EXPIRED_COLOR
            elif days_left <= 60:
                status = f"Истекает ({days_left} дн.)"
                color = WARNING_COLOR
            else:
                status = "Активен"
                color = NORMAL_COLOR
            return {
                'file_name': cert_path,
                'file_type': 'Сертификат',
                'valid_from': valid_from.strftime('%d.%m.%Y'),
                'valid_to': valid_to.strftime('%d.%m.%Y'),
                'subject_cn': subject_cn,
                'serial_number': hex(cert.serial_number)[2:].upper(),
                'email': email or "—",
                'status': status,
                'color': color,
                'office_number': office_number,
                'department': department,
                'phone': '—'
            }
        except Exception as e:
            return {"error": f"Ошибка в файле {os.path.basename(cert_path)}: {str(e)}"}

    def export_to_excel(self, certs, save_path=None, report_title="Отчет"):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Данные"
            ws.merge_cells('A1:K1')
            title_cell = ws.cell(row=1, column=1)
            title_cell.value = report_title
            title_cell.font = Font(size=14, bold=True, color="6c5ce7")
            title_cell.alignment = Alignment(horizontal='center', vertical='center')
            ws.merge_cells('A2:K2')
            date_cell = ws.cell(row=2, column=1)
            date_cell.value = f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
            date_cell.font = Font(size=10, italic=True)
            date_cell.alignment = Alignment(horizontal='center', vertical='center')
            ws.merge_cells('A3:K3')
            info_cell = ws.cell(row=3, column=1)
            info_cell.value = f"Источник: {report_title.replace('Отчет по сертификатам ', '')}"
            info_cell.font = Font(size=10, bold=True, color="6c5ce7")
            info_cell.alignment = Alignment(horizontal='center', vertical='center')
            headers = ["Тип", "Файл", "Действ. с", "Действ. до", "ФИО", "Номер", "Email", "Кабинет", "Подразделение",
                       "Телефон", "Статус"]
            ws.append(headers)
            header_fill = PatternFill(start_color="6c5ce7", end_color="6c5ce7", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            alignment = Alignment(horizontal='left', vertical='center')
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                                 top=Side(style='thin'), bottom=Side(style='thin'))
            for col in range(1, len(headers) + 1):
                cell = ws.cell(row=4, column=col)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = alignment
                cell.border = thin_border
            for cert in certs:
                status = cert.get('status', '')
                ws.append([
                    cert.get('file_type', 'Сертификат'),
                    os.path.basename(cert.get('file_name', '')),
                    cert.get('valid_from', ''),
                    cert.get('valid_to', ''),
                    cert.get('subject_cn', ''),
                    cert.get('serial_number', ''),
                    cert.get('email', '—'),
                    cert.get('office_number', '—'),
                    cert.get('department', '—'),
                    cert.get('phone', '—'),
                    status
                ])
                row = ws.max_row
                for col in range(1, len(headers) + 1):
                    ws.cell(row=row, column=col).alignment = alignment
                    ws.cell(row=row, column=col).border = thin_border
                    if "Просрочен" in status:
                        ws.cell(row=row, column=col).fill = PatternFill(start_color="f5c6cb", end_color="f5c6cb",
                                                                        fill_type="solid")
                        ws.cell(row=row, column=col).font = Font(color="721c24")
                    elif "Истекает" in status:
                        ws.cell(row=row, column=col).fill = PatternFill(start_color="ffeeba", end_color="ffeeba",
                                                                        fill_type="solid")
                        ws.cell(row=row, column=col).font = Font(color="856404")
                    elif "Активен" in status:
                        ws.cell(row=row, column=col).fill = PatternFill(start_color="c3e6cb", end_color="c3e6cb",
                                                                        fill_type="solid")
                        ws.cell(row=row, column=col).font = Font(color="155724")
            for col in ws.columns:
                max_length = 0
                column_letter = get_column_letter(col[0].column)
                for cell in col:
                    try:
                        if cell.value and len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width
            if not save_path:
                report_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                save_path = os.path.join(self.export_folder, report_name)
            wb.save(save_path)
            return save_path
        except Exception as e:
            raise Exception(f"Ошибка экспорта в Excel: {str(e)}")

    def export_to_pdf(self, certs, save_path=None, figure=None, report_title="Отчет", include_chart=True):
        try:
            if not save_path:
                report_name = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                save_path = os.path.join(self.export_folder, report_name)
            doc = SimpleDocTemplate(save_path, pagesize=landscape(letter),
                                    leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                                    topMargin=0.5 * inch, bottomMargin=0.5 * inch)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('TitleStyle', parent=styles['Title'],
                                         fontName=f'{PDF_FONT}-Bold' if PDF_FONT == 'Arial' else 'Helvetica-Bold',
                                         fontSize=14, spaceAfter=10, alignment=1,
                                         textColor=colors.HexColor("#6c5ce7"))
            subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'],
                                            fontName=PDF_FONT, fontSize=10, alignment=1, spaceAfter=20)
            normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'],
                                          fontName=PDF_FONT, fontSize=7, leading=8)
            table_header_style = ParagraphStyle('TableHeader', parent=styles['Normal'],
                                                fontName=f'{PDF_FONT}-Bold' if PDF_FONT == 'Arial' else 'Helvetica-Bold',
                                                fontSize=7, textColor=colors.white)
            elements = []
            elements.append(Paragraph(report_title, title_style))
            elements.append(
                Paragraph(f"Источник: {report_title.replace('Отчет по сертификатам ', '')}", subtitle_style))
            elements.append(Paragraph(f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", subtitle_style))
            elements.append(Spacer(1, 8))
            total = len(certs) if certs else 0
            normal_count = len([c for c in certs if (c.get('status') == 'Активен') and 'Истекает' not in c.get('status',
                                                                                                               '')]) if certs else 0
            warning_count = len([c for c in certs if 'Истекает' in c.get('status', '')]) if certs else 0
            expired_count = len([c for c in certs if c.get('status') == 'Просрочен']) if certs else 0
            stats_text = f"<b>Статистика:</b><br/>Всего: {total} | Активные: {normal_count} | Истекают: {warning_count} | Просрочены: {expired_count}"
            elements.append(Paragraph(stats_text, normal_style))
            elements.append(Spacer(1, 10))
            if include_chart and figure:
                try:
                    imgdata = io.BytesIO()
                    figure.savefig(imgdata, format='png', dpi=100, bbox_inches='tight')
                    imgdata.seek(0)
                    img = Image(imgdata, width=5 * inch, height=2.5 * inch)
                    elements.append(img)
                    elements.append(Spacer(1, 10))
                except Exception as e:
                    print(f"Ошибка при добавлении графика в PDF: {e}")
            if certs:
                table_data = []
                headers = ["Тип", "Файл", "С", "По", "ФИО", "Номер", "Email", "Каб.", "Подр.", "Телефон", "Статус"]
                table_data.append([Paragraph(h, table_header_style) for h in headers])
                for cert in certs:
                    phone = cert.get('phone', '—')
                    if len(phone) > 15:
                        phone = phone[:12] + '...'
                    table_data.append([
                        Paragraph(cert.get('file_type', 'Серт')[:3], normal_style),
                        Paragraph(os.path.basename(cert['file_name'])[:15], normal_style),
                        Paragraph(cert.get('valid_from', '')[:10], normal_style),
                        Paragraph(cert.get('valid_to', '')[:10], normal_style),
                        Paragraph(cert.get('subject_cn', '')[:20], normal_style),
                        Paragraph(cert.get('serial_number', '')[:10], normal_style),
                        Paragraph(cert.get('email', '—')[:12], normal_style),
                        Paragraph(cert.get('office_number', '—')[:5], normal_style),
                        Paragraph(cert.get('department', '—')[:10], normal_style),
                        Paragraph(phone[:15], normal_style),
                        Paragraph(cert.get('status', '')[:15], normal_style)
                    ])
                col_widths = [0.4, 1.0, 0.6, 0.6, 1.5, 0.8, 0.8, 0.5, 0.8, 0.8, 0.8]
                col_widths = [w * inch for w in col_widths]
                cert_table = Table(table_data, repeatRows=1, colWidths=col_widths)
                cert_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(ACCENT_COLOR)),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]))
                for i, cert in enumerate(certs, start=1):
                    if cert.get('status') == "Просрочен":
                        bg_color = colors.HexColor(EXPIRED_COLOR)
                    elif "Истекает" in cert.get('status', ''):
                        bg_color = colors.HexColor(WARNING_COLOR)
                    else:
                        bg_color = colors.HexColor(NORMAL_COLOR)
                    cert_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), bg_color)]))
                elements.append(cert_table)
            doc.build(elements)
            return save_path
        except Exception as e:
            raise Exception(f"Ошибка экспорта в PDF: {str(e)}")


class CertificateAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Анализатор сертификатов и МЧД")
        self.root.geometry("1600x900")
        self.root.configure(bg=BG_COLOR)
        self.current_folder_key = "📁 Сотрудники"
        self.current_display_path = ""
        self.recent_folders = []
        self.setup_styles()
        self.core = CertificateAnalyzerCore()
        self.cert_data_cache = []
        self.mchd_data_cache = []
        self.mchd_parser = MCHDParser()
        self.current_display_mode = "certificates"
        self.search_active = False
        self.current_search_query = ""
        self.date_filter_active = False
        self.date_from = None
        self.date_to = None
        self._notification_shown = False
        self.chart_type = "pie"
        self.open_windows = {}
        self.setup_ui()
        self.load_default_folder()
        self.setup_folder_menu()
        self.setup_push_notifications()
        self.root.bind("<Configure>", self.on_window_resize)
        self.tree.bind("<Double-1>", self.on_item_double_click)
        self.cal.bind("<<CalendarMonthChanged>>", self.on_month_change)
        self.notification_history = NotificationHistory(root)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background=BG_COLOR, foreground=TEXT_COLOR, font=('Segoe UI', 9))
        self.root.configure(bg=BG_COLOR)
        style.configure('TFrame', background=BG_COLOR)
        style.configure('TLabelFrame', background=HEADER_COLOR, foreground=TEXT_COLOR,
                        font=('Segoe UI', 10, 'bold'), borderwidth=2, relief='groove')
        style.configure('TLabelFrame.Label', background=HEADER_COLOR, foreground=TEXT_COLOR)
        style.configure('TButton', background=BUTTON_COLOR, foreground='white',
                        font=('Segoe UI', 9, 'bold'), borderwidth=0, padding=8)
        style.map('TButton', background=[('active', BUTTON_HOVER), ('pressed', BUTTON_HOVER)],
                  foreground=[('active', 'white')])
        style.configure('Accent.TButton', background=BUTTON_COLOR, foreground='white',
                        font=('Segoe UI', 9, 'bold'), borderwidth=0, padding=8)
        style.map('Accent.TButton', background=[('active', BUTTON_HOVER), ('pressed', BUTTON_HOVER)],
                  foreground=[('active', 'white')])
        style.configure('Sidebar.TButton', background=SIDEBAR_COLOR, foreground=SIDEBAR_TEXT_COLOR,
                        font=('Segoe UI', 10), borderwidth=0, padding=8)
        style.map('Sidebar.TButton', background=[('active', '#34495e'), ('pressed', '#2c3e50')],
                  foreground=[('active', 'white')])
        style.configure('TEntry', fieldbackground='white', foreground=TEXT_COLOR,
                        insertcolor=TEXT_COLOR, bordercolor='#e1e8ed', borderwidth=1,
                        padding=5, font=('Segoe UI', 9))
        style.configure('Treeview', background='white', foreground=TEXT_COLOR,
                        fieldbackground='white', rowheight=28, borderwidth=0,
                        font=('Segoe UI', 9))
        style.configure('Treeview.Heading', background=ACCENT_COLOR, foreground='white',
                        font=('Segoe UI', 9, 'bold'), borderwidth=0)
        style.map('Treeview', background=[('selected', BUTTON_COLOR)],
                  foreground=[('selected', 'white')])
        style.configure('Card.TFrame', background=CARD_BG_COLOR, borderwidth=1, relief='solid',
                        bordercolor=CARD_BORDER_COLOR)
        style.configure('CardTitle.TLabel', font=('Segoe UI', 9), foreground=CARD_TITLE_COLOR,
                        background=CARD_BG_COLOR)
        style.configure('CardValue.TLabel', font=('Segoe UI', 14), foreground=CARD_VALUE_COLOR,
                        background=CARD_BG_COLOR)
        style.configure('Sidebar.TFrame', background=SIDEBAR_COLOR)
        style.configure('TCheckbutton', background=BG_COLOR, foreground=TEXT_COLOR, font=('Segoe UI', 9))

    def close_window(self, key, window):
        self.open_windows[key] = None
        window.destroy()

    def show_window(self, window_key, window_class, *args, **kwargs):
        if window_key in self.open_windows and self.open_windows[window_key] is not None:
            try:
                if self.open_windows[window_key].winfo_exists():
                    self.open_windows[window_key].lift()
                    self.open_windows[window_key].focus_force()
                    return self.open_windows[window_key]
            except:
                pass
        window = window_class(*args, **kwargs)
        self.open_windows[window_key] = window
        if hasattr(window, 'protocol'):
            def on_close():
                self.open_windows[window_key] = None
                if hasattr(window, 'destroy'):
                    window.destroy()

            window.protocol("WM_DELETE_WINDOW", on_close)
        return window

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        sidebar_frame = ttk.Frame(main_frame, width=260, style='Sidebar.TFrame')
        sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar_frame.pack_propagate(False)

        logo_frame = ttk.Frame(sidebar_frame, style='Sidebar.TFrame')
        logo_frame.pack(fill=tk.X, pady=(10, 20))

        ttk.Label(logo_frame, text="🔐", font=('Segoe UI', 28),
                  foreground='white', background=SIDEBAR_COLOR).pack(pady=(10, 0))
        ttk.Label(logo_frame, text="Анализатор", font=('Segoe UI', 14, 'bold'),
                  foreground='white', background=SIDEBAR_COLOR).pack()
        ttk.Label(logo_frame, text="Сертификатов и МЧД", font=('Segoe UI', 9),
                  foreground=SIDEBAR_TEXT_COLOR, background=SIDEBAR_COLOR).pack()

        nav_buttons = [
            ("📁 Сотрудники", lambda: self.switch_folder("📁 Сотрудники")),
            ("📁 Руководство", lambda: self.switch_folder("📁 Руководство")),
            ("📁 МЧД", self.scan_mchd_folder),
            ("📤 Экспорт", self.export_menu),
            ("⚙️ Служба", self.service_menu),
            ("📞 Загрузить справочник", self.load_phonebook),
        ]

        for text, command in nav_buttons:
            btn = ttk.Button(sidebar_frame, text=text, command=command, style='Sidebar.TButton')
            btn.pack(fill=tk.X, padx=10, pady=3, ipady=5)
            self.create_tooltip(btn, text)

        sep = ttk.Separator(sidebar_frame, orient='horizontal')
        sep.pack(fill=tk.X, padx=10, pady=15)

        bottom_buttons = [
            ("📋 История уведомлений", self.show_notification_history),
            ("🔔 Push-уведомления", self.show_notification_settings),
            ("📚 Нормативка", self.show_normative),
            ("ℹ️ О программе", self.show_about),
        ]

        for text, command in bottom_buttons:
            btn = ttk.Button(sidebar_frame, text=text, command=command, style='Sidebar.TButton')
            btn.pack(fill=tk.X, padx=10, pady=3, ipady=5)
            self.create_tooltip(btn, text)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        nav_frame = ttk.Frame(top_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 5))

        back_btn = ttk.Button(nav_frame, text="◀ Назад", command=self.folder_back, style='Accent.TButton', width=10)
        back_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.create_tooltip(back_btn, "Вернуться к предыдущей папке")

        self.folder_path = tk.StringVar()
        folder_entry = ttk.Entry(nav_frame, textvariable=self.folder_path, font=('Segoe UI', 10))
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        select_btn = ttk.Button(nav_frame, text="📂 Выбрать папку", command=self.select_folder, style='Accent.TButton')
        select_btn.pack(side=tk.RIGHT)
        self.create_tooltip(select_btn, "Выбрать другую папку с сертификатами")

        settings_btn = ttk.Button(nav_frame, text="⚙️", command=self.show_folder_settings, style='Accent.TButton',
                                  width=3)
        settings_btn.pack(side=tk.RIGHT, padx=(0, 5))
        self.create_tooltip(settings_btn, "Настройка путей к папкам")

        cards_frame = ttk.Frame(main_frame)
        cards_frame.pack(fill=tk.X, pady=(0, 15))

        self.card_total = self.create_card(cards_frame, "Всего записей", "0")
        self.card_normal = self.create_card(cards_frame, "Активные", "0", GRAPH_NORMAL)
        self.card_warning = self.create_card(cards_frame, "Истекают", "0", GRAPH_WARNING)
        self.card_expired = self.create_card(cards_frame, "Просрочены", "0", GRAPH_EXPIRED)

        content_inner_frame = ttk.Frame(main_frame)
        content_inner_frame.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(content_inner_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        files_frame = ttk.LabelFrame(left_panel, text=" Найденные файлы ", padding=10)
        files_frame.pack(fill=tk.BOTH, pady=(0, 10))

        list_frame = ttk.Frame(files_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        cert_list_frame = ttk.LabelFrame(list_frame, text="Сертификаты", padding=5)
        cert_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.listbox_files = tk.Listbox(cert_list_frame, height=6, selectmode=tk.EXTENDED,
                                        font=('Consolas', 9), bg='white', fg=TEXT_COLOR,
                                        selectbackground=BUTTON_COLOR, selectforeground='white')
        self.listbox_files.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll_files = ttk.Scrollbar(cert_list_frame, orient=tk.VERTICAL, command=self.listbox_files.yview)
        scroll_files.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_files.configure(yscrollcommand=scroll_files.set)

        mchd_list_frame = ttk.LabelFrame(list_frame, text="МЧД", padding=5)
        mchd_list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.listbox_mchd = tk.Listbox(mchd_list_frame, height=6, selectmode=tk.EXTENDED,
                                       font=('Consolas', 9), bg='white', fg=TEXT_COLOR,
                                       selectbackground=BUTTON_COLOR, selectforeground='white')
        self.listbox_mchd.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll_mchd = ttk.Scrollbar(mchd_list_frame, orient=tk.VERTICAL, command=self.listbox_mchd.yview)
        scroll_mchd.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox_mchd.configure(yscrollcommand=scroll_mchd.set)

        results_frame = ttk.LabelFrame(left_panel, text=" Результаты анализа сертификатов ", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True)

        action_panel = ttk.Frame(results_frame)
        action_panel.pack(fill=tk.X, pady=(0, 10))

        search_frame = ttk.Frame(action_panel)
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(search_frame, text="🔍 Поиск:", font=('Segoe UI', 10)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=(5, 10))

        filter_btn = ttk.Button(search_frame, text="📅 Фильтр по дате", command=self.show_date_filter,
                                style='Accent.TButton', width=14)
        filter_btn.pack(side=tk.LEFT, padx=5)
        self.create_tooltip(filter_btn, "Фильтр сертификатов по дате окончания")

        delete_btn = ttk.Button(action_panel, text="🗑 Удалить", command=self.delete_selected, 
                                style='Accent.TButton', width=10)
        delete_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self.create_tooltip(delete_btn, "Удалить выбранные файлы с диска")

        refresh_btn = ttk.Button(action_panel, text="🔄 Обновить", command=self.refresh_all, 
                                 style='Accent.TButton', width=10)
        refresh_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self.create_tooltip(refresh_btn, "Обновить список файлов и данные")

        self.search_result_label = ttk.Label(action_panel, text="",
                                             font=('Segoe UI', 9, 'italic'),
                                             foreground=ACCENT_COLOR)
        self.search_result_label.pack(side=tk.RIGHT, padx=(10, 0))

        self.current_folder_label = ttk.Label(action_panel,
                                              text=f"Текущая: {self.current_folder_key}",
                                              font=('Segoe UI', 9, 'italic'),
                                              foreground=ACCENT_COLOR)
        self.current_folder_label.pack(side=tk.RIGHT, padx=(10, 0))

        tree_frame = ttk.Frame(results_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.columns = ("Тип", "Файл", "С", "По", "ФИО", "Номер", "Email",
                        "Кабинет", "Подразделение", "Телефон", "Статус")

        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings", height=15)

        col_widths = [50, 150, 85, 85, 160, 110, 110, 85, 110, 120, 110]
        for col, width in zip(self.columns, col_widths):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_column(c))
            self.tree.column(col, width=width, anchor=tk.W, stretch=True, minwidth=50)

        scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.tag_configure('expired', background=EXPIRED_COLOR, foreground=EXPIRED_TEXT)
        self.tree.tag_configure('warning', background=WARNING_COLOR, foreground=WARNING_TEXT)
        self.tree.tag_configure('normal', background=NORMAL_COLOR, foreground=NORMAL_TEXT)
        self.tree.tag_configure('duplicate', background='#fff3cd', foreground='black')

        right_panel = ttk.Frame(content_inner_frame, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH)

        calendar_frame = ttk.LabelFrame(right_panel, text=" 📅 Календарь окончаний ", padding=10)
        calendar_frame.pack(fill=tk.BOTH, pady=(0, 10))

        cal_controls_frame = ttk.Frame(calendar_frame)
        cal_controls_frame.pack(fill=tk.X, pady=(0, 5))

        today_btn = ttk.Button(cal_controls_frame, text="Сегодня", command=self.show_today, style='Accent.TButton',
                               width=8)
        today_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.create_tooltip(today_btn, "Показать сегодняшнюю дату в календаре")

        prev_btn = ttk.Button(cal_controls_frame, text="◀", command=self.prev_month, style='Accent.TButton', width=3)
        prev_btn.pack(side=tk.LEFT, padx=(0, 5))

        next_btn = ttk.Button(cal_controls_frame, text="▶", command=self.next_month, style='Accent.TButton', width=3)
        next_btn.pack(side=tk.LEFT)

        try:
            self.cal = Calendar(calendar_frame, selectmode='day', date_pattern='dd.mm.yyyy',
                                firstweekday='monday', showweeknumbers=False,
                                weekendbackground='#f5f5f5', weekendforeground='#666666',
                                othermonthbackground='#f9f9f9', othermonthforeground='#cccccc',
                                bordercolor=CARD_BORDER_COLOR, selectbackground=BUTTON_COLOR,
                                selectforeground='white', background='white', foreground=TEXT_COLOR,
                                font=('Segoe UI', 9), headersbackground='#f0f0f0',
                                headersforeground=TEXT_COLOR, normalbackground='white',
                                normalforeground=TEXT_COLOR, disabledforeground='#cccccc', locale='ru_RU')
        except:
            self.cal = Calendar(calendar_frame, selectmode='day', date_pattern='dd.mm.yyyy',
                                firstweekday='monday', showweeknumbers=False,
                                weekendbackground='#f5f5f5', weekendforeground='#666666',
                                othermonthbackground='#f9f9f9', othermonthforeground='#cccccc',
                                bordercolor=CARD_BORDER_COLOR, selectbackground=BUTTON_COLOR,
                                selectforeground='white', background='white', foreground=TEXT_COLOR,
                                font=('Segoe UI', 9), headersbackground='#f0f0f0',
                                headersforeground=TEXT_COLOR, normalbackground='white',
                                normalforeground=TEXT_COLOR, disabledforeground='#cccccc')

        self.cal.pack(fill=tk.BOTH, expand=True)
        self.cal.bind("<<CalendarSelected>>", self.on_date_select)

        dashboard_frame = ttk.LabelFrame(right_panel, text=" 📊 Статус документов ", padding=10)
        dashboard_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        chart_options_frame = ttk.Frame(dashboard_frame)
        chart_options_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(chart_options_frame, text="Тип:").pack(side=tk.LEFT, padx=(0, 5))

        self.chart_type_var = tk.StringVar(value="Круговая")
        chart_types = ["Круговая", "Столбчатая", "Линейная", "С областями", "Кольцевая",
                       "Точечная", "Пузырьковая", "Гистограмма с накоплением"]
        chart_combo = ttk.Combobox(chart_options_frame, textvariable=self.chart_type_var,
                                   values=chart_types, state="readonly", width=18)
        chart_combo.pack(side=tk.LEFT, padx=5)
        chart_combo.bind("<<ComboboxSelected>>", self.on_chart_type_change)

        self.include_chart_var = tk.BooleanVar(value=True)
        chart_check = ttk.Checkbutton(chart_options_frame, text="Включать в PDF",
                                      variable=self.include_chart_var)
        chart_check.pack(side=tk.RIGHT)

        self.figure_status = plt.Figure(figsize=(5, 3), dpi=80, facecolor='white')
        self.ax_status = self.figure_status.add_subplot(111)
        self.ax_status.set_facecolor('white')
        self.canvas_status = FigureCanvasTkAgg(self.figure_status, master=dashboard_frame)
        self.canvas_status.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.sort_reverse = {col: False for col in self.columns}
        self.folder_history = []

        self.root.after(1000, self.update_calendar_colors)

    def load_phonebook(self):
        file_path = filedialog.askopenfilename(
            title="Выберите файл справочника",
            filetypes=[("Документы Word", "*.docx"), ("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if file_path:
            if self.core.load_phonebook(file_path):
                self.show_notification(f"Справочник успешно загружен! Найдено {len(self.core.phonebook.data)} записей", "success", 4000)
                self.refresh_all()
            else:
                self.show_notification("Ошибка при загрузке справочника. Проверьте формат файла.", "error", 4000)

    def on_chart_type_change(self, event=None):
        chart_map = {
            "Круговая": "pie",
            "Столбчатая": "bar",
            "Линейная": "line",
            "С областями": "area",
            "Кольцевая": "doughnut",
            "Точечная": "scatter",
            "Пузырьковая": "bubble",
            "Гистограмма с накоплением": "stacked_bar"
        }
        self.chart_type = chart_map.get(self.chart_type_var.get(), "pie")
        self.update_stats()

    def create_tooltip(self, widget, text):
        def show_tooltip(event):
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            frame = tk.Frame(tooltip, bg='#2c3e50', padx=8, pady=4)
            frame.pack()
            label = tk.Label(frame, text=text, font=('Segoe UI', 9),
                             bg='#2c3e50', fg='white', wraplength=300)
            label.pack()

            def hide_tooltip():
                tooltip.destroy()

            widget.tooltip = tooltip
            widget.after(3000, hide_tooltip)
            widget.bind('<Leave>', lambda e: hide_tooltip())

        widget.bind('<Enter>', show_tooltip)

    def show_notification(self, message, notification_type="info", duration=4000):
        try:
            self.notification_history.add_notification(message, notification_type)
            ToastNotification(self.root, message, duration, notification_type)
        except Exception as e:
            print(f"Ошибка показа уведомления: {e}")

    def show_notification_history(self):
        self.notification_history.show_history_window()

    def show_normative(self):
        self.show_window("normative", NormativeWindow, self.root)

    def show_about(self):
        if "about" in self.open_windows and self.open_windows["about"] is not None:
            try:
                if self.open_windows["about"].winfo_exists():
                    self.open_windows["about"].lift()
                    self.open_windows["about"].focus_force()
                    return
            except:
                pass

        about_window = tk.Toplevel(self.root)
        about_window.title("О программе")
        about_window.geometry("550x500")
        about_window.configure(bg=BG_COLOR)
        about_window.resizable(False, False)
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (550 // 2)
        y = (about_window.winfo_screenheight() // 2) - (500 // 2)
        about_window.geometry(f"550x500+{x}+{y}")
        self.open_windows["about"] = about_window

        main_frame = tk.Frame(about_window, bg=CARD_BG_COLOR, relief='flat', bd=0)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        header_bar = tk.Frame(main_frame, bg=MCHD_COLOR, height=80)
        header_bar.pack(fill=tk.X)
        header_bar.pack_propagate(False)

        tk.Label(header_bar, text="🔐", font=('Segoe UI', 32), bg=MCHD_COLOR, fg='white').place(x=20, y=20)
        tk.Label(header_bar, text="Анализатор сертификатов и МЧД",
                 font=('Segoe UI', 16, 'bold'), bg=MCHD_COLOR, fg='white').place(x=80, y=28)
        tk.Label(header_bar, text="Версия 3.1", font=('Segoe UI', 10),
                 bg=MCHD_COLOR, fg='#e1bee7').place(x=80, y=55)

        body_frame = tk.Frame(main_frame, bg=CARD_BG_COLOR)
        body_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        canvas_frame = tk.Frame(body_frame, bg=CARD_BG_COLOR)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(canvas_frame, bg=CARD_BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CARD_BG_COLOR)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        desc_frame = tk.Frame(scrollable_frame, bg=CARD_BG_COLOR)
        desc_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(desc_frame, text="📋 ОПИСАНИЕ", font=('Segoe UI', 11, 'bold'),
                 fg=MCHD_COLOR, bg=CARD_BG_COLOR).pack(anchor=tk.W, pady=(0, 8))
        description = """Программа для анализа сертификатов электронной подписи 
 и машиночитаемых доверенностей (МЧД)."""
        tk.Label(desc_frame, text=description, font=('Segoe UI', 10),
                 fg=TEXT_COLOR, bg=CARD_BG_COLOR, justify=tk.LEFT, wraplength=460).pack(anchor=tk.W, pady=(0, 10))

        functions_frame = tk.Frame(scrollable_frame, bg=CARD_BG_COLOR)
        functions_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(functions_frame, text="⚡ ОСНОВНЫЕ ФУНКЦИИ", font=('Segoe UI', 11, 'bold'),
                 fg=MCHD_COLOR, bg=CARD_BG_COLOR).pack(anchor=tk.W, pady=(0, 8))
        functions = [
            "• Сканирование и анализ сертификатов (.cer, .crt, .der, .pem)",
            "• Анализ XML файлов МЧД",
            "• Объединение нескольких МЧД одного лица",
            "• Отслеживание сроков действия",
            "• Экспорт отчетов в Excel и PDF",
            "• Календарь окончания сертификатов",
            "• Push-уведомления о просроченных сертификатах",
            "• 8 типов диаграмм для визуализации",
            "• Загрузка справочника телефонов для поиска контактов"
        ]
        for func in functions:
            tk.Label(functions_frame, text=func, font=('Segoe UI', 10),
                     fg=TEXT_COLOR, bg=CARD_BG_COLOR, anchor=tk.W).pack(anchor=tk.W, pady=2)

        dev_frame = tk.Frame(scrollable_frame, bg=CARD_BG_COLOR)
        dev_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(dev_frame, text="👨‍💻 РАЗРАБОТКА", font=('Segoe UI', 11, 'bold'),
                 fg=MCHD_COLOR, bg=CARD_BG_COLOR).pack(anchor=tk.W, pady=(0, 8))
        dev_info = """Разработано для внутреннего использования.
 По вопросам и предложениям обращаться в ИБ-отдел."""
        tk.Label(dev_frame, text=dev_info, font=('Segoe UI', 10),
                 fg=TEXT_COLOR, bg=CARD_BG_COLOR, justify=tk.LEFT, wraplength=460).pack(anchor=tk.W)

        copyright_frame = tk.Frame(scrollable_frame, bg=CARD_BG_COLOR)
        copyright_frame.pack(fill=tk.X, pady=(10, 0))
        tk.Label(copyright_frame, text="© 2026 | Все права защищены", font=('Segoe UI', 9, 'italic'),
                 fg=ACCENT_COLOR, bg=CARD_BG_COLOR).pack(anchor=tk.CENTER)

        btn_frame = tk.Frame(main_frame, bg=CARD_BG_COLOR, pady=15)
        btn_frame.pack(fill=tk.X)
        close_btn = tk.Button(btn_frame, text="❌ ЗАКРЫТЬ", command=lambda: self.close_window("about", about_window),
                              font=('Segoe UI', 10, 'bold'), bg=BUTTON_COLOR, fg='white',
                              cursor='hand2', padx=25, pady=8, relief='flat', bd=0)
        close_btn.pack()

        def on_enter(e):
            close_btn.config(bg=BUTTON_HOVER)

        def on_leave(e):
            close_btn.config(bg=BUTTON_COLOR)

        close_btn.bind("<Enter>", on_enter)
        close_btn.bind("<Leave>", on_leave)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def on_destroy():
            canvas.unbind_all("<MouseWheel>")
            self.open_windows["about"] = None
            about_window.destroy()

        about_window.protocol("WM_DELETE_WINDOW", on_destroy)

    def create_card(self, parent, title, value, color=None):
        card = ttk.Frame(parent, style='Card.TFrame', padding=12)
        card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 10))
        ttk.Label(card, text=title, style='CardTitle.TLabel').pack(anchor=tk.W)
        value_label = ttk.Label(card, text=value, style='CardValue.TLabel')
        value_label.pack(anchor=tk.W)
        if color:
            value_label.configure(foreground=color)
        return value_label

    def setup_push_notifications(self):
        self.notification_manager = PushNotificationManager()
        self.load_notification_settings()
        self.start_notification_monitoring()

    def load_notification_settings(self):
        config_file = os.path.join(os.path.dirname(__file__), "notification_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    interval_hours = settings.get('interval_hours', 1)
                    self.notification_manager.set_interval(interval_hours)
                    self.notification_enabled = settings.get('enabled', True)
            except:
                self.notification_enabled = True
        else:
            self.notification_enabled = True

    def save_notification_settings(self):
        config_file = os.path.join(os.path.dirname(__file__), "notification_config.json")
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'interval_hours': self.notification_manager.notification_interval // 3600,
                    'enabled': self.notification_enabled
                }, f, indent=4)
        except:
            pass

    def start_notification_monitoring(self):
        if not self.notification_enabled:
            return

        def check_certificates():
            if not hasattr(self, 'cert_data_cache') or not self.cert_data_cache:
                return
            expired = sum(1 for c in self.cert_data_cache if c.get('status') == "Просрочен")
            warning = sum(1 for c in self.cert_data_cache if "Истекает" in c.get('status', ''))
            total = len(self.cert_data_cache)
            self.notification_manager.check_and_notify_expired(expired, warning, total)

        self.notification_manager.start_background_monitoring(check_certificates, 3600)

    def show_notification_settings(self):
        if "notification_settings" in self.open_windows and self.open_windows["notification_settings"] is not None:
            try:
                if self.open_windows["notification_settings"].winfo_exists():
                    self.open_windows["notification_settings"].lift()
                    self.open_windows["notification_settings"].focus_force()
                    return
            except:
                pass

        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройка push-уведомлений")
        settings_window.geometry("450x380")
        settings_window.configure(bg=BG_COLOR)
        settings_window.resizable(False, False)
        self.open_windows["notification_settings"] = settings_window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (450 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (380 // 2)
        settings_window.geometry(f"450x380+{x}+{y}")

        main_frame = ttk.Frame(settings_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(main_frame, text="🔔 Настройка push-уведомлений",
                  font=('Segoe UI', 14, 'bold')).pack(pady=(0, 15))

        if not TOAST_AVAILABLE:
            ttk.Label(main_frame, text="⚠️ Для уведомлений установите: pip install win10toast",
                      font=('Segoe UI', 9), foreground=EXPIRED_COLOR).pack(pady=(0, 15))

        enabled_frame = ttk.Frame(main_frame)
        enabled_frame.pack(fill=tk.X, pady=5)
        self.notification_enabled_var = tk.BooleanVar(value=self.notification_enabled)
        ttk.Checkbutton(enabled_frame, text="Включить push-уведомления",
                        variable=self.notification_enabled_var,
                        command=self.toggle_notifications).pack(side=tk.LEFT)

        interval_frame = ttk.Frame(main_frame)
        interval_frame.pack(fill=tk.X, pady=15)
        ttk.Label(interval_frame, text="Интервал уведомлений:", font=('Segoe UI', 10)).pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(value=self.notification_manager.notification_interval // 3600)
        ttk.Spinbox(interval_frame, from_=1, to=24, width=5, textvariable=self.interval_var,
                    command=self.update_notification_interval).pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(interval_frame, text="часов").pack(side=tk.LEFT)

        info_frame = ttk.LabelFrame(main_frame, text=" ℹ️ Информация ", padding=10)
        info_frame.pack(fill=tk.X, pady=15)
        info_text = """Push-уведомления будут приходить:
 • При обнаружении просроченных сертификатов
 • При истекающих сертификатах (менее 60 дней)
 • С выбранным интервалом (не чаще)"""
        ttk.Label(info_frame, text=info_text, font=('Segoe UI', 9),
                  foreground=ACCENT_COLOR, wraplength=380).pack()

        ttk.Button(main_frame, text="🔔 Отправить тестовое уведомление",
                   command=self.send_test_notification, style='Accent.TButton').pack(pady=10)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Сохранить", command=lambda: self.save_notification_settings_close(settings_window),
                   style='Accent.TButton').pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Отмена",
                   command=lambda: self.close_window("notification_settings", settings_window),
                   style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

        def on_destroy():
            self.open_windows["notification_settings"] = None
            settings_window.destroy()

        settings_window.protocol("WM_DELETE_WINDOW", on_destroy)

    def toggle_notifications(self):
        self.notification_enabled = self.notification_enabled_var.get()
        if not self.notification_enabled:
            self.notification_manager.stop_monitoring()
        else:
            self.start_notification_monitoring()
        self.save_notification_settings()

    def update_notification_interval(self):
        hours = self.interval_var.get()
        self.notification_manager.set_interval(hours)
        self.save_notification_settings()
        if self.notification_enabled:
            self.notification_manager.stop_monitoring()
            self.start_notification_monitoring()

    def save_notification_settings_close(self, window):
        self.save_notification_settings()
        self.close_window("notification_settings", window)
        self.show_notification("Настройки уведомлений сохранены", "success", 2000)

    def send_test_notification(self):
        if self.notification_manager.send_notification(
                "🔔 Тестовое уведомление",
                "Если вы видите это сообщение, push-уведомления работают корректно!", duration=5):
            self.show_notification("Тестовое уведомление отправлено!", "success", 2000)
        else:
            self.show_notification("Не удалось отправить уведомление. Проверьте настройки.", "error", 3000)

    def update_calendar_colors(self):
        try:
            self.clear_calendar_events()
            current_date = self.cal.get_date()
            current = datetime.strptime(current_date, "%d.%m.%Y")
            current_month = current.month
            current_year = current.year
            day_priority = {}
            for cert in self.cert_data_cache:
                try:
                    cert_date_str = cert.get('valid_to', '')
                    if cert_date_str and cert_date_str not in ('—', 'Не найден', 'Ошибка'):
                        cert_date = datetime.strptime(cert_date_str, '%d.%m.%Y')
                        if cert_date.month == current_month and cert_date.year == current_year:
                            day = cert_date.day
                            status = cert.get('status', '')
                            if status == "Просрочен":
                                priority = 3
                            elif "Истекает" in status:
                                priority = 2
                            else:
                                priority = 1
                            if day not in day_priority or day_priority[day] < priority:
                                day_priority[day] = priority
                except:
                    continue
            for day, priority in day_priority.items():
                date_obj = datetime(current_year, current_month, day).date()
                if priority == 3:
                    self.cal.calevent_create(date_obj, 'Просрочен', 'expired')
                    self.cal.tag_config('expired', background=EXPIRED_COLOR, foreground=EXPIRED_TEXT)
                elif priority == 2:
                    self.cal.calevent_create(date_obj, 'Истекает', 'warning')
                    self.cal.tag_config('warning', background=WARNING_COLOR, foreground=WARNING_TEXT)
                elif priority == 1:
                    self.cal.calevent_create(date_obj, 'Активен', 'normal')
                    self.cal.tag_config('normal', background=NORMAL_COLOR, foreground=NORMAL_TEXT)
            today = datetime.now().date()
            if today.month == current_month and today.year == current_year:
                self.cal.calevent_create(today, 'Сегодня', 'today')
                self.cal.tag_config('today', background='#3498db', foreground='white')
        except Exception as e:
            print(f"Ошибка при обновлении календаря: {e}")

    def clear_calendar_events(self):
        try:
            self.cal.calevent_remove('all')
        except:
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

    def on_item_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self.tree.item(item)['values']
        if not values:
            return
        file_name = values[1]
        for f in self.core.loaded_files:
            if os.path.basename(f) == file_name:
                full_path = f
                if full_path and os.path.exists(full_path):
                    try:
                        os.startfile(full_path)
                    except Exception as e:
                        messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")
                break

    def show_date_filter(self):
        filter_window = tk.Toplevel(self.root)
        filter_window.title("Фильтр по дате")
        filter_window.geometry("450x300")
        filter_window.configure(bg=BG_COLOR)
        filter_window.resizable(False, False)
        frame = ttk.Frame(filter_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Фильтр по дате окончания",
                  font=('Segoe UI', 12, 'bold')).pack(pady=(0, 20))
        from_frame = ttk.Frame(frame)
        from_frame.pack(fill=tk.X, pady=5)
        ttk.Label(from_frame, text="С даты:", width=10).pack(side=tk.LEFT)
        from_date = DateEntry(from_frame, width=12, background=BUTTON_COLOR,
                              foreground='white', borderwidth=2, date_pattern='dd.mm.yyyy')
        from_date.pack(side=tk.LEFT, padx=5)
        to_frame = ttk.Frame(frame)
        to_frame.pack(fill=tk.X, pady=5)
        ttk.Label(to_frame, text="По дату:", width=10).pack(side=tk.LEFT)
        to_date = DateEntry(to_frame, width=12, background=BUTTON_COLOR,
                            foreground='white', borderwidth=2, date_pattern='dd.mm.yyyy')
        to_date.pack(side=tk.LEFT, padx=5)
        ttk.Label(frame, text="Будут показаны документы,\nсрок действия которых попадает в указанный диапазон",
                  font=('Segoe UI', 9, 'italic'), foreground=ACCENT_COLOR, justify=tk.CENTER).pack(pady=20)
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

        ttk.Button(btn_frame, text="Применить", command=apply_filter, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Сбросить", command=clear_filter, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=filter_window.destroy, style='Accent.TButton').pack(side=tk.RIGHT,
                                                                                                         padx=5)

    def apply_date_filter(self):
        if not self.date_filter_active or not self.date_from or not self.date_to:
            return
        filtered_data = []
        for item in self.cert_data_cache:
            try:
                date_str = item.get('valid_to', '')
                if date_str and date_str not in ('—', 'Не найден', 'Ошибка'):
                    item_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                    if self.date_from <= item_date <= self.date_to:
                        filtered_data.append(item)
            except:
                continue
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._insert_certificates_into_tree(filtered_data)
        self.search_result_label.config(text=f"Фильтр: {len(filtered_data)} записей")

    def scan_mchd_folder(self):
        self.current_folder_key = "📁 МЧД"
        path = self.core.mchd_folder
        if not os.path.exists(path):
            response = messagebox.askyesno("Создать папку", f"Папка МЧД не существует. Создать?\n{path}")
            if response:
                os.makedirs(path)
                messagebox.showinfo("Информация", f"Папка создана:\n{path}\n\nПоместите в нее XML файлы МЧД")
                return
            else:
                return
        self.folder_path.set(path)
        self.current_folder_label.config(text="Текущая: МЧД")
        self.folder_history.append(path)
        try:
            mchd_files = self.core.scan_mchd_files()
            self.listbox_mchd.delete(0, tk.END)
            self.mchd_data_cache = []
            if not mchd_files:
                messagebox.showinfo("Информация", f"В папке {path} не найдено XML файлов")
                return
            for f in mchd_files:
                self.listbox_mchd.insert(tk.END, os.path.basename(f))
                mchd_info = self.mchd_parser.parse_file(f)
                self.mchd_data_cache.append(mchd_info)
            messagebox.showinfo("Успех", f"Найдено и проанализировано {len(mchd_files)} МЧД")
            self.analyze_mchd()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сканировании МЧД:\n{str(e)}")

    def analyze_mchd(self):
        if not self.mchd_data_cache:
            self.scan_mchd_folder()
            if not self.mchd_data_cache:
                messagebox.showwarning("Внимание", "Нет данных МЧД для анализа")
                return
        if "mchd_table" in self.open_windows and self.open_windows["mchd_table"] is not None:
            try:
                if hasattr(self.open_windows["mchd_table"], 'window') and self.open_windows["mchd_table"].window:
                    if self.open_windows["mchd_table"].window.winfo_exists():
                        self.open_windows["mchd_table"].window.lift()
                        self.open_windows["mchd_table"].window.focus_force()
                        return
            except:
                pass
        window = MCHDTableWindow(self.root, self.mchd_data_cache)
        self.open_windows["mchd_table"] = window

    def on_search(self, *args):
        query = self.search_var.get().lower()
        self.current_search_query = query
        if not query:
            self.search_active = False
            self.search_result_label.config(text="")
            self.refresh_current_view()
            return
        self.search_active = True
        filtered_data = []
        for item in self.cert_data_cache:
            values_to_check = [
                os.path.basename(item.get('file_name', '')).lower(),
                item.get('subject_cn', '').lower(),
                item.get('serial_number', '').lower(),
                item.get('email', '').lower(),
                item.get('office_number', '—').lower(),
                item.get('department', '—').lower(),
                item.get('phone', '—').lower(),
                item.get('status', '').lower()
            ]
            if any(query in value for value in values_to_check):
                filtered_data.append(item)
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._insert_certificates_into_tree(filtered_data)
        total = len(self.cert_data_cache)
        self.search_result_label.config(text=f"Найдено: {len(filtered_data)} из {total}")

    def clear_search(self):
        self.search_var.set("")
        self.search_active = False
        self.current_search_query = ""
        self.search_result_label.config(text="")
        self.refresh_current_view()

    def refresh_current_view(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._insert_certificates_into_tree(self.cert_data_cache)

    def _insert_certificates_into_tree(self, data_list):
        names = []
        for item in data_list:
            name = item.get('subject_cn', '')
            if name and name not in ('Не найдено', 'Ошибка'):
                names.append(name)
        name_counter = Counter(names)
        duplicates = {name for name, count in name_counter.items() if count > 1}
        for item in data_list:
            tag_list = []
            status = item.get('status', '')
            if status == "Просрочен":
                tag_list.append('expired')
            elif "Истекает" in status:
                tag_list.append('warning')
            else:
                tag_list.append('normal')
            name = item.get('subject_cn', '')
            if name in duplicates:
                tag_list.append('duplicate')
            self.tree.insert("", tk.END, values=(
                item.get('file_type', 'Серт'),
                os.path.basename(item.get('file_name', '')),
                item.get('valid_from', ''),
                item.get('valid_to', ''),
                item.get('subject_cn', ''),
                item.get('serial_number', ''),
                item.get('email', '—'),
                item.get('office_number', '—'),
                item.get('department', '—'),
                item.get('phone', '—'),
                item.get('status', '')
            ), tags=tuple(tag_list))

    def show_folder_settings(self):
        if "folder_settings" in self.open_windows and self.open_windows["folder_settings"] is not None:
            try:
                if self.open_windows["folder_settings"].winfo_exists():
                    self.open_windows["folder_settings"].lift()
                    self.open_windows["folder_settings"].focus_force()
                    return
            except:
                pass

        settings_window = tk.Toplevel(self.root)
        settings_window.title("Настройка путей к папкам")
        settings_window.geometry("600x450")
        settings_window.configure(bg=BG_COLOR)
        settings_window.resizable(False, False)
        self.open_windows["folder_settings"] = settings_window

        frame = ttk.Frame(settings_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Настройка путей к папкам",
                  font=('Segoe UI', 14, 'bold')).pack(anchor='center', pady=(0, 20))

        emp_frame = ttk.Frame(frame)
        emp_frame.pack(fill=tk.X, pady=5)
        ttk.Label(emp_frame, text="📁 Сотрудники:", font=('Segoe UI', 10, 'bold'), width=15).pack(side=tk.LEFT)
        emp_path_var = tk.StringVar(value=DEFAULT_FOLDERS.get("📁 Сотрудники", ""))
        ttk.Entry(emp_frame, textvariable=emp_path_var, width=40).pack(side=tk.LEFT, padx=(10, 5), fill=tk.X,
                                                                       expand=True)
        ttk.Button(emp_frame, text="Обзор", command=lambda: self.select_folder_path(emp_path_var),
                   style='Accent.TButton', width=10).pack(side=tk.RIGHT)

        mgmt_frame = ttk.Frame(frame)
        mgmt_frame.pack(fill=tk.X, pady=5)
        ttk.Label(mgmt_frame, text="📁 Руководство:", font=('Segoe UI', 10, 'bold'), width=15).pack(side=tk.LEFT)
        mgmt_path_var = tk.StringVar(value=DEFAULT_FOLDERS.get("📁 Руководство", ""))
        ttk.Entry(mgmt_frame, textvariable=mgmt_path_var, width=40).pack(side=tk.LEFT, padx=(10, 5), fill=tk.X,
                                                                         expand=True)
        ttk.Button(mgmt_frame, text="Обзор", command=lambda: self.select_folder_path(mgmt_path_var),
                   style='Accent.TButton', width=10).pack(side=tk.RIGHT)

        mchd_frame = ttk.Frame(frame)
        mchd_frame.pack(fill=tk.X, pady=5)
        ttk.Label(mchd_frame, text="📁 МЧД (XML):", font=('Segoe UI', 10, 'bold'), width=15).pack(side=tk.LEFT)
        mchd_path_var = tk.StringVar(value=self.core.mchd_folder)
        ttk.Entry(mchd_frame, textvariable=mchd_path_var, width=40).pack(side=tk.LEFT, padx=(10, 5), fill=tk.X,
                                                                         expand=True)
        ttk.Button(mchd_frame, text="Обзор", command=lambda: self.select_folder_path(mchd_path_var, is_mchd=True),
                   style='Accent.TButton', width=10).pack(side=tk.RIGHT)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=20)

        def save_settings():
            DEFAULT_FOLDERS["📁 Сотрудники"] = emp_path_var.get()
            DEFAULT_FOLDERS["📁 Руководство"] = mgmt_path_var.get()
            self.core.mchd_folder = mchd_path_var.get()
            if save_config(DEFAULT_FOLDERS):
                messagebox.showinfo("Успех", "Настройки сохранены!")
                self.close_window("folder_settings", settings_window)
                if self.current_folder_key in ["📁 Сотрудники", "📁 Руководство"]:
                    self.folder_path.set(DEFAULT_FOLDERS[self.current_folder_key])
                    self.scan_folder()
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить настройки")

        ttk.Button(btn_frame, text="Сохранить", command=save_settings, style='Accent.TButton').pack(side=tk.RIGHT,
                                                                                                    padx=5)
        ttk.Button(btn_frame, text="Отмена", command=lambda: self.close_window("folder_settings", settings_window),
                   style='Accent.TButton').pack(side=tk.RIGHT, padx=5)

        def on_destroy():
            self.open_windows["folder_settings"] = None
            settings_window.destroy()

        settings_window.protocol("WM_DELETE_WINDOW", on_destroy)

    def select_folder_path(self, var, is_mchd=False):
        folder = filedialog.askdirectory(title="Выберите папку")
        if folder:
            var.set(folder)
            if is_mchd:
                self.core.mchd_folder = folder

    def setup_folder_menu(self):
        self.folder_menu = tk.Menu(self.root, tearoff=0)
        self.folder_menu.add_command(label="📁 Добавить папку в избранное", command=self.add_to_favorites)
        self.folder_menu.add_command(label="📋 Редактировать избранные папки", command=self.edit_favorites)
        self.folder_menu.add_separator()
        self.folder_menu.add_command(label="🗂️ Создать новую папку", command=self.create_new_folder)
        self.folder_menu.add_separator()
        self.folder_menu.add_command(label="⚙️ Настройки путей", command=self.show_folder_settings)

    def switch_folder(self, key):
        self.current_folder_key = key
        path = DEFAULT_FOLDERS[key]
        if not os.path.exists(path):
            response = messagebox.askyesno("Создать папку", f"Папка '{path}' не существует. Создать?")
            if response:
                os.makedirs(path)
            else:
                return
        self.folder_path.set(path)
        self.current_folder_label.config(text=f"Текущая: {key}")
        self.folder_history.append(path)
        self.scan_folder()

    def load_default_folder(self):
        path = DEFAULT_FOLDERS["📁 Сотрудники"]
        if not os.path.exists(path):
            os.makedirs(path)
        self.folder_path.set(path)
        self.folder_history.append(path)
        self.scan_folder()

    def folder_back(self):
        if len(self.folder_history) > 1:
            self.folder_history.pop()
            prev_folder = self.folder_history[-1]
            self.folder_path.set(prev_folder)
            folder_name = "Произвольная папка"
            for name, path in DEFAULT_FOLDERS.items():
                if path == prev_folder:
                    folder_name = name
                    break
            self.current_folder_label.config(text=f"Текущая: {folder_name}")
            self.scan_folder()

    def add_to_favorites(self):
        current_path = self.folder_path.get()
        if not current_path:
            messagebox.showwarning("Внимание", "Сначала выберите папку")
            return
        name = simpledialog.askstring("Добавить в избранное", "Введите имя для папки:",
                                      initialvalue=os.path.basename(current_path))
        if name:
            DEFAULT_FOLDERS[name] = current_path
            if save_config(DEFAULT_FOLDERS):
                messagebox.showinfo("Успех", f"Папка '{name}' добавлена в избранное")
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить настройки")

    def edit_favorites(self):
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Редактирование избранных папок")
        edit_window.geometry("500x400")
        edit_window.configure(bg=BG_COLOR)
        frame = ttk.Frame(edit_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Избранные папки:", font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        listbox = tk.Listbox(frame, height=10, selectmode=tk.SINGLE)
        listbox.pack(fill=tk.BOTH, expand=True, pady=10)
        for name, path in DEFAULT_FOLDERS.items():
            listbox.insert(tk.END, f"{name}: {path}")

        def remove_selected():
            selection = listbox.curselection()
            if selection:
                item = listbox.get(selection[0])
                name = item.split(":")[0]
                if name in DEFAULT_FOLDERS:
                    del DEFAULT_FOLDERS[name]
                    listbox.delete(selection[0])
                    save_config(DEFAULT_FOLDERS)

        def add_new():
            name = simpledialog.askstring("Добавить папку", "Имя:")
            if name:
                path = filedialog.askdirectory(title=f"Выберите папку для '{name}'")
                if path:
                    DEFAULT_FOLDERS[name] = path
                    listbox.insert(tk.END, f"{name}: {path}")
                    save_config(DEFAULT_FOLDERS)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Добавить", command=add_new, style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=remove_selected, style='Accent.TButton').pack(side=tk.LEFT,
                                                                                                    padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=edit_window.destroy, style='Accent.TButton').pack(side=tk.RIGHT,
                                                                                                        padx=5)

    def create_new_folder(self):
        folder_name = simpledialog.askstring("Создать папку", "Введите имя папки:")
        if folder_name:
            new_folder_path = os.path.join(os.path.expanduser("~"), f"Cert_{folder_name}")
            os.makedirs(new_folder_path, exist_ok=True)
            DEFAULT_FOLDERS[f"📁 {folder_name}"] = new_folder_path
            save_config(DEFAULT_FOLDERS)
            messagebox.showinfo("Успех",
                                f"Папка создаена: {new_folder_path}\nДобавлена в избранное как '📁 {folder_name}'")

    def export_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Экспорт в Excel", command=self.export_to_excel_gui)
        menu.add_command(label="Экспорт в PDF", command=self.export_to_pdf_gui)
        menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def service_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Установить службу", command=self.install_service)
        menu.add_command(label="Удалить службу", command=self.remove_service)
        menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def sort_column(self, col):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        if col in ("С", "По"):
            try:
                data.sort(key=lambda x: datetime.strptime(x[0], '%d.%m.%Y') if x[0] and x[0] not in (
                    '—', 'Не найдена', 'Не найден') else datetime.min, reverse=self.sort_reverse[col])
            except:
                data.sort(key=lambda x: x[0], reverse=self.sort_reverse[col])
        elif col == "ФИО":
            data.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse[col])
        else:
            data.sort(key=lambda x: x[0], reverse=self.sort_reverse[col])
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
        self.sort_reverse[col] = not self.sort_reverse[col]

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите записи для удаления")
            return
        if not messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить выбранные файлы?"):
            return
        deleted_count = 0
        for item in selected:
            values = self.tree.item(item)['values']
            if not values:
                continue
            filename = values[1]
            for f in self.core.loaded_files:
                if os.path.basename(f) == filename:
                    full_path = f
                    if full_path and os.path.exists(full_path):
                        try:
                            os.remove(full_path)
                            deleted_count += 1
                        except Exception as e:
                            messagebox.showerror("Ошибка", f"Не удалось удалить {filename}: {e}")
                    break
            self.tree.delete(item)
        if deleted_count > 0:
            messagebox.showinfo("Успех", f"Удалено файлов: {deleted_count}")
            self.refresh_all()

    def on_date_select(self, event=None):
        date_str = self.cal.get_date()
        try:
            selected_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            docs_on_date = []
            for item in self.cert_data_cache:
                try:
                    date_field = item.get('valid_to', '')
                    if date_field and date_field not in ('—', 'Не найден', 'Ошибка'):
                        item_date = datetime.strptime(date_field, '%d.%m.%Y').date()
                        if item_date == selected_date:
                            docs_on_date.append(item)
                except:
                    continue
            if docs_on_date:
                doc_list = []
                for doc in docs_on_date:
                    name = doc.get('subject_cn', 'Неизвестно')
                    status = doc.get('status', '')
                    doc_list.append(f"- {name} ({status})")
                msg = f"Сертификаты, истекающие {date_str}:\n" + "\n".join(doc_list)
                messagebox.showinfo(f"Сертификаты на {date_str}", msg)
            else:
                messagebox.showinfo(f"Дата {date_str}", "На эту дату нет истекающих сертификатов")
        except Exception as e:
            print(f"Ошибка при обработке даты: {e}")

    def show_today(self):
        today = datetime.now().date()
        self.cal.selection_set(today)
        self.cal.see(today)
        self.update_calendar_colors()

    def prev_month(self):
        self.cal._prev_month()
        self.update_calendar_colors()

    def next_month(self):
        self.cal._next_month()
        self.update_calendar_colors()

    def update_stats(self):
        current_data = self.cert_data_cache

        total = len(current_data)
        expired = 0
        warning = 0
        normal = 0

        for doc in current_data:
            status = doc.get('status', '')
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

        EXCEL_GREEN = '#81c784'
        EXCEL_YELLOW = '#ffd54f'
        EXCEL_RED = '#e57373'
        EXCEL_BLUE = '#4472C4'

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
                chart_type = getattr(self, 'chart_type', 'pie')

                if chart_type == "pie":
                    self.ax_status = self.figure_status.add_subplot(111)
                    explode = [0.05] * len(sizes)
                    wedges, texts, autotexts = self.ax_status.pie(
                        sizes,
                        labels=labels,
                        colors=excel_colors,
                        autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
                        startangle=90,
                        explode=explode,
                        textprops={'fontsize': 9, 'fontweight': 'bold'},
                        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
                    )
                    for autotext in autotexts:
                        autotext.set_fontsize(9)
                        autotext.set_fontweight('bold')
                        autotext.set_color('#333333')
                    self.ax_status.set_title('Статус сертификатов', fontsize=11, fontweight='bold', pad=10)

                elif chart_type == "bar":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    bars = self.ax_status.bar(x, sizes, color=excel_colors, width=0.6, edgecolor='white', linewidth=1)
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel('Количество', fontsize=9)
                    self.ax_status.set_title('Статус сертификатов', fontsize=11, fontweight='bold', pad=10)
                    self.ax_status.spines['top'].set_visible(False)
                    self.ax_status.spines['right'].set_visible(False)

                    for bar, size in zip(bars, sizes):
                        height = bar.get_height()
                        self.ax_status.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                                            str(size), ha='center', va='bottom', fontsize=9, fontweight='bold')
                    self.ax_status.set_ylim(0, max(sizes) * 1.15)

                elif chart_type == "line":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    self.ax_status.plot(x, sizes, marker='o', linewidth=2.5, markersize=8,
                                        color=EXCEL_BLUE, markerfacecolor='white', markeredgewidth=2)
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel('Количество', fontsize=9)
                    self.ax_status.set_title('Статус сертификатов', fontsize=11, fontweight='bold', pad=10)
                    self.ax_status.spines['top'].set_visible(False)
                    self.ax_status.spines['right'].set_visible(False)
                    self.ax_status.set_ylim(0, max(sizes) * 1.15)

                    for i, size in enumerate(sizes):
                        self.ax_status.annotate(str(size), (i, size), textcoords="offset points",
                                                xytext=(0, 10), ha='center', fontsize=9, fontweight='bold')

                elif chart_type == "area":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    self.ax_status.fill_between(x, sizes, alpha=0.4, color=EXCEL_BLUE)
                    self.ax_status.plot(x, sizes, marker='o', linewidth=2.5, markersize=6, color=EXCEL_BLUE)
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel('Количество', fontsize=9)
                    self.ax_status.set_title('Статус сертификатов', fontsize=11, fontweight='bold', pad=10)
                    self.ax_status.spines['top'].set_visible(False)
                    self.ax_status.spines['right'].set_visible(False)
                    self.ax_status.set_ylim(0, max(sizes) * 1.15)

                    for i, size in enumerate(sizes):
                        self.ax_status.text(i, size + 0.1, str(size), ha='center', fontsize=9, fontweight='bold')

                elif chart_type == "doughnut":
                    self.ax_status = self.figure_status.add_subplot(111)
                    wedges, texts, autotexts = self.ax_status.pie(
                        sizes,
                        labels=labels,
                        colors=excel_colors,
                        autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
                        startangle=90,
                        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5, 'width': 0.5},
                        textprops={'fontsize': 9, 'fontweight': 'bold'}
                    )
                    for autotext in autotexts:
                        autotext.set_fontsize(9)
                        autotext.set_fontweight('bold')
                        autotext.set_color('#333333')
                    self.ax_status.set_title('Статус сертификатов', fontsize=11, fontweight='bold', pad=10)

                elif chart_type == "scatter":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    point_sizes = [max(s * 60, 120) for s in sizes]
                    self.ax_status.scatter(x, sizes, s=point_sizes, c=excel_colors, alpha=0.8,
                                           edgecolors='white', linewidth=1.5)
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel('Количество', fontsize=9)
                    self.ax_status.set_title('Статус сертификатов', fontsize=11, fontweight='bold', pad=10)
                    self.ax_status.spines['top'].set_visible(False)
                    self.ax_status.spines['right'].set_visible(False)
                    self.ax_status.set_ylim(0, max(sizes) * 1.2)

                    for i, (xi, yi) in enumerate(zip(x, sizes)):
                        self.ax_status.annotate(str(yi), (xi, yi), textcoords="offset points",
                                                xytext=(0, 12), ha='center', fontsize=9, fontweight='bold')

                elif chart_type == "bubble":
                    self.ax_status = self.figure_status.add_subplot(111)
                    x = range(len(labels))
                    bubble_sizes = [max(s * 150, 250) for s in sizes]
                    self.ax_status.scatter(x, sizes, s=bubble_sizes, c=excel_colors, alpha=0.7,
                                           edgecolors='white', linewidth=1.5)
                    self.ax_status.set_xticks(x)
                    self.ax_status.set_xticklabels(labels, fontsize=9)
                    self.ax_status.set_ylabel('Количество', fontsize=9)
                    self.ax_status.set_title('Статус сертификатов', fontsize=11, fontweight='bold', pad=10)
                    self.ax_status.spines['top'].set_visible(False)
                    self.ax_status.spines['right'].set_visible(False)
                    self.ax_status.set_ylim(0, max(sizes) * 1.25)

                    for i, (xi, yi) in enumerate(zip(x, sizes)):
                        self.ax_status.annotate(str(yi), (xi, yi), textcoords="offset points",
                                                xytext=(0, 15), ha='center', fontsize=9, fontweight='bold')

                elif chart_type == "stacked_bar":
                    self.ax_status = self.figure_status.add_subplot(111)
                    bottom = 0
                    bar_width = 0.5
                    for i, (size, color, label) in enumerate(zip(sizes, excel_colors, labels)):
                        bar = self.ax_status.bar(0, size, bottom=bottom, label=label, color=color,
                                                 width=bar_width, edgecolor='white', linewidth=1)
                        if size > 0:
                            self.ax_status.text(0, bottom + size / 2, str(size), ha='center', va='center',
                                                fontsize=10, fontweight='bold', color='#333333')
                        bottom += size
                    self.ax_status.set_xticks([0])
                    self.ax_status.set_xticklabels(['Всего'], fontsize=9)
                    self.ax_status.set_ylabel('Количество', fontsize=9)
                    self.ax_status.set_title('Статус сертификатов', fontsize=11, fontweight='bold', pad=10)
                    self.ax_status.spines['top'].set_visible(False)
                    self.ax_status.spines['right'].set_visible(False)
                    self.ax_status.set_xlim(-0.5, 0.5)
                    self.ax_status.set_ylim(0, sum(sizes) * 1.1)
                    self.ax_status.legend(loc='upper right', fontsize=8, frameon=True, fancybox=False)

                else:
                    self.ax_status = self.figure_status.add_subplot(111)
                    self.ax_status.text(0.5, 0.5, 'Выберите тип диаграммы', ha='center', va='center', fontsize=10)

            except Exception as e:
                print(f"Ошибка построения диаграммы: {e}")
                self.ax_status = self.figure_status.add_subplot(111)
                self.ax_status.text(0.5, 0.5, f'Ошибка', ha='center', va='center', fontsize=10)
        else:
            self.ax_status = self.figure_status.add_subplot(111)
            self.ax_status.text(0.5, 0.5, 'Нет данных', ha='center', va='center', fontsize=10)
            self.ax_status.set_title('Статус сертификатов', fontsize=11, fontweight='bold', pad=10)

        try:
            self.figure_status.tight_layout(pad=1.5)
        except:
            pass

        self.canvas_status.draw()
        self.update_calendar_colors()

    def select_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с сертификатами")
        if folder:
            self.folder_path.set(folder)
            self.folder_history.append(folder)
            self.current_folder_label.config(text=f"Текущая: {os.path.basename(folder)}")
            self.scan_folder()

    def scan_folder(self):
        path = self.folder_path.get()
        if not path:
            messagebox.showwarning("Внимание", "Выберите папку!")
            return
        try:
            self.core.scan_certificates(path)
            self.listbox_files.delete(0, tk.END)
            for f in self.core.loaded_files:
                self.listbox_files.insert(tk.END, os.path.basename(f))
            self.parse_certificates()
            self.clear_search()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def parse_certificates(self):
        if not self.core.loaded_files:
            messagebox.showerror("Ошибка", "Нет загруженных файлов!")
            return
        try:
            results = self.core.parse_certificates()
            self.cert_data_cache = results
            self.display_current_data()
            self.check_for_expired_certificates()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def display_current_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._insert_certificates_into_tree(self.cert_data_cache)
        self.update_stats()

    def check_for_expired_certificates(self):
        if not hasattr(self, 'cert_data_cache'):
            return
        expired_count = sum(1 for cert in self.cert_data_cache if cert.get('status') == "Просрочен")
        warning_count = sum(1 for cert in self.cert_data_cache if "Истекает" in cert.get('status', ''))
        if expired_count > 0 and not hasattr(self, '_expired_notification_shown'):
            self.show_notification(f"⚠️ Обнаружено {expired_count} просроченных сертификатов! Требуется внимание.",
                                   "error", 5000)
            self._expired_notification_shown = True
        elif warning_count > 0 and not hasattr(self, '_warning_notification_shown'):
            self.show_notification(f"⚡ {warning_count} сертификатов истекают в ближайшее время.", "warning", 4000)
            self._warning_notification_shown = True

    def get_report_title(self):
        if "Сотрудники" in self.current_folder_key:
            return "Отчет по сертификатам сотрудников"
        elif "Руководство" in self.current_folder_key:
            return "Отчет по сертификатам руководства"
        else:
            folder_name = os.path.basename(self.folder_path.get()) if self.folder_path.get() else "сертификатам"
            return f"Отчет по сертификатам ({folder_name})"

    def export_to_excel_gui(self):
        if not self.cert_data_cache:
            messagebox.showerror("Ошибка", "Нет данных для экспорта!")
            return
        try:
            report_title = self.get_report_title()
            default_name = f"cert_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel файлы", "*.xlsx"), ("Все файлы", "*.*")],
                initialdir=self.core.export_folder,
                initialfile=default_name,
                title=f"Сохранить Excel отчет - {report_title}"
            )
            if not save_path:
                return
            saved_path = self.core.export_to_excel(self.cert_data_cache, save_path, report_title)
            if saved_path and os.path.exists(saved_path):
                self.show_notification(f"Excel отчет успешно сохранен!\n{os.path.basename(saved_path)}", "success",
                                       4000)
                if messagebox.askyesno("Открыть папку", "Открыть папку с отчетом?"):
                    os.startfile(os.path.dirname(saved_path))
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить файл")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать в Excel:\n{str(e)}")

    def export_to_pdf_gui(self):
        if not self.cert_data_cache:
            messagebox.showerror("Ошибка", "Нет данных для экспорта!")
            return
        try:
            report_title = self.get_report_title()
            include_chart = self.include_chart_var.get()
            default_name = f"cert_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            save_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF файлы", "*.pdf"), ("Все файлы", "*.*")],
                initialdir=self.core.export_folder,
                initialfile=default_name,
                title=f"Сохранить PDF отчет - {report_title}"
            )
            if not save_path:
                return
            if not save_path.lower().endswith('.pdf'):
                save_path += '.pdf'
            if os.path.exists(save_path):
                if not messagebox.askyesno("Подтверждение", f"Файл уже существует. Перезаписать?"):
                    return
            saved_path = self.core.export_to_pdf(self.cert_data_cache, save_path, self.figure_status, report_title,
                                                 include_chart)
            if saved_path and os.path.exists(saved_path):
                self.show_notification(f"PDF отчет успешно сохранен!\n{os.path.basename(saved_path)}", "success", 4000)
                if messagebox.askyesno("Открыть файл", "Открыть PDF отчет?"):
                    os.startfile(saved_path)
            else:
                messagebox.showerror("Ошибка", "Не удалось сохранить PDF файл")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать в PDF:\n{str(e)}")

    def copy_to_clipboard(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Ошибка", "Нет выделенных строк!")
            return
        data = []
        for item in selected:
            data.append("\t".join(str(v) for v in self.tree.item(item)['values']))
        pyperclip.copy("\n".join(data))
        messagebox.showinfo("Успех", "Скопировано!")

    def refresh_all(self):
        self.scan_folder()

    def show_help(self):
        if "help" in self.open_windows and self.open_windows["help"] is not None:
            try:
                if self.open_windows["help"].winfo_exists():
                    self.open_windows["help"].lift()
                    self.open_windows["help"].focus_force()
                    return
            except:
                pass

        help_text = """Анализатор сертификатов и МЧД - Справка

 ОСНОВНЫЕ ФУНКЦИИ:

 1. 📁 РАБОТА С ПАПКАМИ
    • Сотрудники - сканирование сертификатов сотрудников
    • Руководство - сканирование сертификатов руководства
    • МЧД - сканирование XML файлов МЧД

 2. 📊 АНАЛИЗ СЕРТИФИКАТОВ    • Автоматическое определение статуса
    • Извлечение кабинета и подразделения из OU
    • Автоматический поиск телефона из справочника

 3. 📊 АНАЛИЗ МЧД
    • Номер доверенности, даты, ФИО, коды полномочий
    • Подсветка людей с несколькими МЧД
    • Поиск по фамилии, сортировка

 4. 🔄 ОБЪЕДИНЕНИЕ МЧД
    • Выберите несколько МЧД одного человека
    • Нажмите "Объединить выбранные МЧД"

 5. 🔍 ПОИСК И ФИЛЬТРАЦИЯ
    • Поиск по всем полям
    • Фильтр по диапазону дат

 6. 📅 КАЛЕНДАРЬ
    • Светло-розовый - просроченные
    • Светло-желтый - истекающие
    • Светло-зеленый - активные

 7. 📊 ДИАГРАММЫ
    • 8 типов диаграмм на выбор

 8. 📤 ЭКСПОРТ
    • Excel и PDF с графиком

 9. 🔔 PUSH-УВЕДОМЛЕНИЯ
    • Уведомления в системный трей Windows

10. 📞 СПРАВОЧНИК ТЕЛЕФОНОВ
    • Загрузка справочника из файла .docx или .txt
    • Автоматический поиск телефона по кабинету, ФИО или подразделению
    • Отображение найденного телефона в общем списке
"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Справка")
        help_window.geometry("750x650")
        help_window.configure(bg=BG_COLOR)
        self.open_windows["help"] = help_window

        frame = ttk.Frame(help_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        text_widget = tk.Text(frame, wrap=tk.WORD, font=('Segoe UI', 10),
                              background='white', foreground=TEXT_COLOR)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert('1.0', help_text)
        text_widget.config(state='disabled')
        ttk.Button(frame, text="Закрыть", command=lambda: self.close_window("help", help_window),
                   style='Accent.TButton').pack(pady=(10, 0))

        def on_destroy():
            self.open_windows["help"] = None
            help_window.destroy()

        help_window.protocol("WM_DELETE_WINDOW", on_destroy)

    def install_service(self):
        try:
            export_path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
            if not export_path:
                return
            scan_folder = filedialog.askdirectory(mustexist=True)
            if not scan_folder:
                return
            config_file = os.path.join(os.path.dirname(__file__), "service_config.json")
            with open(config_file, 'w') as f:
                json.dump({"export_path": export_path, "scan_folder": scan_folder}, f, indent=4)

            def install():
                try:
                    win32serviceutil.InstallService(None, SERVICE_NAME, SERVICE_DISPLAY_NAME,
                                                    description="Автоматический анализ сертификатов и МЧД",
                                                    startType=win32service.SERVICE_AUTO_START)
                    messagebox.showinfo("Успех", "Служба установлена!")
                except pywintypes.error as e:
                    if e.winerror == 5:
                        messagebox.showerror("Ошибка", "Запустите от администратора!")
                    else:
                        messagebox.showerror("Ошибка", str(e))

            threading.Thread(target=install, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def remove_service(self):
        def remove():
            try:
                win32serviceutil.RemoveService(SERVICE_NAME)
                messagebox.showinfo("Успех", "Служба удалена!")
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))

        threading.Thread(target=remove, daemon=True).start()


def run_as_service():
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(CertificateAnalyzerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(CertificateAnalyzerService)


def run_as_gui():
    root = tk.Tk()
    app = CertificateAnalyzerApp(root)
    root.mainloop()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'service':
        run_as_service()
    else:
        run_as_gui()
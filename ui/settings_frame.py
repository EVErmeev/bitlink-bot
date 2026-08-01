import tkinter as tk
from tkinter import ttk, messagebox
import os
from pathlib import Path
from dotenv import load_dotenv, set_key
import importlib

from protocol_templates.registry import TemplateRegistry
from services.bitlink_service import BitlinkClient
from services.transcription_service import TranscriptionClient
from services.confluence_service import ConfluenceClient
from services.telegram_service import TelegramClient
import settings


class SettingsFrame(ttk.Frame):
    TEMPLATE_OPTIONS = [
        ("management_summary", "Управленческий протокол"),
        ("project_standard", "Проектный протокол"),
        ("project_detailed", "Подробный проектный протокол"),
        ("business_process_discovery", "Обследование бизнес-процессов"),
    ]

    MODE_OPTIONS = [("auto", "Авто"), ("brief", "Краткий"), ("detailed", "Подробный")]

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.env_path = Path(__file__).resolve().parent.parent / ".env"
        self._block_entries = {}
        self._build()
        self._load_settings()

    def _make_block_key(self, title):
        return title.lower().replace(".", "_")

    def _build(self):
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable = ttk.Frame(canvas)
        self.scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        top = ttk.Frame(self.scrollable)
        top.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top, text="Настройки", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="Назад", command=lambda: self.main_window.show_main_menu()).pack(side=tk.RIGHT)

        self._build_block("БИТ.Link", [
            ("email", "Email:", None),
            ("password", "Пароль:", "*"),
        ], self._test_bitlink)

        self._build_block("Newton", [
            ("token", "Токен:", "*"),
            ("path", "Путь:", None),
            ("base_url", "Base URL:", None),
        ], self._test_newton)

        self._build_block("Confluence", [
            ("token", "Токен:", "*"),
            ("base_url", "Base URL:", None),
            ("space_key", "Space Key:", None),
            ("parent_page_id", "Parent Page ID:", None),
            ("parent_page_title", "Parent Page Title:", None),
        ], self._test_confluence, extra_btn_text="Выбрать страницу")

        self._build_block("Telegram", [
            ("bot_token", "Bot Token:", "*"),
            ("chat_id", "Chat ID:", None),
        ], self._test_telegram)

        self._build_protocol_block()

        ttk.Button(self.scrollable, text="Сохранить настройки", command=self._save_settings).pack(pady=10)

    def _build_block(self, title, fields, test_callback, extra_btn_text=None):
        frame = ttk.LabelFrame(self.scrollable, text=title, padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        entries = {}
        for i, (key, label, mask) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            show = "*" if mask else ""
            entry = ttk.Entry(frame, width=50, show=show)
            entry.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            entries[key] = entry

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="Проверить подключение", command=test_callback).pack(side=tk.LEFT, padx=3)
        if extra_btn_text:
            ttk.Button(btn_frame, text=extra_btn_text, command=self._choose_confluence_parent).pack(side=tk.LEFT, padx=3)

        self._block_entries[self._make_block_key(title)] = entries

    def _build_protocol_block(self):
        frame = ttk.LabelFrame(self.scrollable, text="Протокол", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame, text="Шаблон по умолчанию:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._template_var = tk.StringVar(value="project_detailed")
        template_combo = ttk.Combobox(frame, textvariable=self._template_var, state="readonly", width=40)
        template_combo["values"] = [t[0] for t in self.TEMPLATE_OPTIONS]
        template_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(frame, text="Режим по умолчанию:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._mode_var = tk.StringVar(value="auto")
        mode_combo = ttk.Combobox(frame, textvariable=self._mode_var, state="readonly", width=40)
        mode_combo["values"] = [m[0] for m in self.MODE_OPTIONS]
        mode_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        self._continue_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Продолжать обработку после ошибки", variable=self._continue_var).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=2
        )

    def _load_settings(self):
        load_dotenv(self.env_path)
        settings_map = {
            "бит_link": {"email": "BITLINK_EMAIL", "password": "BITLINK_PASSWORD"},
            "newton": {"token": "NEWTON_TOKEN", "path": "NEWTON_PATH", "base_url": "NEWTON_BASE_URL"},
            "confluence": {
                "token": "CONFLUENCE_TOKEN", "base_url": "CONFLUENCE_BASE_URL",
                "space_key": "CONFLUENCE_SPACE_KEY", "parent_page_id": "CONFLUENCE_PARENT_PAGE_ID",
                "parent_page_title": "CONFLUENCE_PARENT_PAGE_TITLE",
            },
            "telegram": {"bot_token": "TG_BOT_TOKEN", "chat_id": "TG_CHAT_ID"},
        }
        for block_name, field_map in settings_map.items():
            entries = self._block_entries.get(block_name, {})
            for field_key, env_key in field_map.items():
                if field_key in entries:
                    val = os.getenv(env_key, "")
                    entries[field_key].delete(0, tk.END)
                    entries[field_key].insert(0, val)

        self._template_var.set(os.getenv("PROTOCOL_TEMPLATE", "project_detailed"))
        self._mode_var.set(os.getenv("PROTOCOL_MODE", "auto"))
        self._continue_var.set(os.getenv("BATCH_CONTINUE_AFTER_ERROR", "true").lower() in ("true", "1", "yes"))

    def _save_settings(self):
        bitlink_e = self._block_entries.get("бит_link", {})
        newton_e = self._block_entries.get("newton", {})
        confluence_e = self._block_entries.get("confluence", {})
        telegram_e = self._block_entries.get("telegram", {})

        env_map = {
            "BITLINK_EMAIL": bitlink_e.get("email", tk.Entry()).get(),
            "BITLINK_PASSWORD": bitlink_e.get("password", tk.Entry()).get(),
            "NEWTON_TOKEN": newton_e.get("token", tk.Entry()).get(),
            "NEWTON_PATH": newton_e.get("path", tk.Entry()).get(),
            "NEWTON_BASE_URL": newton_e.get("base_url", tk.Entry()).get(),
            "CONFLUENCE_TOKEN": confluence_e.get("token", tk.Entry()).get(),
            "CONFLUENCE_BASE_URL": confluence_e.get("base_url", tk.Entry()).get(),
            "CONFLUENCE_SPACE_KEY": confluence_e.get("space_key", tk.Entry()).get(),
            "CONFLUENCE_PARENT_PAGE_ID": confluence_e.get("parent_page_id", tk.Entry()).get(),
            "CONFLUENCE_PARENT_PAGE_TITLE": confluence_e.get("parent_page_title", tk.Entry()).get(),
            "TG_BOT_TOKEN": telegram_e.get("bot_token", tk.Entry()).get(),
            "TG_CHAT_ID": telegram_e.get("chat_id", tk.Entry()).get(),
            "PROTOCOL_TEMPLATE": self._template_var.get(),
            "PROTOCOL_MODE": self._mode_var.get(),
            "BATCH_CONTINUE_AFTER_ERROR": str(self._continue_var.get()).lower(),
        }

        for key, value in env_map.items():
            set_key(str(self.env_path), key, value)

        importlib.reload(settings)
        messagebox.showinfo("Успех", "Настройки сохранены")

    def _test_bitlink(self):
        client = BitlinkClient()
        if client.check_connection():
            messagebox.showinfo("БИТ.Link", "Подключение успешно (mock-режим)")
        else:
            messagebox.showerror("БИТ.Link", "Ошибка подключения")

    def _test_newton(self):
        client = TranscriptionClient()
        if client.check_connection():
            messagebox.showinfo("Newton", "Подключение успешно (mock-режим)")
        else:
            messagebox.showerror("Newton", "Ошибка подключения")

    def _test_confluence(self):
        client = ConfluenceClient()
        if client.check_connection():
            messagebox.showinfo("Confluence", "Подключение успешно (mock-режим)")
        else:
            messagebox.showerror("Confluence", "Ошибка подключения")

    def _test_telegram(self):
        client = TelegramClient()
        if client.check_connection():
            messagebox.showinfo("Telegram", "Подключение успешно (mock-режим)")
        else:
            messagebox.showinfo("Telegram", "Telegram не настроен (опционально)")

    def _choose_confluence_parent(self):
        from ui.confluence_parent_dialog import ConfluenceParentDialog
        dialog = ConfluenceParentDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            confluence_e = self._block_entries.get("confluence", {})
            if "parent_page_id" in confluence_e:
                confluence_e["parent_page_id"].delete(0, tk.END)
                confluence_e["parent_page_id"].insert(0, dialog.result.get("id", ""))
            if "parent_page_title" in confluence_e:
                confluence_e["parent_page_title"].delete(0, tk.END)
                confluence_e["parent_page_title"].insert(0, dialog.result.get("title", ""))


def show_item_params_dialog(parent_frame, item):
    dialog = tk.Toplevel(parent_frame)
    dialog.title("Параметры строки")
    dialog.geometry("450x400")
    dialog.transient(parent_frame)
    dialog.grab_set()

    frame = ttk.Frame(dialog, padding=10)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Шаблон:").grid(row=0, column=0, sticky=tk.W, pady=5)
    template_var = tk.StringVar(value=item.protocol_template)
    combo = ttk.Combobox(frame, textvariable=template_var, state="readonly", width=40)
    combo["values"] = ["management_summary", "project_standard", "project_detailed", "business_process_discovery"]
    combo.grid(row=0, column=1, sticky=tk.W, pady=5)

    ttk.Label(frame, text="Режим:").grid(row=1, column=0, sticky=tk.W, pady=5)
    mode_var = tk.StringVar(value=item.protocol_mode)
    mode_combo = ttk.Combobox(frame, textvariable=mode_var, state="readonly", width=40)
    mode_combo["values"] = ["auto", "brief", "detailed"]
    mode_combo.grid(row=1, column=1, sticky=tk.W, pady=5)

    ttk.Label(frame, text="ID родительской страницы:").grid(row=2, column=0, sticky=tk.W, pady=5)
    page_id_var = tk.StringVar(value=item.parent_page_id or "")
    ttk.Entry(frame, textvariable=page_id_var, width=40).grid(row=2, column=1, sticky=tk.W, pady=5)

    send_var = tk.BooleanVar(value=item.send_telegram)
    ttk.Checkbutton(frame, text="Отправлять в Telegram", variable=send_var).grid(
        row=3, column=0, columnspan=2, sticky=tk.W, pady=5
    )

    def save():
        item.protocol_template = template_var.get()
        item.protocol_mode = mode_var.get()
        item.parent_page_id = page_id_var.get() or None
        item.send_telegram = send_var.get()
        dialog.destroy()

    ttk.Button(frame, text="Сохранить", command=save).grid(row=4, column=0, columnspan=2, pady=10)
import importlib
import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from dotenv import load_dotenv, set_key

import settings
from services.bitlink_service import BitlinkClient
from services.confluence_service import ConfluenceClient
from services.runtime_config import reload_runtime_config
from services.telegram_service import TelegramClient
from services.transcription_service import TranscriptionClient


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

        self._build_llm_block()

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

    def _build_llm_block(self):
        frame = ttk.LabelFrame(self.scrollable, text="Нейросеть / LLM", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame, text="Провайдер:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._llm_provider_var = tk.StringVar(value="onebit_newton_cli")
        provider_combo = ttk.Combobox(frame, textvariable=self._llm_provider_var, state="readonly", width=25)
        provider_combo["values"] = ["mock", "onebit_newton_cli", "openai_compatible"]
        provider_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        provider_combo.bind("<<ComboboxSelected>>", self._on_llm_provider_change)

        # ── Newton CLI fields (row 1-4) ──
        ttk.Label(frame, text="Путь CLI:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._llm_cli_path_entry = ttk.Entry(frame, width=50)
        self._llm_cli_path_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(frame, text="Модель:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self._llm_cli_model_var = tk.StringVar(value="gpt4")
        model_combo = ttk.Combobox(frame, textvariable=self._llm_cli_model_var, state="readonly", width=15)
        model_combo["values"] = ["llama", "gpt4"]
        model_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(frame, text="Таймаут (сек):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self._llm_cli_timeout_entry = ttk.Entry(frame, width=10)
        self._llm_cli_timeout_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        self._llm_cli_btn_frame = ttk.Frame(frame)
        self._llm_cli_btn_frame.grid(row=4, column=0, columnspan=3, pady=5, sticky=tk.W)
        ttk.Button(self._llm_cli_btn_frame, text="Обнаружить CLI", command=self._discover_cli).pack(side=tk.LEFT, padx=3)
        ttk.Button(self._llm_cli_btn_frame, text="Проверить CLI", command=self._check_cli).pack(side=tk.LEFT, padx=3)

        # ── OpenAI fields (row 5-8) ──
        ttk.Label(frame, text="Base URL:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self._llm_url_entry = ttk.Entry(frame, width=50)
        self._llm_url_entry.grid(row=5, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(frame, text="API Key:").grid(row=6, column=0, sticky=tk.W, pady=2)
        self._llm_key_entry = ttk.Entry(frame, width=50, show="*")
        self._llm_key_entry.grid(row=6, column=1, sticky=tk.W, padx=5, pady=2)

        self._llm_show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Показать API Key", variable=self._llm_show_key_var,
                        command=self._toggle_llm_key_visibility).grid(row=6, column=2, sticky=tk.W, padx=5)

        ttk.Label(frame, text="Model:").grid(row=7, column=0, sticky=tk.W, pady=2)
        self._llm_model_entry = ttk.Entry(frame, width=50)
        self._llm_model_entry.grid(row=7, column=1, sticky=tk.W, padx=5, pady=2)

        # ── Status + button (row 8-9) ──
        ttk.Label(frame, text="Статус:").grid(row=8, column=0, sticky=tk.W, pady=2)
        self._llm_status_label = ttk.Label(frame, text="Не проверено", foreground="gray")
        self._llm_status_label.grid(row=8, column=1, sticky=tk.W, padx=5, pady=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=9, column=0, columnspan=3, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="Проверить LLM", command=self._test_llm).pack(side=tk.LEFT, padx=3)

        self._llm_widgets = {
            "provider": self._llm_provider_var,
            "cli_path": self._llm_cli_path_entry,
            "cli_model": self._llm_cli_model_var,
            "cli_timeout": self._llm_cli_timeout_entry,
            "cli_btn_frame": self._llm_cli_btn_frame,
            "url": self._llm_url_entry,
            "key": self._llm_key_entry,
            "model": self._llm_model_entry,
            "status": self._llm_status_label,
        }

        self._show_provider_fields("onebit_newton_cli")

    def _show_provider_fields(self, provider):
        is_openai = (provider == "openai_compatible")
        is_newton = (provider == "onebit_newton_cli")
        is_mock = (provider == "mock")

        # Newton CLI fields
        state_visible = tk.NORMAL if is_newton else tk.DISABLED
        self._llm_cli_path_entry.configure(state=state_visible)
        self._llm_cli_model_var.set("gpt4")
        self._llm_cli_timeout_entry.configure(state=state_visible)
        for child in self._llm_cli_btn_frame.winfo_children():
            child.configure(state=state_visible)

        # OpenAI fields
        state_openai = tk.NORMAL if is_openai else tk.DISABLED
        self._llm_url_entry.configure(state=state_openai)
        self._llm_key_entry.configure(state=state_openai)
        self._llm_model_entry.configure(state=state_openai)

        if is_mock:
            self._llm_status_label.configure(text="Mock — проверка не требуется", foreground="#cc6600")
        else:
            self._llm_status_label.configure(text="Не проверено", foreground="gray")

    def _on_llm_provider_change(self, event=None):
        p = self._llm_provider_var.get()
        self._llm_status_label.configure(text="Не проверено", foreground="gray")
        self._show_provider_fields(p)

    def _toggle_llm_key_visibility(self):
        show = self._llm_show_key_var.get()
        self._llm_key_entry.configure(show="" if show else "*")

    def _discover_cli(self):
        import shutil
        candidates = [
            r"C:\Users\egore\AppData\Local\NewtonCLI\newton.cmd",
            "newton.cmd",
            "newton",
        ]
        for path in candidates:
            resolved = shutil.which(path)
            if resolved:
                self._llm_cli_path_entry.delete(0, tk.END)
                self._llm_cli_path_entry.insert(0, resolved)
                self._llm_status_label.configure(text=f"Найден: {resolved}", foreground="green")
                return
        self._llm_status_label.configure(text="CLI не найден", foreground="red")

    def _check_cli(self):
        path = self._llm_cli_path_entry.get().strip()
        if not path:
            self._llm_status_label.configure(text="Укажите путь CLI", foreground="red")
            return
        import os

        from services.llm_providers import OneBitNewtonCLIProvider
        token = os.getenv("NEWTON_TOKEN", "")
        try:
            timeout = int(self._llm_cli_timeout_entry.get().strip() or "15")
        except ValueError:
            timeout = 15
        p = OneBitNewtonCLIProvider(cli_path=path, model="gpt4", token=token, timeout_seconds=timeout)
        result = p.check_connection()
        if result.ok:
            self._llm_status_label.configure(text=result.safe_message, foreground="green")
        else:
            self._llm_status_label.configure(text=result.safe_message, foreground="red")

    def _test_llm(self):
        pt = self._llm_provider_var.get()

        if pt == "mock":
            self._llm_status_label.configure(text="Mock — проверка не требуется", foreground="#cc6600")
            return

        if pt == "onebit_newton_cli":
            import os

            from services.llm_providers import OneBitNewtonCLIProvider
            path = self._llm_cli_path_entry.get().strip()
            model = self._llm_cli_model_var.get()
            token = os.getenv("NEWTON_TOKEN", "")
            try:
                timeout = int(self._llm_cli_timeout_entry.get().strip() or "120")
            except ValueError:
                timeout = 120
            p = OneBitNewtonCLIProvider(cli_path=path, model=model, token=token, timeout_seconds=timeout)
            result = p.check_connection()
            if result.ok:
                self._llm_status_label.configure(text=result.safe_message, foreground="green")
            else:
                self._llm_status_label.configure(text=result.safe_message, foreground="red")
            return

        if pt == "openai_compatible":
            url = self._llm_url_entry.get().strip()
            key = self._llm_key_entry.get().strip()
            model = self._llm_model_entry.get().strip()

            if not url or not key:
                self._llm_status_label.configure(text="Ошибка: укажите Base URL и API Key", foreground="red")
                return

            from services.llm_service import LLMClient
            try:
                client = LLMClient(api_url=url, api_key=key, model=model, mock_mode=False)
                conn = client.check_connection()
                if not conn:
                    self._llm_status_label.configure(text="Ошибка: нет соединения с API", foreground="red")
                    return

                smoke_schema = {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}
                result, raw = client.generate_json(
                    system_prompt="Return JSON with status: ok",
                    user_prompt="Return {\"status\": \"ok\"}",
                    json_schema=smoke_schema,
                )
                if result.get("status") == "ok":
                    self._llm_status_label.configure(text=f"OK — модель: {model}", foreground="green")
                else:
                    self._llm_status_label.configure(text=f"OK, но ответ: {result}", foreground="#cc6600")
            except Exception as e:
                self._llm_status_label.configure(text=f"Ошибка: {e}", foreground="red")

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

        self._llm_provider_var.set(os.getenv("LLM_PROVIDER", "onebit_newton_cli"))
        self._llm_cli_path_entry.delete(0, tk.END)
        self._llm_cli_path_entry.insert(0, os.getenv("ONEBIT_CLI_PATH", r"C:\Users\egore\AppData\Local\NewtonCLI\newton.cmd"))
        self._llm_cli_model_var.set(os.getenv("LLM_MODEL", "gpt4"))
        self._llm_cli_timeout_entry.delete(0, tk.END)
        self._llm_cli_timeout_entry.insert(0, os.getenv("ONEBIT_CLI_TIMEOUT_SECONDS", "120"))
        self._llm_url_entry.delete(0, tk.END)
        self._llm_url_entry.insert(0, os.getenv("LLM_API_URL", ""))
        self._llm_key_entry.delete(0, tk.END)
        self._llm_key_entry.insert(0, os.getenv("LLM_API_KEY", ""))
        self._llm_model_entry.delete(0, tk.END)
        self._llm_model_entry.insert(0, os.getenv("LLM_MODEL", "gpt4"))
        self._show_provider_fields(self._llm_provider_var.get())

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
            "LLM_PROVIDER": self._llm_provider_var.get(),
            "LLM_MOCK": "true" if self._llm_provider_var.get() == "mock" else "false",
            "LLM_API_URL": self._llm_url_entry.get(),
            "LLM_API_KEY": self._llm_key_entry.get(),
            "LLM_MODEL": self._llm_model_entry.get() or self._llm_cli_model_var.get(),
            "ONEBIT_CLI_PATH": self._llm_cli_path_entry.get(),
            "ONEBIT_CLI_TRANSPORT": "native",
            "ONEBIT_CLI_TIMEOUT_SECONDS": self._llm_cli_timeout_entry.get(),
        }

        for key, value in env_map.items():
            set_key(str(self.env_path), key, value)

        importlib.reload(settings)
        reload_runtime_config()
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

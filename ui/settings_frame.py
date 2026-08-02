import importlib
import json
import os
import threading
import tkinter as tk
from datetime import UTC, datetime
from pathlib import Path
from tkinter import messagebox, ttk

import requests
from dotenv import load_dotenv, set_key

import settings
from services.connection_checks import (
    ConnectionCheckResult,
    make_error_result,
    make_mock_result,
    make_not_configured_result,
    make_not_implemented_result,
)
from services.runtime_config import reload_runtime_config


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
        self._block_btn = {}
        self._block_status = {}
        self._service_blocks = []
        self._build()
        self._load_settings()

    # ── UI helpers ──

    def _run_on_ui(self, callback, *args):
        if not self.winfo_exists():
            return
        self.after(0, lambda: callback(*args))

    def _start_async_check(self, check_id, btn, status_label,
                           worker_fn, on_complete):
        if getattr(self, f'_checking_{check_id}', False):
            return
        setattr(self, f'_checking_{check_id}', True)
        btn.configure(state=tk.DISABLED)
        status_label.configure(text="Проверка...", foreground="blue")

        def runner():
            try:
                result = worker_fn()
            except Exception as e:
                import traceback
                result = ConnectionCheckResult(
                    service_id=check_id, status="FAIL",
                    stage="internal_error",
                    safe_message=str(e)[:200],
                    details={"traceback": traceback.format_exc()[-500:]})
            finally:
                def restore():
                    try:
                        btn.configure(state=tk.NORMAL)
                        setattr(self, f'_checking_{check_id}', False)
                    except Exception:
                        pass
                self._run_on_ui(restore)
            self._run_on_ui(lambda r=result: on_complete(r))

        threading.Thread(target=runner, daemon=True).start()

    @staticmethod
    def _color_for_status(status):
        return {
            "PASS": "green",
            "FAIL": "red",
            "MOCK": "#cc6600",
            "NOT_IMPLEMENTED": "#cc6600",
            "NOT_CONFIGURED": "gray",
            "TIMEOUT": "red",
            "SKIPPED": "gray",
        }.get(status, "gray")

    def _make_block_key(self, title):
        return title.lower().replace(".", "_")

    # ── Build ──

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

        ttk.Button(self.scrollable, text="Проверить все подключения",
                   command=self._check_all_connections).pack(pady=5)

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
        ], self._test_confluence, extra_btn_text="Выбрать страницу",
            extra_btn_command=self._choose_confluence_parent)

        self._build_block("Telegram", [
            ("bot_token", "Bot Token:", "*"),
            ("chat_id", "Chat ID:", None),
        ], self._test_telegram)

        self._build_llm_block()
        self._build_protocol_block()

        ttk.Button(self.scrollable, text="Сохранить настройки",
                   command=self._save_settings).pack(pady=10)

    def _build_block(self, title, fields, test_callback,
                     extra_btn_text=None, extra_btn_command=None):
        frame = ttk.LabelFrame(self.scrollable, text=title, padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        entries = {}
        for i, (key, label, mask) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=2)
            show_value = "*" if mask else ""
            entry = ttk.Entry(frame, width=50, show=show_value)
            entry.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            entries[key] = entry

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=5, sticky=tk.W)

        btn = ttk.Button(btn_frame, text="Проверить подключение")
        btn.pack(side=tk.LEFT, padx=3)
        if extra_btn_text and extra_btn_command:
            ttk.Button(btn_frame, text=extra_btn_text,
                       command=extra_btn_command).pack(side=tk.LEFT, padx=3)

        status_label = ttk.Label(frame, text="Не проверено", foreground="gray")
        status_label.grid(row=len(fields) + 1, column=0, columnspan=2,
                          sticky=tk.W, pady=2)

        key = self._make_block_key(title)
        btn.configure(command=lambda b=btn, sl=status_label, cb=test_callback: cb(b, sl))

        self._block_entries[key] = entries
        self._block_btn[key] = btn
        self._block_status[key] = status_label
        self._service_blocks.append({
            "title": title,
            "check_id": key,
            "entries": entries,
            "btn": btn,
            "status_label": status_label,
        })

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
        ttk.Checkbutton(frame, text="Продолжать обработку после ошибки",
                        variable=self._continue_var).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=2
        )

    # ── LLM block ──

    def _build_llm_block(self):
        frame = ttk.LabelFrame(self.scrollable, text="Нейросеть / LLM", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame, text="Провайдер:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._llm_provider_var = tk.StringVar(value="onebit_newton_cli")
        provider_combo = ttk.Combobox(frame, textvariable=self._llm_provider_var, state="readonly", width=25)
        provider_combo["values"] = ["mock", "onebit_newton_cli", "openai_compatible"]
        provider_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        provider_combo.bind("<<ComboboxSelected>>", self._on_llm_provider_change)

        # Status label
        ttk.Label(frame, text="Статус:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._llm_status_label = ttk.Label(frame, text="Не проверено", foreground="gray")
        self._llm_status_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        # Sub-panels
        self._onebit_panel = ttk.Frame(frame, padding=(0, 5, 0, 0))
        self._onebit_panel.grid(row=2, column=0, columnspan=3, sticky=tk.W + tk.E)
        self._onebit_panel.grid_remove()
        self._build_onebit_panel()

        self._openai_panel = ttk.Frame(frame, padding=(0, 5, 0, 0))
        self._openai_panel.grid(row=2, column=0, columnspan=3, sticky=tk.W + tk.E)
        self._openai_panel.grid_remove()
        self._build_openai_panel()

        self._mock_panel = ttk.Frame(frame, padding=(0, 5, 0, 0))
        self._mock_panel.grid(row=2, column=0, columnspan=3, sticky=tk.W + tk.E)
        self._mock_panel.grid_remove()
        self._build_mock_panel()

        self._show_provider_panel("onebit_newton_cli")

    def _build_onebit_panel(self):
        p = self._onebit_panel

        ttk.Label(p, text="Токен БИТ Ньютон:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._llm_onebit_token_entry = ttk.Entry(p, width=50, show="*")
        self._llm_onebit_token_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        self._llm_onebit_show_token_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(p, text="Показать", variable=self._llm_onebit_show_token_var,
                        command=self._toggle_onebit_token_visibility).grid(
            row=0, column=2, sticky=tk.W, padx=5)

        ttk.Label(p, text="Путь CLI:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._llm_onebit_cli_path_entry = ttk.Entry(p, width=50)
        self._llm_onebit_cli_path_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(p, text="Модель:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self._llm_onebit_model_var = tk.StringVar(value="gpt4")
        model_combo = ttk.Combobox(p, textvariable=self._llm_onebit_model_var, state="readonly", width=15)
        model_combo["values"] = ["llama", "gpt4"]
        model_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(p, text="Таймаут (сек):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self._llm_onebit_timeout_entry = ttk.Entry(p, width=10)
        self._llm_onebit_timeout_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        btn_frame = ttk.Frame(p)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="Обнаружить CLI", command=self._discover_cli).pack(side=tk.LEFT, padx=3)
        self._llm_version_btn = ttk.Button(btn_frame, text="Проверить версию", command=self._check_cli_version)
        self._llm_version_btn.pack(side=tk.LEFT, padx=3)
        self._llm_health_btn = ttk.Button(btn_frame, text="Проверить health", command=self._check_cli_health)
        self._llm_health_btn.pack(side=tk.LEFT, padx=3)
        self._llm_token_btn = ttk.Button(btn_frame, text="Проверить токен и LLM",
                                         command=self._check_cli_token_and_llm)
        self._llm_token_btn.pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Копировать диагностику", command=self._copy_diagnostics).pack(side=tk.LEFT, padx=3)

    def _build_openai_panel(self):
        p = self._openai_panel

        ttk.Label(p, text="Base URL:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._llm_openai_url_entry = ttk.Entry(p, width=50)
        self._llm_openai_url_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(p, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._llm_openai_key_entry = ttk.Entry(p, width=50, show="*")
        self._llm_openai_key_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        self._llm_openai_show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(p, text="Показать API Key", variable=self._llm_openai_show_key_var,
                        command=self._toggle_openai_key_visibility).grid(
            row=1, column=2, sticky=tk.W, padx=5)

        ttk.Label(p, text="Model:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self._llm_openai_model_entry = ttk.Entry(p, width=50)
        self._llm_openai_model_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        btn_frame = ttk.Frame(p)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=5, sticky=tk.W)
        ttk.Button(btn_frame, text="Проверить LLM", command=self._test_openai_llm).pack(side=tk.LEFT, padx=3)

    def _build_mock_panel(self):
        p = self._mock_panel
        ttk.Label(p, text="Демо-режим — проверка не требуется. Ответы генерируются локально.",
                  foreground="#cc6600", wraplength=400).grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=5)

    # ── Panel switching ──

    def _show_provider_panel(self, provider):
        self._onebit_panel.grid_remove()
        self._openai_panel.grid_remove()
        self._mock_panel.grid_remove()

        if provider == "onebit_newton_cli":
            self._onebit_panel.grid()
            self._llm_status_label.configure(text="Не проверено", foreground="gray")
        elif provider == "openai_compatible":
            self._openai_panel.grid()
            self._llm_status_label.configure(text="Не проверено", foreground="gray")
        elif provider == "mock":
            self._mock_panel.grid()
            self._llm_status_label.configure(text="Mock — проверка не требуется", foreground="#cc6600")

    def _on_llm_provider_change(self, event=None):
        self._show_provider_panel(self._llm_provider_var.get())

    # ── Token visibility ──

    def _toggle_onebit_token_visibility(self):
        show = self._llm_onebit_show_token_var.get()
        self._llm_onebit_token_entry.configure(show="" if show else "*")

    def _toggle_openai_key_visibility(self):
        show = self._llm_openai_show_key_var.get()
        self._llm_openai_key_entry.configure(show="" if show else "*")

    # ── Newton CLI helpers ──

    def _get_cli_path(self):
        return self._llm_onebit_cli_path_entry.get().strip()

    def _get_onebit_token(self):
        return self._llm_onebit_token_entry.get().strip()

    def _get_onebit_model(self):
        return self._llm_onebit_model_var.get()

    def _get_onebit_timeout(self):
        try:
            return int(self._llm_onebit_timeout_entry.get().strip() or "120")
        except ValueError:
            return 120

    def _build_cli_args(self, subcommand):
        path = self._get_cli_path()
        if path.endswith(".cmd") or path.endswith(".bat"):
            return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", path, subcommand]
        return [path, subcommand]

    # ── Newton CLI diagnostics ──

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
                self._llm_onebit_cli_path_entry.delete(0, tk.END)
                self._llm_onebit_cli_path_entry.insert(0, resolved)
                self._llm_status_label.configure(text=f"Найден: {resolved}", foreground="green")
                return
        self._llm_status_label.configure(text="CLI не найден", foreground="red")

    def _check_cli_version(self):
        from services.process_runner import run_process as _rp

        path = self._get_cli_path()
        if not path:
            self._llm_status_label.configure(text="Укажите путь CLI", foreground="red")
            return

        self._llm_status_label.configure(text="Проверка версии...", foreground="gray")
        self._llm_version_btn.configure(state=tk.DISABLED)

        def worker():
            args = self._build_cli_args("version")
            result = _rp(args, timeout_seconds=15)
            self._run_on_ui(lambda: self._on_version_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_version_result(self, result):
        self._llm_version_btn.configure(state=tk.NORMAL)
        if result.returncode == 0:
            self._llm_status_label.configure(
                text=f"Версия: {result.stdout.strip()[:100]}", foreground="green")
        else:
            self._llm_status_label.configure(
                text=f"CLI exit {result.returncode}: {result.stderr[:150]}", foreground="red")

    def _check_cli_health(self):
        from services.process_runner import run_process as _rp

        path = self._get_cli_path()
        if not path:
            self._llm_status_label.configure(text="Укажите путь CLI", foreground="red")
            return

        self._llm_status_label.configure(text="Проверка health...", foreground="gray")
        self._llm_health_btn.configure(state=tk.DISABLED)

        def worker():
            args = self._build_cli_args("health")
            result = _rp(args, timeout_seconds=15)
            self._run_on_ui(lambda: self._on_health_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_health_result(self, result):
        self._llm_health_btn.configure(state=tk.NORMAL)
        if result.returncode == 0:
            self._llm_status_label.configure(
                text=f"Health OK: {result.stdout.strip()[:100]}", foreground="green")
            messagebox.showinfo("Health", "CLI health check прошёл успешно.\n\n"
                                "Примечание: health НЕ проверяет аутентификацию токена. "
                                "Для проверки токена нажмите «Проверить токен и LLM».")
        else:
            self._llm_status_label.configure(
                text=f"Health exit {result.returncode}", foreground="red")

    def _check_cli_token_and_llm(self):
        from services.llm_providers import OneBitNewtonCLIProvider, OneBitProviderError

        path = self._get_cli_path()
        token = self._get_onebit_token()
        model = self._get_onebit_model()
        timeout = self._get_onebit_timeout()

        if not path:
            self._llm_status_label.configure(text="Укажите путь CLI", foreground="red")
            return
        if not token:
            self._llm_status_label.configure(
                text="Ошибка: токен не указан. Заполните поле «Токен БИТ Ньютон».", foreground="red")
            return

        self._llm_status_label.configure(text="Проверяю токен и LLM...", foreground="#3366cc")
        self._llm_token_btn.configure(state=tk.DISABLED)
        self.update_idletasks()

        def worker():
            p = OneBitNewtonCLIProvider(cli_path=path, model=model, token=token, timeout_seconds=timeout)
            conn = p.check_connection()
            if not conn.ok:
                self._run_on_ui(lambda: self._on_token_result(
                    ok=False, text=f"CLI: {conn.safe_message}", foreground="red"))
                return
            try:
                result = p.generate(
                    system_prompt="Return valid JSON with exactly one key: status, value: ok. "
                                  "Output ONLY the JSON object, no explanation, no markdown fences.",
                    user_prompt='{"status": "ok"}',
                    model=model,
                    temperature=0.1,
                    max_tokens=128,
                )
                parsed = json.loads(result)
                if parsed.get("status") == "ok":
                    self._run_on_ui(lambda: self._on_token_result(
                        ok=True, text=f"OK — {model}", foreground="green"))
                else:
                    self._run_on_ui(lambda: self._on_token_result(
                        ok=True, text=f"OK, но неожиданный ответ: {result[:100]}",
                        foreground="#cc6600"))
            except OneBitProviderError as e:
                self._run_on_ui(lambda e=e: self._on_token_error(e))
            except Exception as e:
                self._run_on_ui(lambda e=e: self._on_token_result(
                    ok=False, text=f"Ошибка: {e}", foreground="red"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_token_result(self, ok, text, foreground):
        self._llm_token_btn.configure(state=tk.NORMAL)
        self._llm_status_label.configure(text=text, foreground=foreground)

    def _on_token_error(self, e):
        self._llm_token_btn.configure(state=tk.NORMAL)
        self._llm_status_label.configure(text=f"Ошибка [{e.code}]: {e.safe_message}", foreground="red")
        messagebox.showerror("Ошибка Newton CLI",
                             f"Код: {e.code}\n"
                             f"Этап: {e.stage}\n"
                             f"{e.safe_message}\n\n"
                             f"stderr: {e.safe_stderr[:200] if e.safe_stderr else '(нет)'}")

    def _copy_diagnostics(self):
        from services.process_runner import run_process

        path = self._get_cli_path()
        lines = []
        lines.append("=== Диагностика OneBit Newton CLI ===")
        lines.append(f"CLI путь: {path}")
        lines.append(f"Токен задан: {'да' if self._get_onebit_token() else 'нет'}")
        lines.append(f"Модель: {self._get_onebit_model()}")
        lines.append(f"Таймаут: {self._get_onebit_timeout()}с")

        lines.append(f"Файл CLI существует: {os.path.isfile(path) if path else 'путь не указан'}")

        if path and os.path.isfile(path):
            rv = run_process(self._build_cli_args("version"), timeout_seconds=15)
            lines.append(f"CLI version exit={rv.returncode}")
            if rv.stdout.strip():
                lines.append(f"  stdout: {rv.stdout.strip()[:200]}")
            if rv.stderr.strip():
                lines.append(f"  stderr: {rv.stderr.strip()[:200]}")

            rh = run_process(self._build_cli_args("health"), timeout_seconds=15)
            lines.append(f"CLI health exit={rh.returncode}")
            if rh.stdout.strip():
                lines.append(f"  stdout: {rh.stdout.strip()[:200]}")
            if rh.stderr.strip():
                lines.append(f"  stderr: {rh.stderr.strip()[:200]}")

        lines.append(f"NEWTON_TOKEN env: {'задан' if os.getenv('NEWTON_TOKEN') else 'не задан'}")
        lines.append(f"ONEBIT_LLM_TOKEN env: {'задан' if os.getenv('ONEBIT_LLM_TOKEN') else 'не задан'}")

        text = "\n".join(lines)
        self.clipboard_clear()
        self.clipboard_append(text)
        self._llm_status_label.configure(text="Диагностика скопирована в буфер обмена", foreground="#3366cc")

    def _test_openai_llm(self):
        url = self._llm_openai_url_entry.get().strip()
        key = self._llm_openai_key_entry.get().strip()
        model = self._llm_openai_model_entry.get().strip()

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

    # ── Service check implementations ──

    def _check_bitlink_impl(self):
        entries = self._block_entries.get("бит_link", {})
        email_w = entries.get("email")
        password_w = entries.get("password")
        _ = email_w.get().strip() if email_w else ""
        _ = password_w.get().strip() if password_w else ""

        if settings.BITLINK_MOCK:
            return make_mock_result("bitlink")
        return make_not_implemented_result("bitlink")

    def _check_newton_impl(self):
        entries = self._block_entries.get("newton", {})
        token_w = entries.get("token")
        path_w = entries.get("path")
        base_url_w = entries.get("base_url")
        _ = token_w.get().strip() if token_w else ""
        _ = path_w.get().strip() if path_w else ""
        _ = base_url_w.get().strip() if base_url_w else ""

        if settings.NEWTON_MOCK:
            return make_mock_result("newton")
        return make_not_implemented_result("newton")

    def _check_confluence_impl(self):
        entries = self._block_entries.get("confluence", {})
        base_url = entries.get("base_url")
        token_ent = entries.get("token")
        space_key_ent = entries.get("space_key")
        ppid_ent = entries.get("parent_page_id")
        pptitle_ent = entries.get("parent_page_title")

        base_url_val = base_url.get().strip().rstrip("/") if base_url else ""
        token_val = token_ent.get().strip() if token_ent else ""
        space_key_val = space_key_ent.get().strip() if space_key_ent else ""
        parent_id_val = ppid_ent.get().strip() if ppid_ent else ""
        parent_title_val = pptitle_ent.get().strip() if pptitle_ent else ""

        if settings.CONFLUENCE_PROVIDER == "mock":
            return make_mock_result("confluence")

        if not base_url_val or not token_val:
            missing = []
            if not base_url_val:
                missing.append("Base URL")
            if not token_val:
                missing.append("Токен")
            return make_not_configured_result("confluence", missing)

        headers = {"Authorization": f"Bearer {token_val}"}
        start = datetime.now(UTC)

        # Stage 1: auth check
        try:
            r = requests.get(f"{base_url_val}/rest/api/user/current",
                             headers=headers, timeout=15)
            if r.status_code != 200:
                return ConnectionCheckResult(
                    service_id="confluence", provider="rest",
                    status="FAIL", stage="auth_check",
                    safe_message=f"Ошибка аутентификации: HTTP {r.status_code}",
                    http_status=r.status_code,
                    endpoint_or_command=f"{base_url_val}/rest/api/user/current")
            user_data = r.json()
            user_display = user_data.get("displayName", user_data.get("username", "?"))
        except requests.RequestException as e:
            return ConnectionCheckResult(
                service_id="confluence", provider="rest",
                status="FAIL", stage="auth_check",
                safe_message=f"Нет соединения: {str(e)[:200]}",
                endpoint_or_command=f"{base_url_val}/rest/api/user/current")

        # Stage 2: space check
        if space_key_val:
            try:
                r = requests.get(f"{base_url_val}/rest/api/space/{space_key_val}",
                                 headers=headers, timeout=15)
                if r.status_code != 200:
                    return ConnectionCheckResult(
                        service_id="confluence", provider="rest",
                        status="FAIL", stage="space_check",
                        safe_message=f"Пространство '{space_key_val}' не найдено (HTTP {r.status_code})",
                        http_status=r.status_code,
                        endpoint_or_command=f"{base_url_val}/rest/api/space/{space_key_val}")
            except requests.RequestException as e:
                return ConnectionCheckResult(
                    service_id="confluence", provider="rest",
                    status="FAIL", stage="space_check",
                    safe_message=f"Ошибка проверки пространства: {str(e)[:200]}")

        # Stage 3: parent page check
        if parent_id_val:
            try:
                r = requests.get(f"{base_url_val}/rest/api/content/{parent_id_val}",
                                 headers=headers, timeout=15)
                if r.status_code != 200:
                    return ConnectionCheckResult(
                        service_id="confluence", provider="rest",
                        status="FAIL", stage="parent_check",
                        safe_message=f"Родительская страница '{parent_id_val}' не найдена (HTTP {r.status_code})",
                        http_status=r.status_code,
                        endpoint_or_command=f"{base_url_val}/rest/api/content/{parent_id_val}")
            except requests.RequestException as e:
                return ConnectionCheckResult(
                    service_id="confluence", provider="rest",
                    status="FAIL", stage="parent_check",
                    safe_message=f"Ошибка проверки родительской страницы: {str(e)[:200]}")

        latency = (datetime.now(UTC) - start).total_seconds()
        parent_info = f", родительская: {parent_title_val or parent_id_val}" if parent_id_val else ""
        return ConnectionCheckResult(
            service_id="confluence", provider="rest",
            status="PASS", stage="all",
            safe_message=f"OK — пользователь {user_display}, пространство {space_key_val}{parent_info}",
            latency_seconds=latency,
            endpoint_or_command=base_url_val)

    def _check_telegram_impl(self):
        entries = self._block_entries.get("telegram", {})
        bot_token_w = entries.get("bot_token")
        chat_id_w = entries.get("chat_id")
        bot_token = bot_token_w.get().strip() if bot_token_w else ""
        chat_id = chat_id_w.get().strip() if chat_id_w else ""

        if settings.TELEGRAM_MOCK:
            return make_mock_result("telegram")

        if not bot_token:
            return make_not_configured_result("telegram", ["Bot Token"])
        if not chat_id:
            return make_not_configured_result("telegram", ["Chat ID"])

        start = datetime.now(UTC)

        # Stage 1: getMe
        try:
            r = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
            if r.status_code != 200 or not r.json().get("ok"):
                return ConnectionCheckResult(
                    service_id="telegram", provider="real",
                    status="FAIL", stage="getMe",
                    safe_message=f"Ошибка getMe: HTTP {r.status_code}",
                    http_status=r.status_code,
                    endpoint_or_command="api.telegram.org/getMe")
            bot_name = r.json().get("result", {}).get("username", "?")
        except requests.RequestException as e:
            return ConnectionCheckResult(
                service_id="telegram", provider="real",
                status="FAIL", stage="getMe",
                safe_message=f"Нет соединения с Telegram API: {str(e)[:200]}")

        # Stage 2: getChat
        try:
            r = requests.get(f"https://api.telegram.org/bot{bot_token}/getChat?chat_id={chat_id}", timeout=10)
            if r.status_code != 200 or not r.json().get("ok"):
                return ConnectionCheckResult(
                    service_id="telegram", provider="real",
                    status="FAIL", stage="getChat",
                    safe_message=f"Ошибка getChat: chat_id={chat_id}, HTTP {r.status_code}",
                    http_status=r.status_code)
            chat_info = r.json().get("result", {})
            chat_title = chat_info.get("title") or chat_info.get("first_name", chat_id)
        except requests.RequestException as e:
            return ConnectionCheckResult(
                service_id="telegram", provider="real",
                status="FAIL", stage="getChat",
                safe_message=f"Ошибка getChat: {str(e)[:200]}")

        latency = (datetime.now(UTC) - start).total_seconds()
        return ConnectionCheckResult(
            service_id="telegram", provider="real",
            status="PASS", stage="all",
            safe_message=f"OK — бот @{bot_name}, чат «{chat_title}»",
            latency_seconds=latency,
            endpoint_or_command="api.telegram.org")

    # ── Test button callbacks (receive btn + status_label from _build_block) ──

    def _test_bitlink(self, btn, status_label):
        def worker_fn():
            return self._check_bitlink_impl()
        def on_complete(result):
            color = self._color_for_status(result.status)
            status_label.configure(text=result.safe_message[:200], foreground=color)
        self._start_async_check("bitlink", btn, status_label, worker_fn, on_complete)

    def _test_newton(self, btn, status_label):
        def worker_fn():
            return self._check_newton_impl()
        def on_complete(result):
            color = self._color_for_status(result.status)
            status_label.configure(text=result.safe_message[:200], foreground=color)
        self._start_async_check("newton", btn, status_label, worker_fn, on_complete)

    def _test_confluence(self, btn, status_label):
        def worker_fn():
            return self._check_confluence_impl()
        def on_complete(result):
            color = self._color_for_status(result.status)
            text = result.safe_message[:200]
            if result.latency_seconds is not None:
                text += f" ({result.latency_seconds:.1f}с)"
            status_label.configure(text=text, foreground=color)
        self._start_async_check("confluence", btn, status_label, worker_fn, on_complete)

    def _test_telegram(self, btn, status_label):
        def worker_fn():
            return self._check_telegram_impl()
        def on_complete(result):
            color = self._color_for_status(result.status)
            status_label.configure(text=result.safe_message[:200], foreground=color)
        self._start_async_check("telegram", btn, status_label, worker_fn, on_complete)

    # ── "Проверить все подключения" ──

    def _check_all_connections(self):
        dialog = tk.Toplevel(self)
        dialog.title("Проверка всех подключений")
        dialog.geometry("600x350")
        dialog.transient(self)
        dialog.grab_set()

        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Выполняется проверка...", font=("Segoe UI", 11)).pack(pady=5)

        tree = ttk.Treeview(main_frame, columns=("service", "status", "message"), show="headings", height=10)
        tree.heading("service", text="Сервис")
        tree.heading("status", text="Статус")
        tree.heading("message", text="Сообщение")
        tree.column("service", width=130)
        tree.column("status", width=100)
        tree.column("message", width=340)
        tree.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Button(main_frame, text="Закрыть", command=dialog.destroy).pack(pady=5)

        service_map = {
            "бит_link": ("БИТ.Link", self._check_bitlink_impl),
            "newton": ("Newton", self._check_newton_impl),
            "confluence": ("Confluence", self._check_confluence_impl),
            "telegram": ("Telegram", self._check_telegram_impl),
        }

        def runner():
            for check_id, (display_name, impl_fn) in service_map.items():
                try:
                    result = impl_fn()
                except Exception:
                    result = make_error_result(check_id, "Неизвестная ошибка")

                tag = result.status.lower().replace("_", "")

                def add_row(r=result, dn=display_name, t=tag):
                    if not tree.winfo_exists():
                        return
                    tree.insert("", tk.END, values=(
                        dn, r.status, r.safe_message[:200],
                    ), tags=(t,))
                    try:
                        tree.tag_configure(t, foreground=SettingsFrame._color_for_status(r.status))
                    except Exception:
                        pass

                self._run_on_ui(add_row)

        threading.Thread(target=runner, daemon=True).start()

    # ── Load / Save ──

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

        provider = os.getenv("LLM_PROVIDER", "onebit_newton_cli")
        self._llm_provider_var.set(provider)

        onebit_token = os.getenv("ONEBIT_LLM_TOKEN", "") or os.getenv("NEWTON_TOKEN", "")
        self._llm_onebit_token_entry.delete(0, tk.END)
        self._llm_onebit_token_entry.insert(0, onebit_token)

        self._llm_onebit_cli_path_entry.delete(0, tk.END)
        self._llm_onebit_cli_path_entry.insert(0, os.getenv(
            "ONEBIT_CLI_PATH", r"C:\Users\egore\AppData\Local\NewtonCLI\newton.cmd"))
        self._llm_onebit_model_var.set(os.getenv("LLM_MODEL", "gpt4"))
        self._llm_onebit_timeout_entry.delete(0, tk.END)
        self._llm_onebit_timeout_entry.insert(0, os.getenv("ONEBIT_CLI_TIMEOUT_SECONDS", "120"))

        self._llm_openai_url_entry.delete(0, tk.END)
        self._llm_openai_url_entry.insert(0, os.getenv("LLM_API_URL", ""))
        self._llm_openai_key_entry.delete(0, tk.END)
        self._llm_openai_key_entry.insert(0, os.getenv("LLM_API_KEY", ""))
        self._llm_openai_model_entry.delete(0, tk.END)
        self._llm_openai_model_entry.insert(0, os.getenv("LLM_MODEL", "gpt-4o"))

        self._show_provider_panel(provider)

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
        }

        provider = self._llm_provider_var.get()
        if provider == "onebit_newton_cli":
            env_map["ONEBIT_LLM_TOKEN"] = self._llm_onebit_token_entry.get().strip()
            env_map["ONEBIT_CLI_PATH"] = self._llm_onebit_cli_path_entry.get().strip()
            env_map["ONEBIT_CLI_TRANSPORT"] = "native"
            env_map["ONEBIT_CLI_TIMEOUT_SECONDS"] = self._llm_onebit_timeout_entry.get().strip()
            env_map["LLM_MODEL"] = self._llm_onebit_model_var.get()
        elif provider == "openai_compatible":
            env_map["LLM_API_URL"] = self._llm_openai_url_entry.get().strip()
            env_map["LLM_API_KEY"] = self._llm_openai_key_entry.get().strip()
            env_map["LLM_MODEL"] = self._llm_openai_model_entry.get().strip()

        for key, value in env_map.items():
            set_key(str(self.env_path), key, value)

        importlib.reload(settings)
        reload_runtime_config()
        messagebox.showinfo("Успех", "Настройки сохранены")

    # ── Confluence parent page chooser ──

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

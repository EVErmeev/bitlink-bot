import json
import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import settings
from models.batch import BatchItem, BatchRun
from services.batch_service import BatchService
from services.processing_service import ProcessingService
from services.runtime_config import get_runtime_config
from services.runtime_estimator import RuntimeEstimator

_queue_controller = None


def get_queue_controller():
    global _queue_controller
    if _queue_controller is None:
        _queue_controller = QueueController()
    return _queue_controller


class QueueController:
    def __init__(self):
        self.batch_service = BatchService()
        if self.batch_service.batch_run is None:
            self.batch_service.create_batch()
        self.processing = False
        self.progress_queue = queue.Queue()

    def add_items(self, items: list[BatchItem]) -> BatchRun:
        return self.batch_service.create_or_add(items)

    def get_items(self) -> list[BatchItem]:
        if self.batch_service.batch_run:
            return self.batch_service.batch_run.items
        return []

    def remove_items(self, item_ids: list[str]):
        self.batch_service.remove_items(item_ids)

    def move_up(self, item_id: str):
        items = self.batch_service.batch_run.items
        for i, item in enumerate(items):
            if item.item_id == item_id and i > 0:
                items[i], items[i - 1] = items[i - 1], items[i]
                break

    def move_down(self, item_id: str):
        items = self.batch_service.batch_run.items
        for i, item in enumerate(items):
            if item.item_id == item_id and i < len(items) - 1:
                items[i], items[i + 1] = items[i + 1], items[i]
                break

    def start_processing(self, progress_callback=None):
        self.processing = True
        if self.batch_service.batch_run:
            self.batch_service.batch_run.cancel_requested = False
        thread = threading.Thread(target=self._process_batch, args=(progress_callback,), daemon=True)
        thread.start()

    def _process_batch(self, progress_callback):
        try:
            self.progress_queue.put(("worker_started", 0, None))
            batch = self.batch_service.batch_run
            batch.status = "processing"
            batch.started_at = datetime.now().isoformat()
            config = get_runtime_config()
            service = ProcessingService(progress_callback=self._on_progress, config=config)

            for i, item in enumerate(batch.items):
                if batch.cancel_requested:
                    item.status = "cancelled"
                    continue
                if item.status in ("completed", "skipped"):
                    continue

                batch.current_index = i
                item.status = "processing"
                item.error_details = None
                item.debug_directory = Path("debug") / batch.batch_id[:8] / item.item_id[:8]
                result = service.process_item(item)

                if not result["success"] and not config.batch_continue_after_error:
                    item.status = "failed"
                    if not item.error_details and result.get("error"):
                        item.error_details = str(result["error"])
                    batch.status = "failed"
                    break

            batch.completed_at = datetime.now().isoformat()

            completed = sum(1 for it in batch.items if it.status == "completed")
            failed = sum(1 for it in batch.items if it.status == "failed")
            cancelled = sum(1 for it in batch.items if it.status == "cancelled")
            validation_failed = sum(1 for it in batch.items if it.status == "validation_failed")
            processed = completed + failed + cancelled + validation_failed
            pending = sum(1 for it in batch.items if it.status == "pending")

            if processed == 0 and pending > 0:
                batch.status = "failed"
            elif processed == 0 and pending == 0:
                batch.status = "nothing_to_process"
            elif batch.cancel_requested:
                batch.status = "cancelled"
            elif failed > 0 or validation_failed > 0:
                batch.status = "completed_with_errors"
            else:
                batch.status = "completed"

            self._save_batch_report(batch, completed, failed, cancelled, validation_failed, pending)

            config = get_runtime_config()
            if config.telegram_send_batch_summary and config.telegram_enabled:
                try:
                    from services.telegram_service import TelegramClient
                    tg = TelegramClient(
                        bot_token=config.telegram_bot_token,
                        chat_id=config.telegram_chat_id,
                    )
                    summary = (
                        f"Пакетная обработка завершена\n"
                        f"Всего элементов: {len(batch.items)}\n"
                        f"Успешно: {completed}\n"
                        f"С ошибками: {failed}\n"
                        f"Валидация не пройдена: {validation_failed}\n"
                        f"Отменено: {cancelled}\n"
                        f"Ожидает: {pending}\n"
                        f"Статус: {batch.status}"
                    )
                    tg.send_batch_summary(summary)
                except Exception:
                    pass

        except Exception as e:
            if self.batch_service.batch_run:
                self.batch_service.batch_run.status = "failed"
                self._save_runtime_error_log(str(e))
        finally:
            self.processing = False
            self.progress_queue.put(("batch_done", 100, None))

    def _save_batch_report(self, batch, completed, failed, cancelled, validation_failed, pending):
        try:
            report_dir = settings.DATA_DIR / "batch_reports"
            report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = report_dir / f"batch_report_{timestamp}.json"
            report = {
                "batch_id": batch.batch_id,
                "status": batch.status,
                "started_at": batch.started_at,
                "completed_at": batch.completed_at,
                "summary": {
                    "total": len(batch.items),
                    "completed": completed,
                    "failed": failed,
                    "cancelled": cancelled,
                    "validation_failed": validation_failed,
                    "pending": pending,
                },
                "items": [],
            }
            for item in batch.items:
                report["items"].append({
                    "item_id": item.item_id,
                    "display_name": item.display_name,
                    "source_type": item.source_type,
                    "source_path": str(item.source_path) if item.source_path else None,
                    "status": item.status,
                    "status_message": item.status_message,
                    "error_details": item.error_details,
                    "result_url": item.result_url,
                    "actual_seconds": item.actual_seconds,
                    "protocol_template": item.protocol_template,
                    "protocol_mode": item.protocol_mode,
                })
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _save_runtime_error_log(self, error_text: str):
        try:
            log_dir = settings.DEBUG_DIR
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "runtime_error.log"
            timestamp = datetime.now().isoformat()
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {error_text}\n")
        except Exception:
            pass

    def _on_progress(self, stage, percent, item):
        self.progress_queue.put((stage, percent, item))

    def save_state(self):
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.batch_service.save_state(settings.DATA_DIR / "batch_state.json")


class SourceQueueFrame(ttk.Frame):
    TEMPLATE_NAMES = {
        "management_summary": "Управленческий протокол",
        "project_standard": "Проектный протокол",
        "project_detailed": "Подробный проектный протокол",
        "business_process_discovery": "Обследование бизнес-процессов",
    }

    MODE_NAMES = {"auto": "Авто", "brief": "Краткий", "detailed": "Подробный"}

    STAGE_NAMES = {
        "loading_source": "Загрузка источника",
        "transcribing": "Транскрибация",
        "extracting_metadata": "Извлечение метаданных",
        "extracting_items": "Извлечение элементов",
        "gap_audit": "Gap-аудит",
        "building_topics": "Построение тем",
        "generating_protocol": "Генерация протокола",
        "fact_validation": "Фактологическая проверка",
        "structure_validation": "Структурная проверка",
        "rendering": "Рендеринг",
        "publishing_confluence": "Публикация в Confluence",
        "sending_telegram": "Отправка в Telegram",
        "completed": "Завершён",
        "failed": "Ошибка",
    }

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.qc = get_queue_controller()
        self.estimator = RuntimeEstimator()
        self.config = get_runtime_config()
        self._current_stage = {}
        self._last_progress = {}
        self._elapsed_start = None
        self._build()
        self._refresh_table()
        self._start_progress_checker()

    def _build(self):
        banner_frame = ttk.LabelFrame(self, text=" РЕЖИМ РАБОТЫ ", padding=8)
        banner_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        self.banner_label = ttk.Label(banner_frame, text="", foreground="#cc6600", font=("Segoe UI", 9, "bold"))
        self.banner_label.pack()
        self._update_banner()

        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top, text="Очередь обработки", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="Назад", command=self._go_back).pack(side=tk.RIGHT)

        tree_frame = ttk.LabelFrame(self, text="Источники в очереди", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("№", "Имя", "Путь", "Размер", "Длит/слов", "Шаблон", "Режим", "Confluence", "Стадия", "Статус", "Длит", "Ошибка")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")

        widths = {
            "№": 40, "Имя": 180, "Путь": 150, "Размер": 70, "Длит/слов": 70,
            "Шаблон": 130, "Режим": 60, "Confluence": 100, "Стадия": 120,
            "Статус": 100, "Длит": 65, "Ошибка": 120,
        }
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths.get(col, 100))
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(tree_frame, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Delete>", self._remove_selected)
        self.tree.bind("<Double-1>", self._on_double_click)

        btn1 = ttk.Frame(self)
        btn1.pack(fill=tk.X, padx=10, pady=2)
        ttk.Button(btn1, text="Добавить файлы", command=self._add_files).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="Удалить выбранные", command=self._remove_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="Очистить список", command=self._clear_all).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="▲ Вверх", command=self._move_up).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="▼ Вниз", command=self._move_down).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="Изменить параметры", command=self._edit_params).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="Сбросить статус", command=self._reset_status).pack(side=tk.LEFT, padx=3)

        btn2 = ttk.Frame(self)
        btn2.pack(fill=tk.X, padx=10, pady=2)
        self.start_btn = ttk.Button(btn2, text="▶ Запустить обработку", command=self._start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=3)
        self.stop_btn = ttk.Button(btn2, text="■ Стоп", command=self._stop_processing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=3)

        self.empty_label = ttk.Label(self, text="Нет элементов для обработки", font=("Segoe UI", 10), foreground="gray")

        progress_frame = ttk.LabelFrame(self, text="Прогресс", padding=5)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress_label = ttk.Label(progress_frame, text="Готов к запуску", font=("Segoe UI", 9))
        self.progress_label.pack()

        self.stage_label = ttk.Label(progress_frame, text="", font=("Segoe UI", 8))
        self.stage_label.pack()

        self.overall_progress = ttk.Progressbar(progress_frame, mode="determinate", length=500)
        self.overall_progress.pack(fill=tk.X, pady=5)

        self.current_progress = ttk.Progressbar(progress_frame, mode="determinate", length=500)
        self.current_progress.pack(fill=tk.X)

        self.time_label = ttk.Label(progress_frame, text="", font=("Segoe UI", 8))
        self.time_label.pack()

        self._update_empty_label()

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        items = self.qc.get_items()
        for i, item in enumerate(items, 1):
            template_name = self.TEMPLATE_NAMES.get(item.protocol_template, item.protocol_template)
            mode_name = self.MODE_NAMES.get(item.protocol_mode, item.protocol_mode)
            size_str = ""
            if item.file_size_bytes:
                mb = item.file_size_bytes / (1024 * 1024)
                size_str = f"{mb:.1f} МБ"
            dur_str = ""
            if item.duration_seconds:
                dur_str = f"{int(item.duration_seconds) // 60} мин"
            elif item.word_count:
                dur_str = f"{item.word_count} слов"

            stage_text = self._current_stage.get(item.item_id, "")
            stage_display = self.STAGE_NAMES.get(stage_text, stage_text) if stage_text else ""

            status_text = item.status
            if item.status_message:
                status_text = item.status_message

            actual_str = ""
            if item.actual_seconds:
                m, s = divmod(int(item.actual_seconds), 60)
                actual_str = f"{m}:{s:02d}"

            error_summary = ""
            if item.error_details:
                error_summary = item.error_details[:60] + ("..." if len(item.error_details) > 60 else "")

            self.tree.insert("", tk.END, iid=item.item_id, values=(
                i, item.display_name, str(item.source_path or ""), size_str, dur_str,
                template_name, mode_name,
                item.parent_page_title or "По умолчанию",
                stage_display, status_text, actual_str, error_summary,
            ))
        self._update_empty_label()

    def _update_empty_label(self):
        items = self.qc.get_items()
        if not items:
            self.empty_label.pack(fill=tk.X, padx=10, pady=10)
        else:
            self.empty_label.pack_forget()

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Все поддерживаемые", "*.txt *.md *.mp4 *.webm *.m4v"), ("Все файлы", "*.*")],
            title="Выберите файлы для добавления в очередь"
        )
        if not paths:
            return

        config = get_runtime_config()
        batch = self.qc.batch_service.batch_run
        items = []
        for p in paths:
            fpath = Path(p)
            source_type = "local_video" if fpath.suffix.lower() in (".mp4", ".webm", ".m4v") else "local_transcript"
            size_bytes = fpath.stat().st_size
            wc = None
            if source_type == "local_transcript":
                try:
                    text = fpath.read_text(encoding="utf-8-sig")
                    from meeting_metadata import count_words
                    wc = count_words(text)
                except Exception:
                    pass

            item = BatchItem(
                source_type=source_type,
                source_path=fpath,
                display_name=fpath.name,
                file_size_bytes=size_bytes,
                word_count=wc,
                protocol_template=config.protocol_template,
                protocol_mode=config.protocol_mode,
            )
            item.debug_directory = Path("debug") / batch.batch_id[:8] / item.item_id[:8]
            items.append(item)

        self.qc.add_items(items)
        self._refresh_table()

    def _remove_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Предупреждение", "Выберите строки для удаления")
            return

        for iid in sel:
            item = self._find_item(iid)
            if item and item.status == "processing":
                messagebox.showwarning("Ошибка", f"Нельзя удалить строку в обработке: {item.display_name}")
                return

        self.qc.remove_items(list(sel))
        self._refresh_table()
        self._renumber()
        self._save_state()

    def _clear_all(self):
        if self.qc.processing:
            messagebox.showwarning("Ошибка", "Дождитесь завершения обработки")
            return
        if messagebox.askyesno("Подтверждение", "Очистить всю очередь?"):
            items = self.qc.get_items()
            self.qc.remove_items([i.item_id for i in items])
            self._refresh_table()
            self._save_state()

    def _move_up(self):
        sel = self.tree.selection()
        if sel:
            self.qc.move_up(sel[0])
            self._refresh_table()
            self._renumber()

    def _move_down(self):
        sel = self.tree.selection()
        if sel:
            self.qc.move_down(sel[0])
            self._refresh_table()
            self._renumber()

    def _edit_params(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Предупреждение", "Выберите строку")
            return
        item = self._find_item(sel[0])
        if item:
            from ui.settings_frame import show_item_params_dialog
            show_item_params_dialog(self, item)
            self._refresh_table()

    def _reset_status(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Предупреждение", "Выберите строки для сброса статуса")
            return
        for iid in sel:
            item = self._find_item(iid)
            if item and item.status != "processing":
                item.status = "pending"
                item.status_message = ""
                item.error_details = None
                item.result_url = None
                item.actual_seconds = None
                item.debug_directory = None
                batch = self.qc.batch_service.batch_run
                item.debug_directory = Path("debug") / batch.batch_id[:8] / item.item_id[:8]
        self._refresh_table()
        self._save_state()

    def _renumber(self):
        for i, item in enumerate(self.qc.get_items(), 1):
            for child in self.tree.get_children():
                if child == item.item_id:
                    vals = list(self.tree.item(child, "values"))
                    vals[0] = i
                    self.tree.item(child, values=vals)
                    break

    def _find_item(self, item_id: str):
        for item in self.qc.get_items():
            if item.item_id == item_id:
                return item
        return None

    def _on_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self._find_item(sel[0])
        if not item:
            return
        if item.result_url:
            import webbrowser; webbrowser.open(item.result_url)
        elif item.error_details:
            self._show_error_dialog(item)
        elif item.status in ("completed", "completed_with_warnings"):
            self._show_status_dialog(item)

    def _show_error_dialog(self, item: BatchItem):
        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title(f"Ошибка: {item.display_name}")
        dlg.geometry("600x400")
        dlg.transient(root)
        dlg.grab_set()

        ttk.Label(dlg, text=f"Файл: {item.display_name}", font=("Segoe UI", 10, "bold")).pack(padx=10, pady=(10, 5), anchor=tk.W)

        info = ttk.LabelFrame(dlg, text="Информация об элементе", padding=5)
        info.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(info, text=f"Тип источника: {item.source_type}").pack(anchor=tk.W)
        ttk.Label(info, text=f"Путь: {item.source_path or '—'}").pack(anchor=tk.W)
        ttk.Label(info, text=f"Шаблон: {self.TEMPLATE_NAMES.get(item.protocol_template, item.protocol_template)}").pack(anchor=tk.W)
        ttk.Label(info, text=f"Режим: {self.MODE_NAMES.get(item.protocol_mode, item.protocol_mode)}").pack(anchor=tk.W)
        ttk.Label(info, text=f"Статус: {item.status}").pack(anchor=tk.W)
        if item.status_message:
            ttk.Label(info, text=f"Сообщение: {item.status_message}").pack(anchor=tk.W)
        if item.actual_seconds:
            ttk.Label(info, text=f"Длительность обработки: {item.actual_seconds:.1f} сек").pack(anchor=tk.W)

        err_frame = ttk.LabelFrame(dlg, text="Детали ошибки", padding=5)
        err_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        err_text = tk.Text(err_frame, wrap=tk.WORD, font=("Consolas", 9))
        err_text.pack(fill=tk.BOTH, expand=True)
        err_text.insert("1.0", item.error_details or "Нет деталей")
        err_text.configure(state=tk.DISABLED)

        ttk.Button(dlg, text="Закрыть", command=dlg.destroy).pack(pady=10)

    def _show_status_dialog(self, item: BatchItem):
        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title(f"Статус: {item.display_name}")
        dlg.geometry("500x380")
        dlg.transient(root)
        dlg.grab_set()
        ttk.Label(dlg, text=f"Файл: {item.display_name}", font=("Segoe UI", 10, "bold")).pack(padx=10, pady=(10, 5))
        ttk.Label(dlg, text=f"Статус: {item.status}").pack(padx=10)
        if item.status_message:
            ttk.Label(dlg, text=f"Сообщение: {item.status_message}", wraplength=450).pack(padx=10, pady=5)
        if item.actual_seconds:
            ttk.Label(dlg, text=f"Длительность: {item.actual_seconds:.1f} сек").pack(padx=10)
        if item.debug_directory:
            ttk.Label(dlg, text=f"Debug: {item.debug_directory}").pack(padx=10, pady=5)
            proto = item.debug_directory / "protocol.json"
            if proto.exists():
                ttk.Label(dlg, text=f"Протокол JSON: {proto}").pack(padx=10)
            html = item.debug_directory / "protocol_preview.html"
            if html.exists():
                ttk.Label(dlg, text=f"HTML preview: {html}").pack(padx=10)
        if item.error_details:
            ttk.Label(dlg, text=f"Ошибка: {item.error_details[:300]}", wraplength=450).pack(padx=10, pady=5)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        if item.result_url:
            def _open_confluence():
                import webbrowser
                webbrowser.open(item.result_url)
            ttk.Button(btn_frame, text="Открыть в Confluence", command=_open_confluence).pack(side=tk.LEFT, padx=3)

        if item.debug_directory:
            html_path = item.debug_directory / "protocol_preview.html"
            if html_path.exists():
                def _open_html():
                    import webbrowser
                    webbrowser.open(str(html_path))
                ttk.Button(btn_frame, text="Открыть локальный HTML", command=_open_html).pack(side=tk.LEFT, padx=3)
            def _open_folder():
                import subprocess
                subprocess.Popen(f'explorer "{item.debug_directory.resolve()}"')
            ttk.Button(btn_frame, text="Открыть папку результата", command=_open_folder).pack(side=tk.LEFT, padx=3)

        ttk.Button(btn_frame, text="Закрыть", command=dlg.destroy).pack(side=tk.RIGHT, padx=3)

    def _log_event(self, stage: str, percent: int, item, severity: str, message: str):
        try:
            batch = self.qc.batch_service.batch_run
            if not batch:
                return
            batch_debug_dir = Path(settings.DEBUG_DIR) / batch.batch_id[:8]
            batch_debug_dir.mkdir(parents=True, exist_ok=True)
            log_path = batch_debug_dir / "processing_events.jsonl"
            import json as json_mod
            entry = {
                "timestamp": datetime.now().isoformat(),
                "stage": stage,
                "percent": percent,
                "severity": severity,
                "message": message,
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json_mod.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _show_nothing_to_process(self, batch):
        result_text = ""
        for item in batch.items:
            if item.status == "completed":
                result_text += f"  ✓ {item.display_name} (завершён)\n"
            elif item.status == "skipped":
                result_text += f"  ⊘ {item.display_name} (пропущен)\n"
            elif item.status == "validation_failed":
                result_text += f"  ✗ {item.display_name} (валидация не пройдена)\n"
            elif item.status == "failed":
                result_text += f"  ✗ {item.display_name} (ошибка)\n"
            else:
                result_text += f"  ? {item.display_name} (статус: {item.status})\n"
        if not result_text:
            result_text = "  (нет элементов)\n"

        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title("Нечего обрабатывать")
        dlg.geometry("450x300")
        dlg.transient(root)
        dlg.grab_set()

        ttk.Label(dlg, text="Все элементы уже обработаны",
                  font=("Segoe UI", 11, "bold")).pack(padx=10, pady=(10, 5))

        text_frame = ttk.Frame(dlg)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 9))
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert("1.0", result_text)
        text_widget.configure(state=tk.DISABLED)

        ttk.Button(dlg, text="Закрыть", command=dlg.destroy).pack(pady=10)

    def _show_internal_error(self, error_msg: str, traceback_text: str):
        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title("Внутренняя ошибка")
        dlg.geometry("650x450")
        dlg.transient(root)
        dlg.grab_set()

        ttk.Label(dlg, text="Произошла внутренняя ошибка при запуске",
                  foreground="red", font=("Segoe UI", 11, "bold")).pack(padx=10, pady=(10, 5))

        text_frame = ttk.Frame(dlg)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        error_text = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 9),
                             yscrollcommand=scrollbar.set)
        error_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.configure(command=error_text.yview)
        error_text.insert(tk.END, f"Ошибка: {error_msg}\n\n")
        error_text.insert(tk.END, traceback_text)
        error_text.configure(state=tk.DISABLED)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        def copy_error():
            dlg.clipboard_clear()
            dlg.clipboard_append(f"Ошибка: {error_msg}\n\n{traceback_text}")

        ttk.Button(btn_frame, text="Копировать", command=copy_error).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Закрыть", command=dlg.destroy).pack(side=tk.RIGHT, padx=3)

        # Save runtime error log
        from pathlib import Path
        log_dir = Path("debug")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "runtime_error.log"
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {error_msg}\n{traceback_text}\n---\n")

    def _start_processing(self):
        if self.qc.processing:
            return
        from services.preflight_service import run_preflight
        from services.runtime_config import get_runtime_config

        batch = self.qc.batch_service.batch_run
        if not batch or not batch.items:
            messagebox.showwarning("Предупреждение", "Очередь пуста")
            return

        try:
            # Reset state
            batch.cancel_requested = False
            batch.stop_after_current = False

            config = get_runtime_config()
            items = [i for i in batch.items if i.status not in ("completed", "skipped")]

            if not items:
                self._show_nothing_to_process(batch)
                return

            # Run preflight — it determines source_type from each BatchItem
            preflight = run_preflight(items, config)

            if preflight["has_blocking"]:
                self._show_preflight_blocking(preflight)
                return

            if preflight["has_warnings"]:
                self._show_preflight_warnings(preflight)
                return

            # No blocking, no warnings — start immediately
            self._log_event("preflight_passed", 0, None, "info", f"Preflight passed, {preflight['items_checked']} items checked")
            self._elapsed_start = self._elapsed_start or datetime.now()
            self._do_start_processing()
        except Exception as e:
            self.start_btn.configure(state=tk.NORMAL)
            self.stop_btn.configure(state=tk.DISABLED)
            import traceback
            tb = traceback.format_exc()
            self._log_event("preflight_internal_error", 0, None, "error", str(e))
            self._show_internal_error(str(e), tb)

    def _show_preflight_warnings(self, preflight):
        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title("Предстартовая проверка — предупреждения")
        dlg.geometry("500x350")
        dlg.transient(root)
        dlg.grab_set()

        ttk.Label(dlg, text="Обнаружены предупреждения", foreground="#cc6600",
                  font=("Segoe UI", 11, "bold")).pack(padx=10, pady=(10, 5))

        text_frame = ttk.Frame(dlg)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        result_text = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 9), height=10)
        result_text.pack(fill=tk.BOTH, expand=True)
        for line in preflight["warnings"]:
            result_text.insert(tk.END, f"  ! {line}\n")
        result_text.configure(state=tk.DISABLED)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        def cont():
            dlg.destroy()
            self._log_event("preflight_warnings_accepted", 0, None, "warning", f"{len(preflight['warnings'])} warnings accepted")
            self._do_start_processing()

        ttk.Button(btn_frame, text="Продолжить обработку", command=cont).pack(side=tk.RIGHT, padx=3)
        ttk.Button(btn_frame, text="Отмена", command=dlg.destroy).pack(side=tk.RIGHT, padx=3)

    def _show_preflight_blocking(self, preflight):
        root = self.winfo_toplevel()
        dlg = tk.Toplevel(root)
        dlg.title("Предстартовая проверка — ошибки")
        dlg.geometry("550x400")
        dlg.transient(root)
        dlg.grab_set()

        ttk.Label(dlg, text="Обнаружены критические ошибки!", foreground="red",
                  font=("Segoe UI", 11, "bold")).pack(padx=10, pady=(10, 5))

        text_frame = ttk.Frame(dlg)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        result_text = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 9))
        result_text.pack(fill=tk.BOTH, expand=True)
        for line in preflight["errors"]:
            result_text.insert(tk.END, f"  X {line}\n")
        result_text.configure(state=tk.DISABLED)

        ttk.Button(dlg, text="Закрыть", command=dlg.destroy).pack(pady=10)

    def _do_start_processing(self):
        if self.qc.processing:
            return

        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.progress_label["text"] = "Запуск обработки..."
        self.stage_label["text"] = ""
        self._elapsed_start = datetime.now()
        self.overall_progress["value"] = 0
        self.current_progress["value"] = 0
        self._current_stage.clear()
        self._last_progress.clear()
        self.qc.start_processing(progress_callback=None)
        self.after(500, self._check_first_progress)

    def _check_first_progress(self):
        if not self.qc.processing:
            return
        if self._current_stage or self._last_progress:
            return
        self.stage_label["text"] = "Ожидание первого этапа..."
        self.after(500, self._check_first_progress)

    def _update_banner(self):
        from services.runtime_config import get_runtime_config
        config = get_runtime_config()
        # Determine source type from first pending item, or default
        source_type = "local_transcript"
        batch = self.qc.batch_service.batch_run
        if batch and batch.items:
            non_completed = [i for i in batch.items if i.status not in ("completed", "skipped")]
            if non_completed:
                source_type = non_completed[0].source_type or "local_transcript"

        banner = config.get_banner_text(source_type)
        self.banner_label.configure(text=banner)

        # Color-code the banner
        if config.is_demo_for_source(source_type):
            self.banner_label.configure(foreground="#cc6600")  # orange
        elif config.is_production_blocked(source_type):
            self.banner_label.configure(foreground="red")
        else:
            self.banner_label.configure(foreground="green")

    def _stop_processing(self):
        if self.qc.batch_service.batch_run:
            self.qc.batch_service.batch_run.cancel_requested = True
        self.stop_btn.configure(state=tk.DISABLED)
        self.start_btn.configure(state=tk.NORMAL)

    def _start_progress_checker(self):
        try:
            while True:
                stage, percent, item = self.qc.progress_queue.get_nowait()
                if stage == "batch_done":
                    self._on_batch_done()
                else:
                    self._update_progress(stage, percent, item)
        except queue.Empty:
            pass
        self._update_eta()
        self.after(200, self._start_progress_checker)

    def _update_progress(self, stage, percent, item):
        if item:
            self._current_stage[item.item_id] = stage
            self._last_progress[item.item_id] = percent

        stage_text = self.STAGE_NAMES.get(stage, stage)

        if item and self.qc.batch_service.batch_run:
            batch = self.qc.batch_service.batch_run
            idx = batch.current_index + 1
            total = len(batch.items)
            overall_pct = ((idx - 1) / total * 100) + (percent / total) if total > 0 else 0
            self.overall_progress["value"] = overall_pct
            self.current_progress["value"] = percent
            self.progress_label["text"] = f"Обрабатывается протокол {idx} из {total}"
            self.stage_label["text"] = (
                f"Файл: {item.display_name}\n"
                f"Шаблон: {self.TEMPLATE_NAMES.get(item.protocol_template, item.protocol_template)}\n"
                f"Этап: {stage_text}"
            )
        else:
            self.current_progress["value"] = percent
            if stage:
                self.progress_label["text"] = stage_text

        self._update_eta()
        self._refresh_table()

    def _update_eta(self):
        if hasattr(self, '_elapsed_start') and self._elapsed_start:
            elapsed = (datetime.now() - self._elapsed_start).total_seconds()
            elapsed_str = str(datetime.utcfromtimestamp(int(elapsed)).strftime("%H:%M:%S"))
        else:
            elapsed_str = "00:00:00"

        items = self.qc.get_items()
        pending = [i for i in items if i.status not in ("completed", "failed", "cancelled", "skipped", "validation_failed")]
        estimate, eta_text = self.estimator.estimate_batch_remaining(pending)

        self.time_label["text"] = f"Прошло: {elapsed_str} | {eta_text}"

    def _on_batch_done(self):
        self.overall_progress["value"] = 100
        self.current_progress["value"] = 100
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self._refresh_table()
        self._save_state()

        batch = self.qc.batch_service.batch_run
        if batch:
            completed = sum(1 for i in batch.items if i.status == "completed")
            failed = sum(1 for i in batch.items if i.status == "failed")
            cancelled = sum(1 for i in batch.items if i.status == "cancelled")
            validation_failed = sum(1 for i in batch.items if i.status == "validation_failed")
            skipped = sum(1 for i in batch.items if i.status == "skipped")
            pending = sum(1 for i in batch.items if i.status == "pending")
            total = len(batch.items)

            status_names = {
                "completed": "Завершена успешно",
                "completed_with_errors": "Завершена с ошибками",
                "failed": "Завершена с ошибкой",
                "cancelled": "Отменена",
                "nothing_to_process": "Нечего обрабатывать",
            }
            status_text = status_names.get(batch.status, batch.status)

            summary = (
                f"Обработка очереди: {status_text}\n\n"
                f"Всего элементов: {total}\n"
                f"Успешно: {completed}\n"
                f"С ошибками: {failed}\n"
                f"Валидация не пройдена: {validation_failed}\n"
                f"Пропущено: {skipped}\n"
                f"Отменено: {cancelled}\n"
                f"Ожидает: {pending}"
            )
            self.progress_label["text"] = f"Обработка завершена — {status_text}"
            self.stage_label["text"] = ""
            messagebox.showinfo("Результат обработки", summary)

    def _save_state(self):
        self.qc.save_state()

    def _go_back(self):
        if self.qc.processing:
            messagebox.showwarning("Предупреждение", "Дождитесь завершения обработки")
            return
        self.main_window.show_main_menu()

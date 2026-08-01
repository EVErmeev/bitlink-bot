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
        thread = threading.Thread(target=self._process_batch, args=(progress_callback,), daemon=True)
        thread.start()

    def _process_batch(self, progress_callback):
        service = ProcessingService(progress_callback=self._on_progress)
        batch = self.batch_service.batch_run
        batch.status = "processing"
        batch.started_at = datetime.now().isoformat()

        for i, item in enumerate(batch.items):
            if batch.cancel_requested:
                item.status = "cancelled"
                continue
            if item.status in ("completed", "skipped"):
                continue

            batch.current_index = i
            result = service.process_item(item)

            if not result["success"] and not settings.BATCH_CONTINUE_AFTER_ERROR:
                batch.status = "failed"
                break

        batch.completed_at = datetime.now().isoformat()
        batch.status = "completed" if not batch.cancel_requested else "cancelled"
        self.processing = False
        self.progress_queue.put(("batch_done", 100, None))

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

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.qc = get_queue_controller()
        self.estimator = RuntimeEstimator()
        self._build()
        self._refresh_table()
        self._start_progress_checker()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top, text="Очередь обработки", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="Назад", command=self._go_back).pack(side=tk.RIGHT)

        tree_frame = ttk.LabelFrame(self, text="Источники в очереди", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("№", "Имя", "Путь", "Размер", "Длит/слов", "Шаблон", "Режим", "Confluence", "Статус", "Результат")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")

        widths = {
            "№": 40, "Имя": 200, "Путь": 200, "Размер": 80, "Длит/слов": 80,
            "Шаблон": 150, "Режим": 70, "Confluence": 120, "Статус": 100, "Результат": 100
        }
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=widths.get(col, 100))
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(tree_frame, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Delete>", self._remove_selected)

        btn1 = ttk.Frame(self)
        btn1.pack(fill=tk.X, padx=10, pady=2)
        ttk.Button(btn1, text="Добавить файлы", command=self._add_files).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="Удалить выбранные", command=self._remove_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="Очистить список", command=self._clear_all).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="▲ Вверх", command=self._move_up).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="▼ Вниз", command=self._move_down).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn1, text="Изменить параметры", command=self._edit_params).pack(side=tk.LEFT, padx=3)

        btn2 = ttk.Frame(self)
        btn2.pack(fill=tk.X, padx=10, pady=2)
        self.start_btn = ttk.Button(btn2, text="▶ Запустить обработку", command=self._start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=3)
        self.stop_btn = ttk.Button(btn2, text="■ Стоп", command=self._stop_processing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=3)

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

            status_text = item.status
            if item.status_message:
                status_text = item.status_message

            self.tree.insert("", tk.END, iid=item.item_id, values=(
                i, item.display_name, str(item.source_path or ""), size_str, dur_str,
                template_name, mode_name,
                item.parent_page_title or "По умолчанию",
                status_text, item.result_url or ""
            ))

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Все поддерживаемые", "*.txt *.md *.mp4 *.webm *.m4v"), ("Все файлы", "*.*")],
            title="Выберите файлы для добавления в очередь"
        )
        if not paths:
            return

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
                protocol_template="project_detailed",
                protocol_mode="auto",
            )
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

    def _start_processing(self):
        if self.qc.processing:
            return
        if not self.qc.get_items():
            messagebox.showwarning("Предупреждение", "Очередь пуста")
            return

        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self._elapsed_start = datetime.now()
        self.qc.start_processing(progress_callback=None)

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
        self.after(200, self._start_progress_checker)

    def _update_progress(self, stage, percent, item):
        stage_names = {
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
        }
        stage_text = stage_names.get(stage, stage)

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

        self._update_eta()
        self._refresh_table()

    def _update_eta(self):
        if hasattr(self, '_elapsed_start'):
            elapsed = (datetime.now() - self._elapsed_start).total_seconds()
            elapsed_str = str(datetime.utcfromtimestamp(int(elapsed)).strftime("%H:%M:%S"))
        else:
            elapsed_str = "00:00:00"

        items = self.qc.get_items()
        pending = [i for i in items if i.status not in ("completed", "failed", "cancelled", "skipped")]
        estimate, eta_text = self.estimator.estimate_batch_remaining(pending)

        self.time_label["text"] = f"Прошло: {elapsed_str} | {eta_text}"

    def _on_batch_done(self):
        self.overall_progress["value"] = 100
        self.current_progress["value"] = 100
        self.progress_label["text"] = "Обработка завершена"
        self.stage_label["text"] = ""
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self._refresh_table()
        self._save_state()

    def _save_state(self):
        self.qc.save_state()

    def _go_back(self):
        if self.qc.processing:
            messagebox.showwarning("Предупреждение", "Дождитесь завершения обработки")
            return
        self.main_window.show_main_menu()

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from models.batch import BatchItem


class LocalVideoFrame(ttk.Frame):
    VIDEO_EXTENSIONS = [("Видео", "*.mp4 *.webm *.m4v"), ("Все файлы", "*.*")]

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.files = []
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top, text="Локальное видео", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="Назад", command=lambda: self.main_window.show_main_menu()).pack(side=tk.RIGHT)

        tree_frame = ttk.LabelFrame(self, text="Выбранные файлы", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("Имя", "Путь", "Размер")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="extended")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(tree_frame, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<Delete>", self._remove_selected)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Добавить файлы", command=self._add_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить выбранные", command=self._remove_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Добавить в очередь", command=self._add_to_queue).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Перейти к очереди", command=self._show_queue).pack(side=tk.LEFT, padx=5)

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            filetypes=self.VIDEO_EXTENSIONS,
            title="Выберите видеофайлы"
        )
        for p in paths:
            fpath = Path(p)
            if fpath in self.files:
                continue
            self.files.append(fpath)
            size_mb = fpath.stat().st_size / (1024 * 1024)
            self.tree.insert("", tk.END, values=(fpath.name, str(fpath), f"{size_mb:.1f} МБ"))

    def _remove_selected(self, event=None):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Предупреждение", "Выберите файлы для удаления")
            return
        for item in sel:
            values = self.tree.item(item, "values")
            self.files = [f for f in self.files if str(f) != values[1]]
            self.tree.delete(item)

    def _add_to_queue(self):
        if not self.files:
            messagebox.showwarning("Предупреждение", "Добавьте файлы")
            return

        from ui.source_queue_frame import get_queue_controller

        items = []
        for fpath in self.files:
            size_bytes = fpath.stat().st_size
            item = BatchItem(
                source_type="local_video",
                source_path=fpath,
                display_name=fpath.name,
                file_size_bytes=size_bytes,
                protocol_template="project_detailed",
                protocol_mode="auto",
            )
            items.append(item)

        qc = get_queue_controller()
        qc.add_items(items)
        messagebox.showinfo("Добавлено", f"Добавлено файлов: {len(items)}")
        self.files.clear()
        self.tree.delete(*self.tree.get_children())

    def _show_queue(self):
        from ui.source_queue_frame import SourceQueueFrame
        self.main_window.show_frame(SourceQueueFrame)
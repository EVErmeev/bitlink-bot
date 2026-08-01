import tkinter as tk
from tkinter import ttk, messagebox


class ResultFrame(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._build()

    def _build(self):
        ttk.Label(self, text="Результаты обработки", font=("Segoe UI", 14, "bold")).pack(pady=10)

        columns = ("№", "Файл", "Статус", "URL")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="В главное меню", command=lambda: self.main_window.show_main_menu()).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="Повторить публикацию", command=self._republish).pack(side=tk.LEFT, padx=5)

    def set_results(self, items):
        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(items, 1):
            self.tree.insert("", tk.END, values=(i, item.display_name, item.status, item.result_url or ""))

    def _republish(self):
        messagebox.showinfo("Информация", "Повторная публикация будет выполнена без повторной генерации")
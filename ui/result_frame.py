import tkinter as tk
from tkinter import messagebox, ttk

from services.processing_service import ProcessingService


class ResultFrame(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.items = []
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
        self.items = items
        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(items, 1):
            self.tree.insert("", tk.END, iid=item.item_id, values=(i, item.display_name, item.status, item.result_url or ""))

    def _republish(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Предупреждение", "Выберите строку для повторной публикации")
            return

        item_id = sel[0]
        item = next((i for i in self.items if i.item_id == item_id), None)
        if not item:
            messagebox.showerror("Ошибка", "Элемент не найден")
            return

        if item.status not in ("completed", "validation_failed", "failed"):
            messagebox.showwarning("Ошибка", "Можно повторно опубликовать только завершённые элементы")
            return

        service = ProcessingService()
        result = service.republish(item)
        if result["success"]:
            messagebox.showinfo("Успех", f"Повторная публикация выполнена.\nURL: {result.get('url', 'dry-run')}")
            self.set_results(self.items)
        else:
            messagebox.showerror("Ошибка", f"Повторная публикация не удалась: {result.get('error')}")

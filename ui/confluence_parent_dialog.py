import tkinter as tk
from tkinter import ttk, messagebox
from services.confluence_service import ConfluenceClient


class ConfluenceParentDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Выбор родительской страницы Confluence")
        self.geometry("500x400")
        self.client = ConfluenceClient()
        self.result = None
        self._build()

    def _build(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, pady=5)
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Найти", command=self._search).pack(side=tk.LEFT)

        columns = ("Название", "ID")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("Название", text="Название")
        self.tree.heading("ID", text="ID")
        self.tree.column("Название", width=300)
        self.tree.column("ID", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=5)

        manual_frame = ttk.Frame(frame)
        manual_frame.pack(fill=tk.X, pady=5)
        ttk.Label(manual_frame, text="ID страницы:").pack(side=tk.LEFT)
        self.page_id_var = tk.StringVar()
        ttk.Entry(manual_frame, textvariable=self.page_id_var, width=30).pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Выбрать", command=self._select).pack(side=tk.RIGHT, padx=3)
        ttk.Button(btn_frame, text="Создать в корне", command=self._create_root).pack(side=tk.RIGHT, padx=3)
        ttk.Button(btn_frame, text="Отмена", command=self.destroy).pack(side=tk.RIGHT, padx=3)

    def _search(self):
        query = self.search_var.get()
        if not query:
            return
        results = self.client.find_page_by_title(query)
        self.tree.delete(*self.tree.get_children())
        for r in results:
            self.tree.insert("", tk.END, values=(r["title"], r["id"]))

    def _select(self):
        page_id = self.page_id_var.get()
        title = ""
        sel = self.tree.selection()
        if sel:
            vals = self.tree.item(sel[0], "values")
            page_id = vals[1]
            title = vals[0]
        if not page_id:
            messagebox.showwarning("Предупреждение", "Укажите ID страницы или выберите из списка")
            return
        self.result = {"id": page_id, "title": title}
        self.destroy()

    def _create_root(self):
        self.result = {"id": None, "title": "(Корень пространства)"}
        self.destroy()
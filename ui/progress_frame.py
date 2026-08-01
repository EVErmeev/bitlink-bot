import tkinter as tk
from tkinter import ttk


class ProgressFrame(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._build()

    def _build(self):
        ttk.Label(self, text="Обработка...", font=("Segoe UI", 14, "bold")).pack(pady=20)

        self.status_label = ttk.Label(self, text="Подготовка...", font=("Segoe UI", 10))
        self.status_label.pack()

        self.overall = ttk.Progressbar(self, mode="determinate", length=500)
        self.overall.pack(pady=10, fill=tk.X, padx=20)
        self.overall["value"] = 0

        self.current = ttk.Progressbar(self, mode="determinate", length=300)
        self.current.pack(pady=5, fill=tk.X, padx=20)
        self.current["value"] = 0

        self.time_label = ttk.Label(self, text="")
        self.time_label.pack(pady=5)

    def update_progress(self, overall_pct, current_pct, status_text, time_text=""):
        self.overall["value"] = overall_pct
        self.current["value"] = current_pct
        self.status_label["text"] = status_text
        if time_text:
            self.time_label["text"] = time_text

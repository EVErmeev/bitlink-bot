import tkinter as tk
from tkinter import ttk, messagebox
from services.bitlink_service import BitlinkClient
from models.batch import BatchItem


class BitlinkFrame(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.client = BitlinkClient()
        self.rooms = []
        self.recordings = []
        self._build()
        self._load_rooms()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top, text="БИТ.Link — записи встреч", font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="Назад", command=lambda: self.main_window.show_main_menu()).pack(side=tk.RIGHT)

        room_frame = ttk.LabelFrame(self, text="Комнаты", padding=5)
        room_frame.pack(fill=tk.X, padx=10, pady=5)

        self.room_listbox = tk.Listbox(room_frame, height=6, exportselection=False)
        self.room_listbox.pack(fill=tk.X)
        self.room_listbox.bind("<<ListboxSelect>>", self._on_room_select)

        rec_frame = ttk.LabelFrame(self, text="Записи", padding=5)
        rec_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("Название", "Дата", "Длительность", "Статус")
        self.rec_tree = ttk.Treeview(rec_frame, columns=columns, show="headings", selectmode="extended")
        for col in columns:
            self.rec_tree.heading(col, text=col)
            self.rec_tree.column(col, width=150)
        self.rec_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(rec_frame, orient=tk.VERTICAL, command=self.rec_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.rec_tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Button(btn_frame, text="Добавить в очередь", command=self._add_to_queue).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Перейти к очереди", command=self._show_queue).pack(side=tk.LEFT, padx=5)

    def _load_rooms(self):
        self.rooms = self.client.get_rooms()
        self.room_listbox.delete(0, tk.END)
        for room in self.rooms:
            self.room_listbox.insert(tk.END, f"{room['name']} ({room['recording_count']} записей)")

    def _on_room_select(self, event):
        sel = self.room_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        room = self.rooms[idx]
        self._load_recordings(room["id"])

    def _load_recordings(self, room_id):
        self.recordings = self.client.get_recordings(room_id)
        self.rec_tree.delete(*self.rec_tree.get_children())
        for rec in self.recordings:
            duration_min = rec.get("duration_seconds", 0) // 60
            self.rec_tree.insert("", tk.END, values=(
                rec["name"], rec.get("date", ""), f"{duration_min} мин", rec.get("status", "")
            ))

    def _add_to_queue(self):
        sel = self.rec_tree.selection()
        if not sel:
            messagebox.showwarning("Предупреждение", "Выберите записи для добавления в очередь")
            return

        from ui.source_queue_frame import get_queue_controller

        items = []
        for idx in sel:
            rec_idx = self.rec_tree.index(idx)
            rec = self.recordings[rec_idx]
            item = BatchItem(
                source_type="bitlink",
                bitlink_recording_id=rec["id"],
                display_name=rec["name"],
                duration_seconds=rec.get("duration_seconds"),
                protocol_template="project_detailed",
                protocol_mode="auto",
            )
            items.append(item)

        qc = get_queue_controller()
        qc.add_items(items)
        messagebox.showinfo("Добавлено", f"Добавлено записей: {len(items)}. Всего в очереди: {len(qc.get_items())}")

    def _show_queue(self):
        from ui.source_queue_frame import SourceQueueFrame
        self.main_window.show_frame(SourceQueueFrame)
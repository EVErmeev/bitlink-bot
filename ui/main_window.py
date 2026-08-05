import tkinter as tk
from tkinter import ttk


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Генератор протоколов встреч")
        self.root.geometry("1024x768")
        self.root.minsize(800, 600)

        self.current_frame = None
        self.container = ttk.Frame(root)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.show_main_menu()

    def show_frame(self, frame_class):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame_class(self.container, self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_main_menu(self):
        from ui.main_menu_frame import MainMenuFrame
        self.show_frame(MainMenuFrame)

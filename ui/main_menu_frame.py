import tkinter as tk
from tkinter import ttk


class MainMenuFrame(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self._build()

    def _build(self):
        title = ttk.Label(self, text="Генератор протоколов встреч", font=("Segoe UI", 18, "bold"))
        title.pack(pady=(40, 10))

        subtitle = ttk.Label(
            self, text="Выберите источник для создания протокола встречи",
            font=("Segoe UI", 10)
        )
        subtitle.pack(pady=(0, 30))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(expand=True)

        btn_style = {"width": 30, "padding": 15}

        ttk.Button(btn_frame, text="БИТ.Link", command=self._open_bitlink, **btn_style).pack(pady=6)
        ttk.Button(btn_frame, text="Локальное видео", command=self._open_local_video, **btn_style).pack(pady=6)
        ttk.Button(btn_frame, text="Локальная расшифровка", command=self._open_transcript, **btn_style).pack(pady=6)
        ttk.Button(btn_frame, text="Настройки", command=self._open_settings, **btn_style).pack(pady=6)

        ttk.Separator(btn_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        ttk.Button(btn_frame, text="Выход", command=self._exit_app, **btn_style).pack(pady=6)

    def _open_bitlink(self):
        from ui.bitlink_frame import BitlinkFrame
        self.main_window.show_frame(BitlinkFrame)

    def _open_local_video(self):
        from ui.local_video_frame import LocalVideoFrame
        self.main_window.show_frame(LocalVideoFrame)

    def _open_transcript(self):
        from ui.local_transcript_frame import LocalTranscriptFrame
        self.main_window.show_frame(LocalTranscriptFrame)

    def _open_settings(self):
        from ui.settings_frame import SettingsFrame
        self.main_window.show_frame(SettingsFrame)

    def _exit_app(self):
        self.main_window.root.quit()
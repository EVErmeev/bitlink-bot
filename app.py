import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    from ui.main_window import MainWindow
    from settings import DATA_DIR
    from services.batch_service import BatchService

    root = tk.Tk()
    root.withdraw()

    state_path = DATA_DIR / "batch_state.json"
    if state_path.exists():
        svc = BatchService()
        batch = svc.load_state(state_path)
        if batch and batch.items:
            pending = [i for i in batch.items if i.status not in ("completed", "skipped")]
            if pending:
                answer = messagebox.askyesno(
                    "Восстановление очереди",
                    f"Обнаружена незавершённая очередь из {len(batch.items)} элементов.\n"
                    f"Не завершено: {len(pending)}.\n\n"
                    f"Продолжить обработку?"
                )
                if answer:
                    from ui.source_queue_frame import get_queue_controller
                    qc = get_queue_controller()
                    qc.batch_service.batch_run = batch
                    root.deiconify()
                    app = MainWindow(root)
                    root.mainloop()
                    return

    root.deiconify()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
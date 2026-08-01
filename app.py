import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    from services.batch_service import BatchService
    from settings import DATA_DIR
    from ui.main_window import MainWindow

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
                    _ = MainWindow(root)
                    root.mainloop()
                    return

    root.deiconify()
    _ = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

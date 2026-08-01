import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))


def startup_check():
    from protocol_templates.registry import TemplateRegistry
    registry = TemplateRegistry()
    templates = registry.list_templates()
    if len(templates) != 4:
        print(f"STARTUP_CHECK_FAIL: expected 4 templates, got {len(templates)}")
        sys.exit(1)
    for t in templates:
        tmpl = registry.get(t["id"])
        if not tmpl:
            print(f"STARTUP_CHECK_FAIL: template {t['id']} not loaded")
            sys.exit(1)
        schema = tmpl.get_schema()
        if not schema or not isinstance(schema, dict):
            print(f"STARTUP_CHECK_FAIL: template {t['id']} has invalid schema")
            sys.exit(1)
    from services.confluence_service import ConfluenceClient
    client = ConfluenceClient()
    if not client.check_connection():
        print("STARTUP_CHECK_FAIL: Confluence connection failed")
        sys.exit(1)
    print("STARTUP_CHECK_OK")
    sys.exit(0)


def main():
    if "--startup-check" in sys.argv:
        startup_check()

    from services.batch_service import BatchService
    from settings import DATA_DIR
    from ui.main_window import MainWindow

    root = tk.Tk()
    from ui.clipboard_support import install_clipboard_support
    install_clipboard_support(root)
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

"""Cross-platform clipboard support for tkinter widgets.
Windows keyboard codes are used for reliable detection in any keyboard layout."""
import tkinter as tk
from tkinter import Menu

_WIN_KEYCODES = {
    65: "select_all",   # A
    67: "copy",         # C
    86: "paste",        # V
    88: "cut",          # X
    45: "copy",         # Insert
    46: "cut",          # Delete (Shift+Delete)
}


def install_clipboard_support(root: tk.Tk) -> None:
    """Install clipboard hotkeys globally. Call once after creating root."""
    _bind_all_widgets(root)
    root.bind_class("Entry", "<Button-3><ButtonRelease-3>", _show_context_menu, add="+")
    root.bind_class("TEntry", "<Button-3><ButtonRelease-3>", _show_context_menu, add="+")
    root.bind_class("Text", "<Button-3><ButtonRelease-3>", _show_context_menu, add="+")
    root.bind_class("TCombobox", "<Button-3><ButtonRelease-3>", _show_text_menu, add="+")


def _bind_all_widgets(root: tk.Tk) -> None:
    for widget_class in ("Entry", "TEntry", "Text", "TCombobox"):
        root.bind_class(widget_class, "<Control-Key>", _on_ctrl_key, add="+")
        root.bind_class(widget_class, "<Control-Shift-Key>", _on_ctrl_key, add="+")
        root.bind_class(widget_class, "<Shift-Insert>", _on_shift_insert, add="+")
        root.bind_class(widget_class, "<Shift-Delete>", _on_shift_delete, add="+")
        root.bind_class(widget_class, "<Control-Insert>", _on_ctrl_insert, add="+")


def _on_ctrl_key(event) -> str:
    widget = event.widget
    keycode = event.keycode

    # Windows keycode detection (works in any keyboard layout)
    if keycode == 65:  # A — Select All
        _select_all(widget)
        return "break"
    elif keycode == 67:  # C — Copy
        _copy(widget)
        return "break"
    elif keycode == 86:  # V — Paste
        if not _is_readonly(widget):
            _paste(widget)
        return "break"
    elif keycode == 88:  # X — Cut
        if not _is_readonly(widget):
            _cut(widget)
        return "break"

    # Fallback via keysym
    key = event.keysym.lower() if event.keysym else ""
    if key == "a":
        _select_all(widget)
        return "break"
    elif key == "c":
        _copy(widget)
        return "break"
    elif key == "v":
        if not _is_readonly(widget):
            _paste(widget)
        return "break"
    elif key == "x":
        if not _is_readonly(widget):
            _cut(widget)
        return "break"

    return ""


def _on_shift_insert(event) -> str:
    if not _is_readonly(event.widget):
        _paste(event.widget)
    return "break"


def _on_shift_delete(event) -> str:
    if not _is_readonly(event.widget):
        _cut(event.widget)
    return "break"


def _on_ctrl_insert(event) -> str:
    _copy(event.widget)
    return "break"


def _is_readonly(widget) -> bool:
    state = str(widget.cget("state")) if hasattr(widget, "cget") else ""
    return "readonly" in state or "disabled" in state


def _select_all(widget) -> None:
    try:
        if isinstance(widget, tk.Text):
            widget.tag_add("sel", "1.0", "end-1c")
        else:
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
    except Exception:
        pass


def _copy(widget) -> None:
    try:
        if isinstance(widget, tk.Text):
            if widget.tag_ranges("sel"):
                text = widget.get("sel.first", "sel.last")
                widget.clipboard_clear()
                widget.clipboard_append(text)
        else:
            if widget.selection_present():
                text = widget.selection_get()
                widget.clipboard_clear()
                widget.clipboard_append(text)
    except Exception:
        pass


def _paste(widget) -> None:
    try:
        text = widget.clipboard_get()
        if isinstance(widget, tk.Text):
            if widget.tag_ranges("sel"):
                widget.delete("sel.first", "sel.last")
            widget.insert("insert", text)
        else:
            if widget.selection_present():
                widget.delete("sel.first", "sel.last")
            widget.insert("insert", text)
    except Exception:
        pass


def _cut(widget) -> None:
    try:
        if isinstance(widget, tk.Text):
            if widget.tag_ranges("sel"):
                text = widget.get("sel.first", "sel.last")
                widget.clipboard_clear()
                widget.clipboard_append(text)
                widget.delete("sel.first", "sel.last")
        else:
            if widget.selection_present():
                text = widget.selection_get()
                widget.clipboard_clear()
                widget.clipboard_append(text)
                widget.delete("sel.first", "sel.last")
    except Exception:
        pass


def _show_context_menu(event) -> str:
    widget = event.widget
    menu = Menu(widget, tearoff=0)
    ro = _is_readonly(widget)
    try:
        if isinstance(widget, tk.Text):
            _ = bool(widget.tag_ranges("sel"))
        else:
            _ = widget.selection_present()
    except Exception:
        pass

    menu.add_command(label="Вырезать", command=lambda: _cut(widget))
    menu.add_command(label="Копировать", command=lambda: _copy(widget))
    menu.add_command(label="Вставить", command=lambda: _paste(widget))
    menu.add_separator()
    menu.add_command(label="Выделить всё", command=lambda: _select_all(widget))

    if ro:
        menu.entryconfigure("Вырезать", state="disabled")
        menu.entryconfigure("Вставить", state="disabled")

    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()

    return "break"


def _show_text_menu(event) -> str:
    return _show_context_menu(event)


def _show_combobox_menu(event) -> str:
    return _show_context_menu(event)

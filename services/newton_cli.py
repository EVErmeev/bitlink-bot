"""Unified Newton CLI command builder for Windows."""
import os


def build_newton_command(cli_path: str, *args: str) -> list[str]:
    """Build command list for Newton CLI. Wraps .cmd/.bat in cmd.exe."""
    ext = os.path.splitext(cli_path)[1].lower()
    if ext in (".cmd", ".bat"):
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", cli_path] + list(args)
    return [cli_path] + list(args)

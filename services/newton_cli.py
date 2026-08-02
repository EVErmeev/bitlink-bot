"""Unified Newton CLI command builder for Windows."""


def build_newton_command(cli_path: str, *args: str) -> list[str]:
    """Build command list for Newton CLI. Windows .cmd/.bat runs directly."""
    return [cli_path] + list(args)

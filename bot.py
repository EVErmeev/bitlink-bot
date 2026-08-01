import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    if len(sys.argv) > 1:
        # CLI mode
        from cli import main as cli_main
        cli_main()
    else:
        # GUI mode
        from app import main as app_main
        app_main()


if __name__ == "__main__":
    main()

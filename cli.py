import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import settings
from models.batch import BatchItem
from services.processing_service import ProcessingService


def main():
    parser = argparse.ArgumentParser(description="bitlink-bot — генератор протоколов встреч")
    parser.add_argument("--text", type=str, help="Путь к файлу расшифровки (.txt/.md)")
    parser.add_argument("--local", type=str, help="Путь к локальному видео (.mp4/.webm/.m4v)")
    parser.add_argument("--watch", action="store_true", help="Режим наблюдения за директорией")
    parser.add_argument("--setup", action="store_true", help="Интерактивная настройка")
    parser.add_argument("--protocol-template", type=str, default=settings.PROTOCOL_TEMPLATE,
                        choices=["management_summary", "project_standard", "project_detailed", "business_process_discovery"])
    parser.add_argument("--protocol-mode", type=str, default=settings.PROTOCOL_MODE,
                        choices=["auto", "brief", "detailed"])
    parser.add_argument("--parent-page-id", type=str, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Генерация без публикации")
    parser.add_argument("--no-telegram", action="store_true", help="Пропустить Telegram-уведомление")
    parser.add_argument("--resume", action="store_true", help="Восстановить очередь из batch_state.json")

    args = parser.parse_args()

    if args.setup:
        run_setup()
        return

    if args.watch:
        run_watch()
        return

    if args.text:
        process_file(args.text, "local_transcript", args)
    elif args.local:
        process_file(args.local, "local_video", args)
    elif args.resume:
        resume_queue(args)
    else:
        parser.print_help()
        print("\nУкажите --text или --local для обработки файла")


def process_file(filepath: str, source_type: str, args):
    fpath = Path(filepath)
    if not fpath.exists():
        print(f"Ошибка: файл не найден: {filepath}")
        sys.exit(1)

    size_bytes = fpath.stat().st_size
    item = BatchItem(
        source_type=source_type,
        source_path=fpath,
        display_name=fpath.name,
        file_size_bytes=size_bytes,
        protocol_template=args.protocol_template,
        protocol_mode=args.protocol_mode,
        parent_page_id=args.parent_page_id,
        send_telegram=not args.no_telegram,
        dry_run=args.dry_run,
    )

    if source_type == "local_transcript":
        try:
            text = fpath.read_text(encoding="utf-8-sig")
            from meeting_metadata import count_words
            item.word_count = count_words(text)
        except Exception as e:
            print(f"Предупреждение: не удалось прочитать файл: {e}")

    print(f"\nОбработка: {fpath.name}")
    print(f"Тип: {source_type}")
    print(f"Шаблон: {args.protocol_template}")
    print(f"Режим: {args.protocol_mode}")
    if args.dry_run:
        print("Режим: dry-run (без публикации)")

    if args.dry_run:
        # Override publishing for dry run
        pass

    service = ProcessingService(progress_callback=lambda stage, pct, it: print(f"  [{pct:.0f}%] {stage}"))
    result = service.process_item(item)

    if result["success"]:
        print("\nГотово! Протокол создан.")
        if result.get("url"):
            print(f"URL: {result['url']}")
    else:
        print(f"\nОшибка: {result.get('error', 'Неизвестная ошибка')}")
        sys.exit(1)


def run_setup():
    print("=== Мастер настройки bitlink-bot ===\n")

    env_path = Path(__file__).resolve().parent / ".env"

    print("Настройка подключений (оставьте пустым для mock-режима):")

    bitlink_base = input("БИТ.Link Base URL: ").strip()
    bitlink_email = input("БИТ.Link Email: ").strip()
    bitlink_password = input("БИТ.Link Password: ").strip()

    newton_base = input("\nNewton Base URL: ").strip()
    newton_token = input("Newton Token: ").strip()

    confluence_base = input("\nConfluence Base URL: ").strip()
    confluence_token = input("Confluence Token: ").strip()
    confluence_space = input("Confluence Space Key: ").strip()

    tg_token = input("\nTelegram Bot Token (опционально): ").strip()
    tg_chat = input("Telegram Chat ID (опционально): ").strip()

    if env_path.exists():
        with open(env_path, encoding="utf-8") as f:
            _ = f.readlines()

    env_vars = {
        "BITLINK_BASE_URL": bitlink_base,
        "BITLINK_EMAIL": bitlink_email,
        "BITLINK_PASSWORD": bitlink_password,
        "NEWTON_BASE_URL": newton_base,
        "NEWTON_TOKEN": newton_token,
        "CONFLUENCE_BASE_URL": confluence_base,
        "CONFLUENCE_TOKEN": confluence_token,
        "CONFLUENCE_SPACE_KEY": confluence_space,
        "TG_BOT_TOKEN": tg_token,
        "TG_CHAT_ID": tg_chat,
        "TELEGRAM_ENABLED": "true" if tg_token else "false",
    }

    with open(env_path, "w", encoding="utf-8") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(f"\nНастройки сохранены в {env_path}")
    print("Приложение готово к использованию.")


def run_watch():
    print("Режим наблюдения за директорией...")
    print("Нажмите Ctrl+C для выхода")
    # Simple watch implementation
    import time
    watch_dir = Path.cwd()
    known_files = set()

    try:
        while True:
            current = set()
            for ext in [".txt", ".md", ".mp4", ".webm", ".m4v"]:
                for f in watch_dir.glob(f"*{ext}"):
                    current.add(f)

            new_files = current - known_files
            for nf in new_files:
                print(f"Обнаружен новый файл: {nf.name}")

            known_files = current
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nНаблюдение остановлено.")


def resume_queue(args):
    from services.batch_service import BatchService
    from services.processing_service import ProcessingService
    from settings import DATA_DIR

    state_path = DATA_DIR / "batch_state.json"
    if not state_path.exists():
        print("Файл batch_state.json не найден. Нечего восстанавливать.")
        sys.exit(1)

    service = BatchService()
    batch = service.load_state(state_path)
    if not batch or not batch.items:
        print("Очередь пуста.")
        return

    pending = [i for i in batch.items if i.status not in ("completed", "skipped")]
    print(f"Восстановлено: {len(batch.items)} элементов, {len(pending)} ожидают обработки.")

    proc = ProcessingService(progress_callback=lambda stage, pct, item:
                             print(f"  [{pct:.0f}%] {stage} — {item.display_name}"))
    for item in pending:
        print(f"\nОбработка: {item.display_name}")
        result = proc.process_item(item)
        if not result["success"]:
            print(f"  Ошибка: {result.get('error', 'неизвестно')}")

    service.save_state(state_path)
    print("\nВосстановление завершено.")


if __name__ == "__main__":
    main()

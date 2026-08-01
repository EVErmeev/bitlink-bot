from pathlib import Path

from models.batch import BatchItem
from services.runtime_config import RuntimeConfig


def run_preflight(items: list[BatchItem], config: RuntimeConfig) -> dict:
    errors = []
    warnings = []
    has_blocking = False
    items_checked = 0

    for item in items:
        if item.status in ("completed", "skipped"):
            continue
        items_checked += 1
        item_errors, item_warnings, item_blocking = _check_item(item, config)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        if item_blocking:
            has_blocking = True

    if items_checked == 0:
        errors.append("Нет элементов для обработки (все completed/skipped)")
        has_blocking = True

    has_warnings = len(warnings) > 0

    return {
        "passed": not has_blocking,
        "has_warnings": has_warnings,
        "has_blocking": has_blocking,
        "errors": errors,
        "warnings": warnings,
        "items_checked": items_checked,
        "items_total": len(items),
    }


def _check_item(item: BatchItem, config: RuntimeConfig) -> tuple[list[str], list[str], bool]:
    errors: list[str] = []
    warnings: list[str] = []
    blocking = False

    st = item.source_type

    # File checks
    if st in ("local_transcript", "local_video"):
        if not item.source_path:
            errors.append(f"{item.display_name}: путь к файлу не указан")
            return errors, warnings, True
        fpath = Path(item.source_path)
        if not fpath.exists():
            errors.append(f"{item.display_name}: файл не найден: {item.source_path}")
            return errors, warnings, True
        if fpath.is_dir():
            errors.append(f"{item.display_name}: указан каталог, а не файл")
            return errors, warnings, True
        if fpath.stat().st_size == 0:
            errors.append(f"{item.display_name}: файл пуст")
            return errors, warnings, True
        try:
            with open(fpath, "rb") as f:
                f.read(1)
        except Exception:
            errors.append(f"{item.display_name}: файл недоступен для чтения")
            return errors, warnings, True

    # Template check
    from protocol_templates.registry import TemplateRegistry
    tmpl = TemplateRegistry().get(item.protocol_template)
    if not tmpl:
        errors.append(f"{item.display_name}: шаблон {item.protocol_template} не найден")
        return errors, warnings, True

    # Service checks per source type
    if st == "local_transcript":
        # LLM required
        if config.llm_mode == "mock":
            warnings.append(f"{item.display_name}: LLM в mock-режиме")
        elif config.llm_mode == "real":
            if not config.llm_api_url or not config.llm_api_key:
                errors.append(f"{item.display_name}: LLM в real-режиме, но API URL/Key не указаны")
                blocking = True
            else:
                try:
                    from services.client_factory import build_llm_client
                    llm = build_llm_client(config)
                    if not llm.check_connection():
                        errors.append(f"{item.display_name}: LLM API недоступен")
                        blocking = True
                except Exception as e:
                    errors.append(f"{item.display_name}: ошибка LLM: {e}")
                    blocking = True
        # Newton SKIPPED for transcript
        # Bitlink SKIPPED for transcript
        # Confluence only if not dry-run
        if not item.dry_run and config.confluence_mode != "mock":
            if not config.confluence_base_url or not config.confluence_token:
                errors.append(f"{item.display_name}: Confluence REST требует BASE_URL и TOKEN")
                blocking = True
            elif not config.confluence_parent_page_id:
                warnings.append(f"{item.display_name}: parent_page_id не указан")
        # Telegram only if send_telegram
        if item.send_telegram and config.telegram_mode == "real":
            if not config.telegram_bot_token or not config.telegram_chat_id:
                warnings.append(f"{item.display_name}: Telegram real-режим без токена/chat_id")

    elif st == "local_video":
        if config.newton_mode == "mock":
            warnings.append(f"{item.display_name}: Newton в mock-режиме")
        elif config.newton_mode in ("disabled", "http_api"):
            errors.append(f"{item.display_name}: Newton ({config.newton_mode}) — видео не может быть обработано")
            blocking = True
        # LLM same as transcript
        if config.llm_mode == "mock":
            warnings.append(f"{item.display_name}: LLM в mock-режиме")
        elif config.llm_mode == "real":
            if not config.llm_api_url or not config.llm_api_key:
                errors.append(f"{item.display_name}: LLM в real-режиме, но API URL/Key не указаны")
                blocking = True
            else:
                try:
                    from services.client_factory import build_llm_client
                    llm = build_llm_client(config)
                    if not llm.check_connection():
                        errors.append(f"{item.display_name}: LLM API недоступен")
                        blocking = True
                except Exception as e:
                    errors.append(f"{item.display_name}: ошибка LLM: {e}")
                    blocking = True
        # Confluence same as transcript
        if not item.dry_run and config.confluence_mode != "mock":
            if not config.confluence_base_url or not config.confluence_token:
                errors.append(f"{item.display_name}: Confluence REST требует BASE_URL и TOKEN")
                blocking = True
            elif not config.confluence_parent_page_id:
                warnings.append(f"{item.display_name}: parent_page_id не указан")
        # Telegram same as transcript
        if item.send_telegram and config.telegram_mode == "real":
            if not config.telegram_bot_token or not config.telegram_chat_id:
                warnings.append(f"{item.display_name}: Telegram real-режим без токена/chat_id")

    elif st == "bitlink":
        if config.bitlink_mode == "mock":
            warnings.append(f"{item.display_name}: BIT.Link в mock-режиме")
        elif config.bitlink_mode == "real":
            if not config.bitlink_base_url:
                errors.append(f"{item.display_name}: BIT.Link real требует BASE_URL")
                blocking = True
        # Newton required for bitlink transcript
        if config.newton_mode in ("disabled", "http_api"):
            warnings.append(f"{item.display_name}: Newton ({config.newton_mode}) — транскрибация может быть недоступна")

    # Mixed mode protection
    if config.is_demo_mode() and not item.dry_run:
        item.dry_run = True
        warnings.append(f"{item.display_name}: demo-режим — автоматически включён dry-run для защиты от публикации mock-контента")

    return errors, warnings, blocking

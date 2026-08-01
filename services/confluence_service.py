import uuid
import settings


class ConfluenceConfigurationError(Exception):
    pass


class ConfluenceClient:
    def __init__(self, base_url=None, token=None, space_key=None):
        self.mock_mode = settings.CONFLUENCE_MOCK
        self.base_url = base_url or settings.CONFLUENCE_BASE_URL
        self.token = token or settings.CONFLUENCE_TOKEN
        self.space_key = space_key or settings.CONFLUENCE_SPACE_KEY

        if not self.mock_mode:
            missing = []
            if not self.base_url:
                missing.append("CONFLUENCE_BASE_URL")
            if not self.token:
                missing.append("CONFLUENCE_TOKEN")
            if not self.space_key:
                missing.append("CONFLUENCE_SPACE_KEY")
            if missing:
                raise ConfluenceConfigurationError(
                    f"CONFLUENCE_MOCK=false, но отсутствуют настройки: {', '.join(missing)}. "
                    f"Укажите их в .env или установите CONFLUENCE_MOCK=true."
                )

    def check_connection(self) -> bool:
        if self.mock_mode:
            return True
        return bool(self.base_url and self.token)

    def get_page(self, page_id: str) -> dict | None:
        if self.mock_mode:
            return {"id": page_id, "title": "Мок-страница", "space": self.space_key or "MOCK"}
        raise NotImplementedError(
            "Реальный API Confluence не реализован. "
            "Используйте CONFLUENCE_MOCK=true для mock-режима."
        )

    def find_page_by_title(self, title: str, space_key: str = None) -> list[dict]:
        if self.mock_mode:
            return [
                {"id": "page_1", "title": "Протоколы встреч 2026", "space": space_key or self.space_key or "MOCK"},
                {"id": "page_2", "title": "Рабочая группа ERP", "space": space_key or self.space_key or "MOCK"},
            ]
        raise NotImplementedError(
            "Поиск страниц через реальный API Confluence не реализован."
        )

    def create_page(self, title: str, storage_html: str, parent_page_id: str = None,
                    space_key: str = None) -> dict:
        space = space_key or self.space_key or "MOCK"
        if self.mock_mode:
            page_id = str(uuid.uuid4())[:8]
            url = f"https://mock-confluence.example.com/spaces/{space}/pages/{page_id}"
            return {"id": page_id, "title": title, "url": url, "space": space}
        raise NotImplementedError(
            "Публикация страниц через реальный API Confluence не реализована. "
            "API-контракты Confluence REST API (POST /wiki/rest/api/content с ancestors) "
            "не подтверждены в рамках данного проекта. "
            "Используйте CONFLUENCE_MOCK=true для mock-режима."
        )
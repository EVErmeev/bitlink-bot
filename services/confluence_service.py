import uuid


class ConfluenceClient:
    def __init__(self, base_url=None, token=None, space_key=None):
        self.base_url = base_url
        self.token = token
        self.space_key = space_key
        self.mock_mode = True

    def check_connection(self) -> bool:
        return self.mock_mode

    def get_page(self, page_id: str) -> dict | None:
        return {
            "id": page_id,
            "title": "Мок-страница",
            "space": self.space_key or "MOCK",
            "version": 1,
        }

    def find_page_by_title(self, title: str, space_key: str = None) -> list[dict]:
        return [
            {"id": "page_1", "title": "Протоколы встреч 2026", "space": space_key or "MOCK"},
            {"id": "page_2", "title": "Рабочая группа ERP", "space": space_key or "MOCK"},
        ]

    def create_page(self, title: str, storage_html: str, parent_page_id: str = None,
                    space_key: str = None) -> dict:
        page_id = str(uuid.uuid4())[:8]
        space = space_key or self.space_key or "MOCK"
        url = f"https://mock-confluence.example.com/spaces/{space}/pages/{page_id}"
        return {
            "id": page_id,
            "title": title,
            "url": url,
            "space": space,
            "status": "created",
        }
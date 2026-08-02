import uuid

import requests

import settings


def _extract_body(html: str) -> str:
    """Extract body content for Confluence storage format. Removes <head>/<style>/<script>."""
    import re
    # Remove <html>, <head>, <body> wrapper tags but keep body content
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    if body_match:
        html = body_match.group(1)
    # Remove style blocks
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    # Remove script blocks
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    return html.strip()


class ConfluenceConfigurationError(Exception):
    pass


class ConfluenceClient:
    def __init__(self, base_url=None, token=None, space_key=None):
        self.provider = settings.CONFLUENCE_PROVIDER
        if self.provider not in ("mock", "rest", "mcp"):
            raise ConfluenceConfigurationError(
                f"Unknown CONFLUENCE_PROVIDER: {self.provider}"
            )

        self.mock_mode = (self.provider == "mock")
        self.base_url = base_url or settings.CONFLUENCE_BASE_URL
        self.token = token or settings.CONFLUENCE_TOKEN
        self.space_key = space_key or settings.CONFLUENCE_SPACE_KEY

        if self.provider == "rest":
            missing = []
            if not self.base_url:
                missing.append("CONFLUENCE_BASE_URL")
            if not self.token:
                missing.append("CONFLUENCE_TOKEN")
            if not self.space_key:
                missing.append("CONFLUENCE_SPACE_KEY")
            if missing:
                raise ConfluenceConfigurationError(
                    f"CONFLUENCE_PROVIDER=rest but missing: {', '.join(missing)}"
                )
        elif self.provider == "mcp":
            raise NotImplementedError(
                "CONFLUENCE_PROVIDER=mcp is not supported as runtime transport. "
                "MCP is only available via OpenCode tools. Use CONFLUENCE_PROVIDER=rest."
            )

    def check_connection(self) -> bool:
        if self.provider == "mock":
            return True
        if self.provider == "rest":
            try:
                resp = requests.get(
                    f"{self.base_url}/rest/api/user/current",
                    headers={"Authorization": f"Bearer {self.token}"},
                    timeout=10,
                )
                return resp.status_code == 200
            except Exception:
                return False
        return False

    def create_page(self, title: str, storage_html: str,
                    parent_page_id: str | None = None,
                    space_key: str | None = None,
                    idempotency_key: str | None = None) -> dict:
        space = space_key or self.space_key
        if self.provider == "mock":
            page_id = str(uuid.uuid4())[:8]
            return {
                "id": page_id,
                "title": title,
                "url": f"https://mock-confluence.example.com/spaces/{space}/pages/{page_id}",
                "space": space,
            }

        if self.provider == "rest":
            body = {
                "type": "page",
                "title": title,
                "space": {"key": space},
                "body": {
                    "storage": {"value": _extract_body(storage_html), "representation": "storage"}
                },
            }
            if parent_page_id:
                try:
                    body["ancestors"] = [{"id": int(parent_page_id)}]  # type: ignore[list-item]
                except (ValueError, TypeError):
                    pass  # non-numeric parent ID in mock/test context
            resp = requests.post(
                f"{self.base_url}/rest/api/content",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json=body,  # type: ignore[arg-type]
                timeout=60,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"Confluence create page failed: {resp.status_code} {resp.text[:500]}"
                )
            data = resp.json()
            page_id = str(data["id"])
            url = f"{self.base_url}/spaces/{space}/pages/{page_id}"
            return {"id": page_id, "title": title, "url": url, "space": space}
        raise NotImplementedError(f"Provider {self.provider} not implemented")

    def get_page(self, page_id: str) -> dict | None:
        if self.provider == "mock":
            return {
                "id": page_id,
                "title": "Mock Page",
                "space": self.space_key or "MOCK",
            }
        resp = requests.get(
            f"{self.base_url}/rest/api/content/{page_id}?expand=body.storage,ancestors,space",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        return resp.json()

    def find_page_by_title(self, title: str,
                           space_key: str | None = None) -> list[dict]:
        if self.provider == "mock":
            return [{
                "id": "page_1",
                "title": title,
                "space": space_key or self.space_key or "MOCK",
            }]
        space = space_key or self.space_key
        cql = f'title~"{title}"'
        if space:
            cql += f' AND space="{space}"'
        resp = requests.get(
            f"{self.base_url}/rest/api/content/search?cql={requests.utils.quote(cql)}&limit=10",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            return []
        results = resp.json().get("results", [])
        return [{
            "id": str(r["id"]),
            "title": r["title"],
            "space": r.get("space", {}).get("key", ""),
        } for r in results]

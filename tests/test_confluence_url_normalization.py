import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from services.confluence_service import (
    ConfluenceConfigurationError,
    ConfluenceClient,
    normalize_confluence_base_url,
)


class TestNormalizeConfluenceBaseUrl:
    def test_keeps_root_without_trailing_slash(self):
        assert normalize_confluence_base_url("https://art-conf.spbco.1cbit.ru") == (
            "https://art-conf.spbco.1cbit.ru"
        )

    def test_strips_trailing_slash(self):
        assert normalize_confluence_base_url("https://art-conf.spbco.1cbit.ru/") == (
            "https://art-conf.spbco.1cbit.ru"
        )

    def test_strips_trailing_multiple_slashes_and_whitespace(self):
        assert normalize_confluence_base_url("  https://host.example.com///  ") == (
            "https://host.example.com"
        )

    def test_rejects_rest_api_path(self):
        with pytest.raises(ConfluenceConfigurationError):
            normalize_confluence_base_url("https://host.example.com/rest/api")

    def test_rejects_rest_api_content_path(self):
        with pytest.raises(ConfluenceConfigurationError):
            normalize_confluence_base_url("https://host.example.com/rest/api/content")

    def test_rejects_space_path(self):
        with pytest.raises(ConfluenceConfigurationError):
            normalize_confluence_base_url("https://host.example.com/spaces/TXT")

    def test_rejects_display_path(self):
        with pytest.raises(ConfluenceConfigurationError):
            normalize_confluence_base_url("https://host.example.com/display/TXT/Some+Page")

    def test_rejects_concrete_page_url(self):
        with pytest.raises(ConfluenceConfigurationError):
            normalize_confluence_base_url(
                "https://host.example.com/pages/viewpage.action?pageId=213352588"
            )

    def test_rejects_non_http_scheme(self):
        with pytest.raises(ConfluenceConfigurationError):
            normalize_confluence_base_url("ftp://host.example.com")

    def test_empty_returns_empty(self):
        assert normalize_confluence_base_url("") == ""
        assert normalize_confluence_base_url(None) == ""


class TestConfluenceClientNormalization:
    def test_client_normalizes_base_url(self, monkeypatch):
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_BASE_URL",
                            "https://host.example.com/")
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_PROVIDER", "mock")
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_TOKEN", "t")
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_SPACE_KEY", "TXT")
        client = ConfluenceClient()
        assert client.base_url == "https://host.example.com"

    def test_client_rejects_bad_base_url(self, monkeypatch):
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_PROVIDER", "mock")
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_TOKEN", "t")
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_SPACE_KEY", "TXT")
        with pytest.raises(ConfluenceConfigurationError):
            ConfluenceClient(base_url="https://host.example.com/rest/api/content")

    def test_parent_page_exists_returns_false_for_mock(self, monkeypatch):
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_PROVIDER", "mock")
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_TOKEN", "t")
        monkeypatch.setattr("services.confluence_service.settings.CONFLUENCE_SPACE_KEY", "TXT")
        client = ConfluenceClient(base_url="https://host.example.com")
        assert client.parent_page_exists("123") is False
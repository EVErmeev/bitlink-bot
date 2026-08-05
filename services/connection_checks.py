"""Unified connection check result model for all service providers."""
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ConnectionCheckResult:
    service_id: str = ""
    provider: str = ""
    status: str = ""  # PASS, FAIL, TIMEOUT, NOT_CONFIGURED, MOCK, NOT_IMPLEMENTED, SKIPPED
    stage: str = ""
    safe_message: str = ""
    recommendation: str = ""
    endpoint_or_command: str = ""
    http_status: int | None = None
    exit_code: int | None = None
    latency_seconds: float | None = None
    checked_at: str = ""
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict:
        return {
            "service_id": self.service_id, "provider": self.provider,
            "status": self.status, "stage": self.stage,
            "safe_message": self.safe_message, "recommendation": self.recommendation,
            "endpoint_or_command": self.endpoint_or_command,
            "http_status": self.http_status, "exit_code": self.exit_code,
            "latency_seconds": self.latency_seconds, "checked_at": self.checked_at,
            "details": {k: v for k, v in self.details.items()
                       if k not in ("token", "password", "api_key", "authorization")},
        }

    @property
    def is_pass(self) -> bool:
        return self.status == "PASS"


def make_mock_result(service_id: str) -> ConnectionCheckResult:
    return ConnectionCheckResult(service_id=service_id, provider="mock", status="MOCK",
        stage="provider_check", safe_message="DEMO / MOCK — реальное подключение не проверялось",
        recommendation="Для рабочей проверки переключите provider в real-режим.")


def make_not_implemented_result(service_id: str) -> ConnectionCheckResult:
    return ConnectionCheckResult(service_id=service_id, provider="real", status="NOT_IMPLEMENTED",
        stage="provider_check",
        safe_message="Реальный адаптер не реализован. Проверка подключения невозможна.",
        recommendation="API-контракт не подтверждён. Используйте mock-режим.")


def make_not_configured_result(service_id: str, missing_fields: list[str]) -> ConnectionCheckResult:
    return ConnectionCheckResult(service_id=service_id, provider="real", status="NOT_CONFIGURED",
        stage="config_validation",
        safe_message=f"Не настроено: {', '.join(missing_fields)}",
        recommendation="Заполните обязательные поля и повторите проверку.")


def make_error_result(service_id: str, error: str) -> ConnectionCheckResult:
    return ConnectionCheckResult(service_id=service_id, provider="unknown", status="FAIL",
        stage="internal_error", safe_message=str(error)[:300],
        recommendation="Проверьте настройки и повторите.")


@dataclass(frozen=True)
class ConnectionCheckInput:
    service_id: str = ""
    provider: str = "mock"
    base_url: str = ""
    token: str = ""
    space_key: str = ""
    parent_page_id: str = ""
    parent_page_title: str = ""
    chat_id: str = ""
    cli_path: str = ""
    model: str = ""
    timeout_seconds: int = 30
    output_encoding: str = "auto"

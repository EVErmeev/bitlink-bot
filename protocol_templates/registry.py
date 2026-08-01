from protocol_templates.base import BaseProtocolTemplate
from protocol_templates.management_summary import ManagementSummaryTemplate
from protocol_templates.project_standard import ProjectStandardTemplate
from protocol_templates.project_detailed import ProjectDetailedTemplate
from protocol_templates.business_process_discovery import BusinessProcessDiscoveryTemplate


class TemplateRegistry:
    _instance = None
    _templates: dict[str, BaseProtocolTemplate] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._register()
        return cls._instance

    def _register(self):
        self._templates = {
            "management_summary": ManagementSummaryTemplate(),
            "project_standard": ProjectStandardTemplate(),
            "project_detailed": ProjectDetailedTemplate(),
            "business_process_discovery": BusinessProcessDiscoveryTemplate(),
        }

    def get(self, template_id: str) -> BaseProtocolTemplate | None:
        return self._templates.get(template_id)

    def list_templates(self) -> list[dict]:
        return [
            {"id": tid, "display_name": t.display_name, "version": t.version, "description": t.description}
            for tid, t in self._templates.items()
        ]

    def get_all(self) -> dict[str, BaseProtocolTemplate]:
        return self._templates
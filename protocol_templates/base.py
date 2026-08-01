from abc import ABC, abstractmethod

from models.protocol import (
    Protocol,
)
from models.validation import ValidationReport


class BaseProtocolTemplate(ABC):
    template_id: str = ""
    version: str = "1.0"
    display_name: str = ""
    description: str = ""

    @abstractmethod
    def get_schema(self) -> dict:
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    @abstractmethod
    def assemble(self, protocol: Protocol, atomic_items: list, meeting_metadata: dict) -> Protocol:
        pass

    def assemble_from_llm_json(self, protocol: Protocol, atomic_items: list,
                                llm_data: dict, meeting_metadata: dict) -> Protocol:
        """Parse schema-valid LLM JSON dict into protocol fields. Override per template."""
        protocol.meeting_purpose = llm_data.get("meeting_purpose", protocol.meeting_purpose or "")
        protocol.key_outcomes = llm_data.get("key_outcomes", "")
        protocol.meeting_context = llm_data.get("meeting_context", "")
        if llm_data.get("participants"):
            protocol.participants = llm_data["participants"]
        return protocol

    def assemble_with_llm_output(self, protocol: Protocol, atomic_items: list,
                                  llm_output: str, meeting_metadata: dict) -> Protocol:
        try:
            import json
            llm_data = json.loads(llm_output)
            return self.assemble_from_llm_json(protocol, atomic_items, llm_data, meeting_metadata)
        except (json.JSONDecodeError, TypeError):
            return self.assemble(protocol, atomic_items, meeting_metadata)

    @abstractmethod
    def validate(self, protocol: Protocol) -> ValidationReport:
        pass

    @abstractmethod
    def render_html(self, protocol: Protocol) -> str:
        pass

    @abstractmethod
    def validate_render(self, html: str, protocol: Protocol) -> ValidationReport:
        pass

    def get_json_schema(self) -> dict:
        return self.get_schema()

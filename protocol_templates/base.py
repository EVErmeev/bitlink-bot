from abc import ABC, abstractmethod
from models.protocol import Protocol, TopicBlock, DecisionItem, QuestionItem, RiskItem, TaskItem
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

    def assemble_with_llm_output(self, protocol: Protocol, atomic_items: list,
                                  llm_output: str, meeting_metadata: dict) -> Protocol:
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
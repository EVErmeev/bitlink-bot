from dataclasses import dataclass, field
from datetime import date, time


@dataclass
class AtomicItem:
    item_id: str
    source_context_id: str
    item_type: str
    text: str
    speaker: str = ""
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    importance: float = 0.5
    confidence: float = 0.8
    explicit_agreement: bool = False
    commitment_confirmed: bool = False
    evidence: str = ""


@dataclass
class TopicBlock:
    topic_id: str
    title: str
    source_context_id: str
    discussion_content: str = ""
    conclusion: str = ""
    status_text: str = ""
    status_reason: str = ""
    status_next_action: str = ""
    status_responsible: str = ""
    status_deadline: str = ""
    order: int = 0
    word_count: int = 0
    source_item_ids: list = field(default_factory=list)
    evidence: list = field(default_factory=list)


@dataclass
class DecisionItem:
    decision_id: str
    source_context_id: str
    decision_text: str = ""
    context_and_basis: str = ""
    agreed_scope: str = ""
    boundaries: str = ""
    responsible: str = ""
    deadline: str = ""
    related_topic: str = ""
    order: int = 0
    explicit_agreement: bool = False
    confidence: float = 0.0
    evidence: str = ""


@dataclass
class QuestionItem:
    question_id: str
    source_context_id: str
    question_text: str = ""
    context: str = ""
    known_info: str = ""
    to_determine: str = ""
    responsible: str = ""
    deadline: str = ""
    next_action: str = ""
    status: str = ""
    related_topic: str = ""
    order: int = 0


@dataclass
class RiskItem:
    risk_id: str
    source_context_id: str
    risk_type: str = ""
    risk_text: str = ""
    reason: str = ""
    impact: str = ""
    trigger_condition: str = ""
    measures: str = ""
    responsible: str = ""
    deadline: str = ""
    status: str = ""
    related_topic: str = ""
    order: int = 0


@dataclass
class TaskItem:
    task_id: str
    source_context_id: str
    task_text: str = ""
    basis: str = ""
    expected_result: str = ""
    responsible: str = ""
    co_executors: str = ""
    deadline: str = ""
    dependencies: str = ""
    status: str = ""
    related_topic: str = ""
    order: int = 0
    commitment_confirmed: bool = False


@dataclass
class Protocol:
    protocol_id: str
    template_id: str
    source_context_id: str

    # Section 1: General info
    meeting_date: date | None = None
    meeting_time: time | None = None
    protocol_title: str = ""
    meeting_purpose: str = ""

    # Section 2: Participants
    participants: list[dict] = field(default_factory=list)

    # Section 3: Purpose and context
    meeting_context: str = ""

    # Section 4: Key outcomes
    key_outcomes: str = ""

    # Section 5: Topic blocks (detailed)
    topic_blocks: list[TopicBlock] = field(default_factory=list)

    # Section 6: Current state
    current_state: str = ""

    # Section 7: Decisions
    decisions: list[DecisionItem] = field(default_factory=list)

    # Section 8: Questions
    questions: list[QuestionItem] = field(default_factory=list)

    # Section 9: Risks
    risks: list[RiskItem] = field(default_factory=list)

    # Section 10: Tasks
    tasks: list[TaskItem] = field(default_factory=list)

    # Additional sections for other templates
    management_summary: str = ""
    process_scheme: str = ""
    functional_gaps: str = ""
    control_points: str = ""
    agreed_approaches: str = ""
    considered_options: str = ""
    thematic_sections: list = field(default_factory=list)

    # For business_process_discovery
    processes_as_is: str = ""
    roles_description: str = ""
    systems_and_documents: str = ""
    process_steps: list = field(default_factory=list)
    problems: list = field(default_factory=list)
    requirements: list = field(default_factory=list)
    integration_points: str = ""

    # Provenance
    source_alignment_passed: bool = False
    fact_validation_passed: bool = False
    structure_validation_passed: bool = False
    render_validation_passed: bool = False
    topic_coverage_passed: bool = False
    topic_alignment_passed: bool = False

    # Atomic items used to generate
    atomic_items: list[AtomicItem] = field(default_factory=list)

    # Client/project context
    client_name: str = ""
    project_name: str = ""

    def to_dict(self) -> dict:
        return {
            "protocol_id": self.protocol_id,
            "template_id": self.template_id,
            "source_context_id": self.source_context_id,
            "meeting_date": self.meeting_date.isoformat() if self.meeting_date else None,
            "meeting_time": self.meeting_time.strftime("%H:%M") if self.meeting_time else None,
            "protocol_title": self.protocol_title,
            "meeting_purpose": self.meeting_purpose,
            "participants": self.participants,
            "meeting_context": self.meeting_context,
            "key_outcomes": self.key_outcomes,
            "topic_blocks": [
                {
                    "topic_id": tb.topic_id,
                    "title": tb.title,
                    "source_context_id": tb.source_context_id,
                    "discussion_content": tb.discussion_content,
                    "conclusion": tb.conclusion,
                    "status_text": tb.status_text,
                    "status_reason": tb.status_reason,
                    "status_next_action": tb.status_next_action,
                    "status_responsible": tb.status_responsible,
                    "status_deadline": tb.status_deadline,
                    "order": tb.order,
                    "word_count": tb.word_count,
                    "source_item_ids": tb.source_item_ids,
                    "evidence": tb.evidence,
                }
                for tb in self.topic_blocks
            ],
            "current_state": self.current_state,
            "decisions": [
                {
                    "decision_id": d.decision_id,
                    "source_context_id": d.source_context_id,
                    "decision_text": d.decision_text,
                    "context_and_basis": d.context_and_basis,
                    "agreed_scope": d.agreed_scope,
                    "boundaries": d.boundaries,
                    "responsible": d.responsible,
                    "deadline": d.deadline,
                    "related_topic": d.related_topic,
                    "order": d.order,
                    "explicit_agreement": d.explicit_agreement,
                    "confidence": d.confidence,
                    "evidence": d.evidence,
                }
                for d in self.decisions
            ],
            "questions": [
                {
                    "question_id": q.question_id,
                    "source_context_id": q.source_context_id,
                    "question_text": q.question_text,
                    "context": q.context,
                    "known_info": q.known_info,
                    "to_determine": q.to_determine,
                    "responsible": q.responsible,
                    "deadline": q.deadline,
                    "next_action": q.next_action,
                    "status": q.status,
                    "related_topic": q.related_topic,
                    "order": q.order,
                }
                for q in self.questions
            ],
            "risks": [
                {
                    "risk_id": r.risk_id,
                    "source_context_id": r.source_context_id,
                    "risk_type": r.risk_type,
                    "risk_text": r.risk_text,
                    "reason": r.reason,
                    "impact": r.impact,
                    "trigger_condition": r.trigger_condition,
                    "measures": r.measures,
                    "responsible": r.responsible,
                    "deadline": r.deadline,
                    "status": r.status,
                    "related_topic": r.related_topic,
                    "order": r.order,
                }
                for r in self.risks
            ],
            "tasks": [
                {
                    "task_id": t.task_id,
                    "source_context_id": t.source_context_id,
                    "task_text": t.task_text,
                    "basis": t.basis,
                    "expected_result": t.expected_result,
                    "responsible": t.responsible,
                    "co_executors": t.co_executors,
                    "deadline": t.deadline,
                    "dependencies": t.dependencies,
                    "status": t.status,
                    "related_topic": t.related_topic,
                    "order": t.order,
                    "commitment_confirmed": t.commitment_confirmed,
                }
                for t in self.tasks
            ],
            "management_summary": self.management_summary,
            "process_scheme": self.process_scheme,
            "functional_gaps": self.functional_gaps,
            "control_points": self.control_points,
            "agreed_approaches": self.agreed_approaches,
            "considered_options": self.considered_options,
            "thematic_sections": self.thematic_sections,
            "processes_as_is": self.processes_as_is,
            "roles_description": self.roles_description,
            "systems_and_documents": self.systems_and_documents,
            "process_steps": self.process_steps,
            "problems": self.problems,
            "requirements": self.requirements,
            "integration_points": self.integration_points,
            "source_alignment_passed": self.source_alignment_passed,
            "fact_validation_passed": self.fact_validation_passed,
            "structure_validation_passed": self.structure_validation_passed,
            "render_validation_passed": self.render_validation_passed,
            "topic_coverage_passed": self.topic_coverage_passed,
            "topic_alignment_passed": self.topic_alignment_passed,
            "client_name": self.client_name,
            "project_name": self.project_name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Protocol":
        p = cls(
            protocol_id=d.get("protocol_id", ""),
            template_id=d.get("template_id", ""),
            source_context_id=d.get("source_context_id", ""),
        )
        if d.get("meeting_date"):
            p.meeting_date = date.fromisoformat(d["meeting_date"])
        if d.get("meeting_time"):
            parts = d["meeting_time"].split(":")
            p.meeting_time = time(int(parts[0]), int(parts[1]))
        p.protocol_title = d.get("protocol_title", "")
        p.meeting_purpose = d.get("meeting_purpose", "")
        p.participants = d.get("participants", [])
        p.meeting_context = d.get("meeting_context", "")
        p.key_outcomes = d.get("key_outcomes", "")
        p.current_state = d.get("current_state", "")
        p.management_summary = d.get("management_summary", "")
        p.process_scheme = d.get("process_scheme", "")
        p.functional_gaps = d.get("functional_gaps", "")
        p.control_points = d.get("control_points", "")
        p.agreed_approaches = d.get("agreed_approaches", "")
        p.considered_options = d.get("considered_options", "")
        p.thematic_sections = d.get("thematic_sections", [])
        p.processes_as_is = d.get("processes_as_is", "")
        p.roles_description = d.get("roles_description", "")
        p.systems_and_documents = d.get("systems_and_documents", "")
        p.process_steps = d.get("process_steps", [])
        p.problems = d.get("problems", [])
        p.requirements = d.get("requirements", [])
        p.integration_points = d.get("integration_points", "")
        p.source_alignment_passed = d.get("source_alignment_passed", False)
        p.fact_validation_passed = d.get("fact_validation_passed", False)
        p.structure_validation_passed = d.get("structure_validation_passed", False)
        p.render_validation_passed = d.get("render_validation_passed", False)
        p.topic_coverage_passed = d.get("topic_coverage_passed", False)
        p.topic_alignment_passed = d.get("topic_alignment_passed", False)
        p.client_name = d.get("client_name", "")
        p.project_name = d.get("project_name", "")

        for tb in d.get("topic_blocks", []):
            p.topic_blocks.append(TopicBlock(
                topic_id=tb.get("topic_id", ""),
                title=tb.get("title", ""),
                source_context_id=tb.get("source_context_id", ""),
                discussion_content=tb.get("discussion_content", ""),
                conclusion=tb.get("conclusion", ""),
                status_text=tb.get("status_text", ""),
                status_reason=tb.get("status_reason", ""),
                status_next_action=tb.get("status_next_action", ""),
                status_responsible=tb.get("status_responsible", ""),
                status_deadline=tb.get("status_deadline", ""),
                order=tb.get("order", 0),
                word_count=tb.get("word_count", 0),
                source_item_ids=tb.get("source_item_ids", []),
                evidence=tb.get("evidence", []),
            ))
        for dec in d.get("decisions", []):
            p.decisions.append(DecisionItem(
                decision_id=dec.get("decision_id", ""),
                source_context_id=dec.get("source_context_id", ""),
                decision_text=dec.get("decision_text", ""),
                context_and_basis=dec.get("context_and_basis", ""),
                agreed_scope=dec.get("agreed_scope", ""),
                boundaries=dec.get("boundaries", ""),
                responsible=dec.get("responsible", ""),
                deadline=dec.get("deadline", ""),
                related_topic=dec.get("related_topic", ""),
                order=dec.get("order", 0),
                explicit_agreement=dec.get("explicit_agreement", False),
                confidence=dec.get("confidence", 0.0),
                evidence=dec.get("evidence", ""),
            ))
        for q in d.get("questions", []):
            p.questions.append(QuestionItem(
                question_id=q.get("question_id", ""),
                source_context_id=q.get("source_context_id", ""),
                question_text=q.get("question_text", ""),
                context=q.get("context", ""),
                known_info=q.get("known_info", ""),
                to_determine=q.get("to_determine", ""),
                responsible=q.get("responsible", ""),
                deadline=q.get("deadline", ""),
                next_action=q.get("next_action", ""),
                status=q.get("status", ""),
                related_topic=q.get("related_topic", ""),
                order=q.get("order", 0),
            ))
        for r in d.get("risks", []):
            p.risks.append(RiskItem(
                risk_id=r.get("risk_id", ""),
                source_context_id=r.get("source_context_id", ""),
                risk_type=r.get("risk_type", ""),
                risk_text=r.get("risk_text", ""),
                reason=r.get("reason", ""),
                impact=r.get("impact", ""),
                trigger_condition=r.get("trigger_condition", ""),
                measures=r.get("measures", ""),
                responsible=r.get("responsible", ""),
                deadline=r.get("deadline", ""),
                status=r.get("status", ""),
                related_topic=r.get("related_topic", ""),
                order=r.get("order", 0),
            ))
        for t in d.get("tasks", []):
            p.tasks.append(TaskItem(
                task_id=t.get("task_id", ""),
                source_context_id=t.get("source_context_id", ""),
                task_text=t.get("task_text", ""),
                basis=t.get("basis", ""),
                expected_result=t.get("expected_result", ""),
                responsible=t.get("responsible", ""),
                co_executors=t.get("co_executors", ""),
                deadline=t.get("deadline", ""),
                dependencies=t.get("dependencies", ""),
                status=t.get("status", ""),
                related_topic=t.get("related_topic", ""),
                order=t.get("order", 0),
                commitment_confirmed=t.get("commitment_confirmed", False),
            ))
        return p

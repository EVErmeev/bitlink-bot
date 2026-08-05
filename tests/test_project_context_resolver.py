import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.project_context_resolver import (
    ProjectContextResolution,
    load_profiles,
    resolve_project_context,
)

_CONTROL = (
    "Встреча по внедрению складского контура на базе 1С и Mobile SMARTS (Клеверенс) с "
    "использованием ТСД. Обсуждались приёмка и размещение, маркированный товар, "
    "агрегированные упаковки, Data Matrix, управление доставкой и транспортная логистика. "
    "Роял Фуд является владельцем товара."
)


def _no_llm(*args, **kwargs):
    return None


class TestProjectContextResolver:
    def test_known_profile_resolves_royal_food_3pl(self):
        r = resolve_project_context(
            transcript_text=_CONTROL,
            source_filename="Встреча_31_07_26_14_06_05",
            source_title="Проектный протокол встречи 3.0 — складские процессы",
            participants=[{"name": "Наталья"}, {"name": "Сергей"}],
            known_profiles=load_profiles(),
            llm_client=None,
        )
        assert r.client_name == "Роял Фуд"
        assert r.project_name == "Склад 3PL"
        assert r.confidence in ("high", "medium")
        assert r.matched_profile_id == "royal-food-3pl"

    def test_context_resolution_has_evidence(self):
        r = resolve_project_context(
            transcript_text=_CONTROL, known_profiles=load_profiles(), llm_client=None,
        )
        assert isinstance(r.evidence, list)
        assert len(r.evidence) > 0

    def test_low_confidence_does_not_hallucinate_project(self):
        r = resolve_project_context(
            transcript_text="Обсуждались общие вопросы без специфики.",
            known_profiles=load_profiles(),
            llm_client=None,
        )
        assert r.client_name == "Не определено"
        assert r.project_name == "Не определено"

    def test_profiles_load_from_data_file(self):
        profiles = load_profiles()
        assert any(p.get("client_name") == "Роял Фуд" for p in profiles)

    def test_profiles_are_not_hardcoded(self):
        import inspect
        src = inspect.getsource(sys.modules[__name__])
        from services import project_context_resolver as mod
        resolver_src = inspect.getsource(mod)
        # Data must live in json, not as a literal in the resolver module
        assert "royal-food-3pl" not in resolver_src
        assert "Роял Фуд" not in resolver_src
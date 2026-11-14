from datetime import date

import pytest

from app.compiler.compiler import Assumption, CompilationError, SimulationModelCompiler
from app.documents.loaders import load_bytes
from app.documents.parser import DocumentParser
from app.knowledge.generator import generate_knowledge_base
from app.knowledge.render import render_markdown
from app.knowledge.schema import TEMPLATE_LABELS
from app.llm.adapter import LLMError
from app.simulation.engine import WorldEngine

PLAN = "\n".join([
    "科學營 2026/03/07",
    "08:00-08:25   報到   中廊",
    "08:25-08:45   始業式   崙暉樓",
    "10:10-10:20   休息",
    "11:00-11:10   休息",
    "16:15   歸賦   全體工作人員",
])


def _kb_json(**overrides):
    kb = {
        "title": "科學營",
        "overview": [
            {"label": "Event Name", "value": "科學營", "status": "confirmed", "pages": [], "quote": "科學營"},
            {"label": "Event Date", "value": "2026-03-07", "status": "confirmed", "pages": [],
             "quote": "2026/03/07"},
            {"label": "Expected Participants", "value": "32", "status": "inferred", "pages": [],
             "quote": "科學營", "note": "8 小隊 × 4 人"},
            {"label": "Event Objectives", "value": "讓學生愛上科學", "status": "confirmed", "pages": [],
             "quote": "讓學生愛上科學"},  # 原文沒有 → 應被標成 unverified
        ],
        "timeline": [
            {"start": "08:00", "end": "08:25", "activity": "報到", "venue": "中廊", "status": "confirmed",
             "quote": "08:00-08:25 報到 中廊"},
            {"start": "08:25", "end": "08:45", "activity": "始業式", "venue": "崙暉樓", "status": "confirmed",
             "quote": "08:25-08:45 始業式 崙暉樓"},
            {"start": "10:10", "end": "10:20", "activity": "休息", "status": "confirmed", "quote": "10:10-10:20 休息"},
            {"start": "11:00", "end": "11:10", "activity": "休息", "status": "confirmed", "quote": "11:00-11:10 休息"},
            {"start": "16:15", "end": None, "activity": "歸賦", "responsible": "全體工作人員",
             "status": "confirmed", "quote": "16:15 歸賦"},
        ],
        "venues": [
            {"name": "中廊", "usage": "報到", "capacity": None, "status": "confirmed", "quote": "中廊"},
            {"name": "崙暉樓", "usage": "始業式", "capacity": None, "status": "confirmed", "quote": "崙暉樓"},
        ],
        "scenarios": [{"title": "Rain", "fields": [{"label": "Trigger Condition", "value": "下雨",
                                                     "status": "inferred", "note": "假設"}]}],
        "data_issues": [{"description": "歸賦沒有結束時間", "pages": [1]}],
        "required_data": [{"item": "場地容量", "purpose": "資源限制", "priority": "高"}],
    }
    kb.update(overrides)
    return kb


class FakeLLM:
    def __init__(self, response):
        self.response = response
        self.context = None

    def generate_json(self, purpose, context, schema_name):
        self.context = context
        return self.response


def _generate():
    doc = load_bytes(PLAN.encode(), "camp.txt")
    llm = FakeLLM(_kb_json())
    return doc, llm, generate_knowledge_base(doc, llm)


def test_unverifiable_quotes_are_flagged_not_trusted():
    _, llm, result = _generate()
    objective = next(i for i in result.kb.overview if i.label == "Event Objectives")
    assert objective.status == "unverified"
    assert len(result.downgraded) == 1
    assert "untrusted_document" in llm.context and "不可捏造" in llm.context["instructions"]


def test_markdown_has_every_template_section_and_label():
    _, _, result = _generate()
    md = render_markdown(result.kb, source_name="camp.txt", today=date(2026, 11, 14))
    for n, heading in enumerate(["Event Overview", "Event Timeline", "Resource Allocation", "Event Constraints",
                                 "Participant Profiles", "Simulation Scenarios", "Event Dependencies",
                                 "Risk Assessment", "Contingency Plans", "AI Simulation Instructions"], start=1):
        assert f"# {n}. {heading}" in md
    for labels in TEMPLATE_LABELS.values():
        for label in labels:
            assert f"**{label}**" in md
    assert "## Scenario 01: Event Delay" in md and "## Scenario 03: Rain" in md
    assert "status: draft" in md and "last_updated: 2026-11-14" in md
    assert "- **Event Objectives**：讓學生愛上科學 [待查證]" in md
    assert "- **Expected Participants**：32 [推算：8 小隊 × 4 人]" in md
    assert "- **Maximum Capacity**：[待補]" in md
    assert "Do not invent missing information." in md


def test_rendered_markdown_compiles_without_llm(tmp_path):
    _, _, result = _generate()
    md_path = tmp_path / "camp.knowledge.md"
    md_path.write_text(render_markdown(result.kb, source_name="camp.txt"), encoding="utf-8")
    facts = DocumentParser().parse(str(md_path))

    with pytest.raises(CompilationError) as exc:
        SimulationModelCompiler().compile(facts)
    missing = {i.field_path for i in exc.value.issues}
    assert missing == {"activities.歸賦.duration_min", "resources.中廊.capacity", "resources.崙暉樓.capacity"}

    result = SimulationModelCompiler().compile_with_report(facts, [
        Assumption("activities.歸賦.duration_min", 15, "test"),
        Assumption("resources.中廊.capacity", 1, "test"),
        Assumption("resources.崙暉樓.capacity", 1, "test"),
    ])
    ir = result.ir
    assert ir.name == "科學營"
    assert [a.id for a in ir.activities] == ["報到", "始業式", "1010_休息", "1100_休息", "歸賦"]
    assert ir.activities[1].planned_start_min == 25 and ir.activities[1].duration_min == 20
    assert ir.activities[1].resource_id == "崙暉樓"
    assert WorldEngine().run(ir).completed_activities == 5


def test_invalid_llm_output_raises():
    doc = load_bytes(PLAN.encode(), "camp.txt")
    with pytest.raises(LLMError, match="schema"):
        generate_knowledge_base(doc, FakeLLM({"timeline": "oops"}))

"""KnowledgeBase → Activity Knowledge Base markdown（固定結構）。

時程表與場地表的欄位名稱刻意對應 ``TableFactExtractor`` 的表頭辨識，
所以產出的 markdown 可以不經 LLM、直接用規則編譯成 EventSimIR：

    | Start | End | Activity | Venue | Location Detail | Responsible | Source |
    | Venue | Usage | Capacity | Source |
"""
from __future__ import annotations

from datetime import date

from app.knowledge.schema import (DEFAULT_SCENARIOS, SCENARIO_LABELS, TEMPLATE_LABELS, Item,
                                  KnowledgeBase, Sourced)

MISSING = "[待補]"

AI_INSTRUCTIONS = [
    "Read and understand all event information before simulation.",
    "Use the provided resources and constraints as the initial state.",
    "Simulate possible unexpected events.",
    "Analyze direct and indirect impacts.",
    "Identify affected activities, resources and schedules.",
    "Evaluate the severity of each risk.",
    "Propose feasible mitigation strategies.",
    "Compare outcomes before and after mitigation.",
    "Do not invent missing information.",
    "Clearly distinguish confirmed facts, assumptions and simulated results.",
    "If information is insufficient, identify what additional data is required.",
]
EXTRA_INSTRUCTIONS = [
    "`[推算]` 視為 assumption；`[待補]`、`[待查證]` 不可自行填值，若模擬必須使用，請明確列出採用的假設值。",
    "第 11 節的資料不一致釐清前，相關模擬結果必須標註所採用的版本。",
]


def tag(src: Sourced) -> str:
    pages = ", ".join(f"p.{p}" for p in sorted(set(src.pages)))
    if src.status == "confirmed":
        return f"[{pages}]" if pages else "[文件]"
    if src.status == "inferred":
        detail = "：" + src.note if src.note else ""
        return f"[推算{detail}{'；' + pages if pages else ''}]"
    if src.status == "unverified":
        return "[待查證]"
    return MISSING


def _cell(text: str | None) -> str:
    if text is None or not str(text).strip():
        return "—"
    return str(text).replace("|", "／").replace("\n", " ").strip()


def _value(item: Item) -> str:
    if item.status == "missing" or item.value is None:
        return MISSING + (f"（{item.note}）" if item.note else "")
    return f"{item.value} {tag(item)}"


def _items(items: list[Item], required: list[str] | None = None) -> list[str]:
    by_label = {i.label: i for i in items}
    ordered = [by_label.get(label) or Item(label=label) for label in required or []]
    ordered += [i for i in items if i.label not in (required or [])]
    return [f"- **{i.label}**：{_value(i)}" for i in ordered]


def render_markdown(kb: KnowledgeBase, *, source_name: str, version: str = "1.0",
                    status: str | None = None, today: date | None = None) -> str:
    has_gaps = _has_gaps(kb)
    status = status or ("draft" if has_gaps else "confirmed")
    out: list[str] = [
        "---",
        f"title: {kb.title}",
        f"version: {version}",
        f"last_updated: {(today or date.today()).isoformat()}",
        f"status: {status}",
        "language: zh-TW",
        f"source: {source_name}",
        "---",
        "",
        "# Activity Knowledge Base",
        "",
        "> **標記說明** `[p.N]` 企劃書第 N 頁明確寫出（confirmed）；`[推算]` 由文件推算，需人工確認（inferred）；",
        "> `[待補]` 文件未提供（missing）；`[待查證]` 自動抽取的引文無法在原文找到，請人工核對。",
        "> 本檔由程式自動產生，可人工修改後再編譯成模擬模型。",
        "",
        "# 1. Event Overview",
        "",
        *_items(kb.overview, TEMPLATE_LABELS["overview"]),
        "",
        "# 2. Event Timeline",
        "",
        "| Start | End | Activity | Venue | Location Detail | Responsible | Source |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in kb.timeline:
        out.append("| " + " | ".join([
            _cell(row.start) if row.start else MISSING,
            _cell(row.end) if row.end else MISSING,
            _cell(row.activity), _cell(row.venue), _cell(row.location_detail),
            _cell(row.responsible), tag(row),
        ]) + " |")
    if kb.timeline_notes:
        out += ["", "## Timeline Notes", "", *_items(kb.timeline_notes)]

    out += ["", "# 3. Resource Allocation", "", "## Human Resources", "",
            *_items(kb.human_resources, TEMPLATE_LABELS["human_resources"]),
            "", "## Venues", "", "| Venue | Usage | Capacity | Source |", "|---|---|---|---|"]
    for v in kb.venues:
        cap = str(v.capacity) if v.capacity is not None else MISSING
        out.append(f"| {_cell(v.name)} | {_cell(v.usage)} | {cap} | {tag(v)} |")
    out += ["", "## Equipment", "", *_items(kb.equipment, TEMPLATE_LABELS["equipment"]),
            "", "## Budget", "", *_items(kb.budget, TEMPLATE_LABELS["budget"]),
            "", "# 4. Event Constraints", "", *_items(kb.constraints, TEMPLATE_LABELS["constraints"]),
            "", "# 5. Participant Profiles", "",
            *_items(kb.participant_profiles, TEMPLATE_LABELS["participant_profiles"]),
            "", "# 6. Simulation Scenarios", "",
            "> 情境為模擬假設；Initial State 等欄位依文件填寫，其餘待模擬或待補。"]

    scenarios = {s.title: s for s in kb.scenarios}
    titles = DEFAULT_SCENARIOS + [t for t in scenarios if t not in DEFAULT_SCENARIOS]
    for n, title in enumerate(titles, start=1):
        fields = scenarios[title].fields if title in scenarios else []
        out += ["", f"## Scenario {n:02d}: {title}", "", *_items(fields, SCENARIO_LABELS)]

    out += ["", "# 7. Event Dependencies", "",
            "| Source Event | Triggered Event | Subsequent Impact | Final Impact | Source |",
            "|---|---|---|---|---|"]
    for d in kb.dependencies:
        out.append(f"| {_cell(d.source_event)} | {_cell(d.triggered_event)} | {_cell(d.subsequent_impact)} "
                   f"| {_cell(d.final_impact)} | {tag(d)} |")
    if not kb.dependencies:
        out.append(f"| {MISSING} | — | — | — | — |")

    out += ["", "# 8. Risk Assessment", "",
            "| Risk | Probability | Impact | Mitigation | Source |", "|---|---|---|---|---|"]
    for r in kb.risks:
        out.append(f"| {_cell(r.risk)} | {_cell(r.probability) if r.probability else '[待評估]'} "
                   f"| {_cell(r.impact) if r.impact else '[待評估]'} | {_cell(r.mitigation)} | {tag(r)} |")
    if not kb.risks:
        out.append(f"| {MISSING} | [待評估] | [待評估] | — | — |")

    out += ["", "# 9. Contingency Plans", "", *_items(kb.contingency, TEMPLATE_LABELS["contingency"]),
            "", "# 10. AI Simulation Instructions", ""]
    out += [f"{i}. {text}" for i, text in enumerate(AI_INSTRUCTIONS + EXTRA_INSTRUCTIONS, start=1)]

    out += ["", "# 11. Data Quality Issues", ""]
    out += [f"{i}. {_cell(x.description)}" + (f" [{', '.join(f'p.{p}' for p in x.pages)}]" if x.pages else "")
            for i, x in enumerate(kb.data_issues, start=1)] or ["- 未發現。"]

    out += ["", "# 12. Required Additional Data", "", "| 項目 | 用途 | 優先度 |", "|---|---|---|"]
    out += [f"| {_cell(x.item)} | {_cell(x.purpose)} | {x.priority} |" for x in kb.required_data] \
        or ["| — | — | — |"]
    return "\n".join(out) + "\n"


def _has_gaps(kb: KnowledgeBase) -> bool:
    sourced: list[Sourced] = [*kb.overview, *kb.timeline, *kb.venues, *kb.human_resources,
                              *kb.equipment, *kb.constraints]
    return bool(kb.data_issues) or any(s.status in ("missing", "unverified") for s in sourced) \
        or any(r.end is None or r.start is None for r in kb.timeline) \
        or any(v.capacity is None for v in kb.venues)

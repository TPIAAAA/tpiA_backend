"""Activity Knowledge Base 的結構化格式（所有企劃書統一轉成這個格式）。

每個值都帶 status：
- confirmed：文件明確寫出，pages + quote 指回原文
- inferred：由文件數字／名單推算，note 說明怎麼算的
- missing：文件沒有提供
- unverified：LLM 宣稱來自文件，但引文在原文中找不到（由驗證步驟標記，不是 LLM 可選的值）
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["confirmed", "inferred", "missing", "unverified"]
LLMStatus = Literal["confirmed", "inferred", "missing"]


class Sourced(BaseModel):
    status: Status = "missing"
    pages: list[int] = Field(default_factory=list)
    quote: str | None = None
    note: str | None = None  # inferred 的推算方式，或其他說明


class Item(Sourced):
    label: str
    value: str | None = None


class TimelineRow(Sourced):
    start: str | None = None  # HH:MM
    end: str | None = None    # HH:MM；文件沒寫為 None
    activity: str
    venue: str | None = None  # 只填單一場地；多場地或未寫時為 None，細節寫在 location_detail
    location_detail: str | None = None
    responsible: str | None = None  # 職務或組別，不寫個人全名


class Venue(Sourced):
    name: str
    usage: str | None = None
    capacity: int | None = None  # 同時可容納的活動數；文件沒寫為 None


class Scenario(BaseModel):
    title: str
    fields: list[Item] = Field(default_factory=list)


class Dependency(Sourced):
    source_event: str
    triggered_event: str | None = None
    subsequent_impact: str | None = None
    final_impact: str | None = None


class Risk(Sourced):
    risk: str
    probability: str | None = None  # 文件沒寫為 None（渲染成「待評估」）
    impact: str | None = None
    mitigation: str | None = None


class DataIssue(BaseModel):
    description: str
    pages: list[int] = Field(default_factory=list)


class RequiredData(BaseModel):
    item: str
    purpose: str | None = None
    priority: Literal["高", "中", "低"] = "中"


class KnowledgeBase(BaseModel):
    title: str
    overview: list[Item] = Field(default_factory=list)
    timeline: list[TimelineRow] = Field(default_factory=list)
    timeline_notes: list[Item] = Field(default_factory=list)  # 例如闖關輪替等子流程
    human_resources: list[Item] = Field(default_factory=list)
    venues: list[Venue] = Field(default_factory=list)
    equipment: list[Item] = Field(default_factory=list)
    budget: list[Item] = Field(default_factory=list)
    constraints: list[Item] = Field(default_factory=list)
    participant_profiles: list[Item] = Field(default_factory=list)
    scenarios: list[Scenario] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    contingency: list[Item] = Field(default_factory=list)
    data_issues: list[DataIssue] = Field(default_factory=list)
    required_data: list[RequiredData] = Field(default_factory=list)


# template 固定欄位：不論 LLM 有沒有填，渲染時一定會出現，沒填就是「待補」
TEMPLATE_LABELS: dict[str, list[str]] = {
    "overview": ["Event Name", "Event Date", "Event Location", "Expected Participants",
                 "Maximum Capacity", "Event Objectives"],
    "human_resources": ["Total Staff", "Registration Staff", "Event Coordinators"],
    "equipment": ["Projectors", "Microphones", "Computers"],
    "budget": ["Total Budget", "Available Budget"],
    "constraints": ["Maximum Participants", "Venue Capacity", "Fixed Schedule",
                    "Safety Requirements", "Non-negotiable Rules"],
    "participant_profiles": ["Participant Types", "Expected Attendance", "Special Requirements",
                             "Potential Behavioral Patterns"],
    "contingency": ["Emergency Contact", "Alternative Venue", "Backup Equipment",
                    "Alternative Schedule", "Emergency Procedures"],
}
SCENARIO_LABELS = ["Trigger Condition", "Initial State", "Potential Impact", "Affected Processes",
                   "Resource Changes", "Possible Actions", "Expected Outcome"]
DEFAULT_SCENARIOS = ["Event Delay", "Equipment Failure"]

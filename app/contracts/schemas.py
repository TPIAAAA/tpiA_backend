"""跨組共用的模型與 Agent 介面。更改需全組審查。"""
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, model_validator


class ResourceSpec(BaseModel):
    id: str = Field(min_length=1)
    capacity: int = Field(ge=1)


class ActivitySpec(BaseModel):
    id: str = Field(min_length=1)
    planned_start_min: float = Field(ge=0)
    duration_min: float = Field(gt=0)
    resource_id: str | None = None
    depends_on: list[str] = Field(default_factory=list)


class AgentTemplate(BaseModel):
    role: str
    count: int = Field(ge=0)
    behavior_modules: list[str] = Field(default_factory=list)


class EventSimIR(BaseModel):
    name: str
    resources: list[ResourceSpec] = Field(default_factory=list)
    activities: list[ActivitySpec] = Field(default_factory=list)
    agents: list[AgentTemplate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self):
        resource_ids = [x.id for x in self.resources]
        activity_ids = [x.id for x in self.activities]
        if len(set(resource_ids)) != len(resource_ids):
            raise ValueError("資源 id 重複")
        if len(set(activity_ids)) != len(activity_ids):
            raise ValueError("活動 id 重複")
        known_resources = set(resource_ids)
        known_activities = set(activity_ids)
        for x in self.activities:
            if x.resource_id and x.resource_id not in known_resources:
                raise ValueError(f"{x.id}: 未定義資源 {x.resource_id}")
            if x.id in x.depends_on or any(dep not in known_activities for dep in x.depends_on):
                raise ValueError(f"{x.id}: 不合法的活動依賴")
        graph = {x.id: x.depends_on for x in self.activities}
        visiting, visited = set(), set()
        def dfs(node: str):
            if node in visiting:
                raise ValueError("活動依賴有循環")
            if node in visited:
                return
            visiting.add(node)
            for other in graph[node]:
                dfs(other)
            visiting.remove(node)
            visited.add(node)
        for node in graph:
            dfs(node)
        return self


class ActionType(str, Enum):
    WAIT = "WAIT"
    MOVE = "MOVE"
    JOIN = "JOIN"
    ATTEND = "ATTEND"
    ASK = "ASK"
    REST = "REST"
    LEAVE = "LEAVE"


class AgentProfile(BaseModel):
    agent_id: str
    role: str
    goals: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    agent_id: str
    location: str | None = None
    active_goal: str | None = None
    status: str = "IDLE"
    beliefs: dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    agent_id: str
    sim_time_min: float = Field(ge=0)
    visible_areas: list[str] = Field(default_factory=list)
    perceived_waits: dict[str, float] = Field(default_factory=dict)
    messages: list[str] = Field(default_factory=list)


class ActionProposal(BaseModel):
    agent_id: str
    action_type: ActionType
    payload: dict[str, Any] = Field(default_factory=dict)


class EventLog(BaseModel):
    sequence: int
    sim_time_min: float
    event_type: str
    activity_id: str
    resource_id: str | None = None


class SimulationResult(BaseModel):
    model_name: str
    seed: int
    completed_activities: int
    total_activities: int
    makespan_min: float
    events: list[EventLog]
    delays_min: dict[str, float]
    note: str = "僅活動流程／資源示範；尚無真實 Agent 行為模型。"


class RunRequest(BaseModel):
    seed: int = 42


class ExperimentCreate(BaseModel):
    model: EventSimIR
    seed: int = 42


class ExperimentInfo(BaseModel):
    id: str
    status: str
    seed: int
    result: dict[str, Any] | None = None
    error: str | None = None

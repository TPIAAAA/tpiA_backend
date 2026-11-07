"""最小教學用 DES 引擎：排程、依賴、容量。沒有模擬個人 Agent 行為。"""
from dataclasses import dataclass, field
import heapq
import itertools
from app.contracts.schemas import EventSimIR, EventLog, SimulationResult


@dataclass(order=True)
class ScheduledEvent:
    at: float
    order: int
    kind: str = field(compare=False)
    activity_id: str = field(compare=False)


class WorldEngine:
    def run(self, ir: EventSimIR, seed: int = 42) -> SimulationResult:
        """固定模型必有固定順序；seed 保留給學生增加隨機行為。"""
        self.ir = ir
        self.time = 0.0
        self.sequence = itertools.count()
        self.events: list[ScheduledEvent] = []
        self.logs: list[EventLog] = []
        self.status = {a.id: "PENDING" for a in ir.activities}
        self.activity_by_id = {a.id: a for a in ir.activities}
        self.capacity = {r.id: r.capacity for r in ir.resources}
        self.used = {r.id: 0 for r in ir.resources}
        self.started_at: dict[str, float] = {}
        self.finished_at: dict[str, float] = {}
        for a in ir.activities:
            self.schedule(a.planned_start_min, "READY", a.id)
        while self.events:
            event = heapq.heappop(self.events)
            self.time = event.at
            if event.kind == "READY":
                self._try_start_ready()
            elif event.kind == "DONE":
                a = self.activity_by_id[event.activity_id]
                self.status[a.id] = "DONE"
                self.finished_at[a.id] = self.time
                if a.resource_id:
                    self.used[a.resource_id] -= 1
                self._log("ACTIVITY_FINISHED", a.id, a.resource_id)
                self._try_start_ready()
        if len(self.finished_at) != len(ir.activities):
            raise RuntimeError("尚有未完成活動，請檢查模型是否可執行")
        return SimulationResult(
            model_name=ir.name,
            seed=seed,
            completed_activities=len(self.finished_at),
            total_activities=len(ir.activities),
            makespan_min=max(self.finished_at.values(), default=0.0),
            events=self.logs,
            delays_min={a.id: round(self.started_at[a.id] - a.planned_start_min, 3) for a in ir.activities},
        )

    def schedule(self, at: float, kind: str, activity_id: str):
        if at < self.time:
            raise ValueError("事件不能排到過去")
        heapq.heappush(self.events, ScheduledEvent(at, next(self.sequence), kind, activity_id))

    def _try_start_ready(self):
        # 同時競爭資源者依 IR 順序服務；留給學生增加公平排程與策略。
        for a in self.ir.activities:
            if self.status[a.id] != "PENDING" or a.planned_start_min > self.time:
                continue
            if any(self.status[d] != "DONE" for d in a.depends_on):
                continue
            if a.resource_id and self.used[a.resource_id] >= self.capacity[a.resource_id]:
                continue
            if a.resource_id:
                self.used[a.resource_id] += 1
            self.status[a.id] = "RUNNING"
            self.started_at[a.id] = self.time
            self._log("ACTIVITY_STARTED", a.id, a.resource_id)
            self.schedule(self.time + a.duration_min, "DONE", a.id)

    def _log(self, event_type: str, activity_id: str, resource_id: str | None):
        self.logs.append(EventLog(sequence=len(self.logs), sim_time_min=self.time,
                                  event_type=event_type, activity_id=activity_id,
                                  resource_id=resource_id))

"""學生 D：從已完成的世界事件與統計指標提出候選風險。"""
from dataclasses import dataclass
from app.contracts.schemas import SimulationResult

@dataclass
class RiskFinding:
    risk_type: str
    supporting_event_ids: list[int]
    assumption_notes: list[str]

class RiskAnalyzer:
    def analyze(self, runs: list[SimulationResult]) -> list[RiskFinding]:
        # TODO(D): static/dynamic/emergent; do not assume correlation is causality
        raise NotImplementedError("學生 D：請自行設計風險分析與驗證")

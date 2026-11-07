"""學生 D：Baseline / Stress / Alternative / Monte Carlo。"""
from dataclasses import dataclass, field

@dataclass
class Scenario:
    name: str
    seed: int
    overrides: dict = field(default_factory=dict)
    injected_events: list[dict] = field(default_factory=list)

class ScenarioGenerator:
    def generate(self, baseline: Scenario) -> list[Scenario]:
        # TODO(D): controlled experiments + common random numbers
        raise NotImplementedError("學生 D：請自行設計情境生成策略")

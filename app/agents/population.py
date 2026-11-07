"""學生 C：synthetic population generator，與人因資料校準。"""
from app.contracts.schemas import AgentTemplate, AgentProfile

class PopulationGenerator:
    def generate(self, templates: list[AgentTemplate], seed: int) -> list[AgentProfile]:
        # TODO(C): correlated sampling; social group assignment; provenance
        raise NotImplementedError("學生 C：請自行設計合成群體模型")

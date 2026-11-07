"""學生 A：抽取結果 -> IR；不得自動把未知值冒充確定事實。"""
from app.contracts.schemas import EventSimIR
from app.documents.parser import ExtractedFact

class SimulationModelCompiler:
    def compile(self, facts: list[ExtractedFact]) -> EventSimIR:
        # TODO(A): provenance + schema validate + assumption handling
        raise NotImplementedError("學生 A：請自行設計模型編譯")

"""學生 A：統一文件抽取輸入與輸出，實作方法由學生自行研究。"""
from dataclasses import dataclass

@dataclass(frozen=True)
class EvidenceSpan:
    document_id: str
    page: int | None
    source_text: str

@dataclass
class ExtractedFact:
    field_path: str
    value: object
    source: EvidenceSpan
    status: str = "inferred"  # confirmed/inferred/estimated/missing

class DocumentParser:
    def parse(self, file_path: str) -> list[ExtractedFact]:
        # TODO(A): PDF/Word/table extraction, source pointer, prompt injection isolation
        raise NotImplementedError("學生 A：請自行實作文件解析")

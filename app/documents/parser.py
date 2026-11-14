"""學生 A：統一文件抽取輸入與輸出。

流程：``load_document``（PDF／Word／Excel／CSV／Markdown／純文字 → 文字片段與表格）
→ 一個或多個 ``FactExtractor`` → ``list[ExtractedFact]``。

每個 ``ExtractedFact`` 都必須帶 ``EvidenceSpan``，指回原文件的頁碼／表格列與原文，
讓 Compiler 與 UI 能追溯每一個數值從哪裡來。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Protocol

if TYPE_CHECKING:
    from app.documents.loaders import LoadedDocument

FACT_STATUSES = ("confirmed", "inferred", "estimated", "missing")


@dataclass(frozen=True)
class EvidenceSpan:
    document_id: str
    page: int | None
    source_text: str
    locator: str | None = None  # 例如 "table 2 row 3"、"line 5"


@dataclass
class ExtractedFact:
    """field_path 規則見 ``app.compiler.compiler``，例如 ``activities.keynote.duration_min``。"""
    field_path: str
    value: object
    source: EvidenceSpan
    status: str = "inferred"  # confirmed/inferred/estimated/missing

    def __post_init__(self):
        if self.status not in FACT_STATUSES:
            raise ValueError(f"未知的 fact status: {self.status}")


class FactExtractor(Protocol):
    def extract(self, document: "LoadedDocument") -> list[ExtractedFact]: ...


class DocumentParser:
    """組合 loader 與 extractor。預設只用決定性的規則抽取器（不呼叫 LLM）。

    要加入 LLM 抽取：``DocumentParser(extractors=[..., LLMFactExtractor(llm)])``。
    """

    def __init__(self, extractors: Iterable[FactExtractor] | None = None):
        if extractors is None:
            from app.documents.extractors import KeyValueFactExtractor, TableFactExtractor
            extractors = [KeyValueFactExtractor(), TableFactExtractor()]
        self.extractors = list(extractors)

    def parse(self, file_path: str) -> list[ExtractedFact]:
        from app.documents.loaders import load_document
        return self.parse_document(load_document(file_path))

    def parse_document(self, document: "LoadedDocument") -> list[ExtractedFact]:
        """已載入（例如 API 上傳、在記憶體中）的文件。"""
        facts: list[ExtractedFact] = []
        for extractor in self.extractors:
            facts.extend(extractor.extract(document))
        if not any(f.field_path == "name" for f in facts):
            # 最後手段：以檔名當模型名稱，標成 inferred 讓使用者確認
            from pathlib import Path
            facts.append(ExtractedFact(
                "name", Path(document.file_name).stem,
                EvidenceSpan(document.document_id, None, document.file_name, "file name"), "inferred"))
        return facts

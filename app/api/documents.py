"""學生 A：企劃書 → Activity Knowledge Base → EventSimIR 的 API（同步處理）。

- POST /api/v1/documents/knowledge  上傳企劃書，以 LLM 整理成知識庫 markdown＋JSON（約 30–60 秒）
- POST /api/v1/documents/compile    上傳知識庫 markdown（或任何支援格式），以規則編譯成 EventSimIR

compile 成功後，前端可把回傳的 ``ir`` 直接送到 ``POST /api/v1/experiments`` 執行模擬。
目前不寫入資料庫；上傳的檔案只在記憶體中處理。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from app.compiler.compiler import Assumption, CompilationError, SimulationModelCompiler
from app.documents.export import build_report
from app.documents.loaders import (MAX_FILE_BYTES, SUPPORTED_SUFFIXES, DocumentLoadError,
                                   LoadedDocument, load_bytes)
from app.documents.parser import DocumentParser
from app.knowledge.generator import generate_knowledge_base
from app.knowledge.render import render_markdown
from app.llm.adapter import PROMPT_VERSION, GeminiLLMAdapter, LLMError, StructuredLLM

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def get_llm() -> StructuredLLM:
    """可在測試中以 app.dependency_overrides 換成假的 LLM。"""
    return GeminiLLMAdapter()


class AssumptionIn(BaseModel):
    field_path: str = Field(min_length=1, examples=["resources.崙暉樓.capacity"])
    value: Any
    rationale: str = Field(min_length=1, examples=["場地組確認同時只能進行 1 個活動"])
    author: str | None = None


_ASSUMPTIONS = TypeAdapter(list[AssumptionIn])


@router.post("/knowledge", summary="企劃書 → 知識庫 markdown（呼叫 LLM）")
def build_knowledge(file: UploadFile = File(..., description=f"支援 {', '.join(SUPPORTED_SUFFIXES)}"),
                    llm: StructuredLLM = Depends(get_llm)):
    document = _load_upload(file)
    try:
        result = generate_knowledge_base(document, llm)
    except LLMError as exc:
        status = 503 if "LLM_API_KEY" in str(exc) else 502
        raise HTTPException(status, detail=f"LLM 處理失敗：{exc}") from exc

    calls = [c.__dict__ for c in getattr(llm, "calls", [])]
    return {
        "schema_version": "plan2sim.knowledge_base.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"file_name": document.file_name, "document_id": document.document_id},
        "markdown": render_markdown(result.kb, source_name=document.file_name),
        "knowledge_base": result.kb.model_dump(mode="json"),
        "verification": {"downgraded_to_unverified": result.downgraded},
        "llm": {"model": getattr(llm, "model", None), "prompt_version": PROMPT_VERSION, "calls": calls},
    }


@router.post("/compile", summary="知識庫 markdown（或其他文件）→ EventSimIR（只用規則，不呼叫 LLM）",
             responses={422: {"description": "缺值、衝突或不合法；detail.issues 列出所有問題"}})
def compile_document(file: UploadFile = File(...),
                     assumptions: str = Form("[]", description="JSON 陣列：[{field_path, value, rationale}]")):
    try:
        items = _ASSUMPTIONS.validate_json(assumptions)
        parsed = [Assumption(a.field_path, a.value, a.rationale, a.author) for a in items]
    except (ValidationError, ValueError) as exc:
        raise HTTPException(400, detail=f"assumptions 格式錯誤：{exc}") from exc

    document = _load_upload(file)
    facts = DocumentParser().parse_document(document)
    try:
        result = SimulationModelCompiler().compile_with_report(facts, parsed)
    except CompilationError as exc:
        report = build_report(document, facts, error=exc, assumptions=parsed)
        raise HTTPException(422, detail={
            "message": f"模型編譯失敗，共 {len(exc.issues)} 個問題",
            "issues": report["compilation"]["issues"],
            "report": report,
        }) from exc

    report = build_report(document, facts, result=result, assumptions=parsed)
    return {
        "ir": report["compilation"]["ir"],
        "model_hash": result.model_hash,
        "needs_review": [
            {"field_path": r.field_path, "value": r.value, "status": r.status, "rationale": r.rationale}
            for r in result.needs_review
        ],
        "warnings": report["compilation"]["warnings"],
        "report": report,
    }


def _load_upload(file: UploadFile) -> LoadedDocument:
    name = Path(file.filename or "").name
    if Path(name).suffix.lower() not in SUPPORTED_SUFFIXES:
        raise HTTPException(415, detail=f"不支援的檔案格式；支援 {', '.join(SUPPORTED_SUFFIXES)}")
    data = file.file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, detail=f"檔案超過 {MAX_FILE_BYTES // (1024 * 1024)} MB 上限")
    if not data:
        raise HTTPException(400, detail="檔案是空的")
    try:
        return load_bytes(data, name)
    except DocumentLoadError as exc:
        raise HTTPException(400, detail=str(exc)) from exc

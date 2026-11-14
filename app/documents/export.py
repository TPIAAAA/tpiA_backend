"""把一次「讀文件 → 抽取 → 編譯」的完整結果存成 JSON，供檢查、重播與之後存入資料庫。

格式（schema_version = plan2sim.extraction-report.v1）：

{
  "schema_version": ...,
  "generated_at": ISO 時間,
  "document":    {document_id, file_name, segments[{page, locator, text}], tables[...]},
  "extraction":  {facts[...], llm: {model, prompt_version, calls[...], rejections[...]} | null},
  "compilation": {status: "ok"|"failed", assumptions[...], issues[...], warnings[...],
                  ir, model_hash, resolutions[...], needs_review[field_path...]}
}

注意：內容包含文件原文（可能有個資），存放位置不可 commit。
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from app.compiler.compiler import Assumption, CompilationError, CompilationResult
from app.documents.loaders import LoadedDocument
from app.documents.parser import ExtractedFact

SCHEMA_VERSION = "plan2sim.extraction-report.v1"


def build_report(document: LoadedDocument, facts: list[ExtractedFact], *,
                 result: CompilationResult | None = None, error: CompilationError | None = None,
                 assumptions: list[Assumption] | None = None,
                 llm_extractor=None, llm_adapter=None) -> dict:
    llm = None
    if llm_extractor is not None:
        llm = {
            "model": getattr(llm_adapter, "model", None),
            "prompt_version": _prompt_version(),
            "schema_name": llm_extractor.schema_name,
            "calls": [asdict(c) for c in getattr(llm_adapter, "calls", [])],
            "rejections": [asdict(r) for r in llm_extractor.rejections],
        }

    compilation: dict = {
        "status": "ok" if result is not None else "failed",
        "assumptions": [asdict(a) for a in assumptions or []],
        "issues": [asdict(i) for i in error.issues] if error else [],
    }
    if result is not None:
        compilation.update(
            ir=result.ir.model_dump(mode="json"),
            model_hash=result.model_hash,
            resolutions=[asdict(r) for r in result.resolutions.values()],
            needs_review=[r.field_path for r in result.needs_review],
            warnings=[asdict(w) for w in result.warnings],
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "document": {
            "document_id": document.document_id,
            "file_name": document.file_name,
            "segments": [asdict(s) for s in document.segments],
            "tables": [asdict(t) for t in document.tables],
        },
        "extraction": {
            "facts": [asdict(f) for f in facts],
            "llm": llm,
        },
        "compilation": compilation,
    }


def save_report(report: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _prompt_version() -> str | None:
    try:
        from app.llm.adapter import PROMPT_VERSION
        return PROMPT_VERSION
    except ImportError:  # pragma: no cover
        return None

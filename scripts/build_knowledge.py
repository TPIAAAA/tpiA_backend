"""企劃書 → Activity Knowledge Base markdown（所有企劃書統一格式）。

用法（在專案根目錄）：
    python scripts/build_knowledge.py my_plan.pdf
        → my_plan.knowledge.md（給人看、可修改）
        → my_plan.knowledge.json（結構化資料＋驗證紀錄）

產出的 markdown 可人工修改後，直接編譯成模擬模型（不再呼叫 LLM）：
    python scripts/try_compile.py my_plan.knowledge.md --default-capacity 1

注意：會把企劃書內容送到 .env 設定的 LLM（Google Gemini）。
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from try_compile import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from app.documents.loaders import load_document  # noqa: E402
from app.knowledge.generator import generate_knowledge_base  # noqa: E402
from app.knowledge.render import render_markdown  # noqa: E402
from app.llm.adapter import PROMPT_VERSION, GeminiLLMAdapter, LLMError  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out", help="markdown 輸出路徑（預設 <檔名>.knowledge.md）")
    ap.add_argument("--overwrite", action="store_true", help="輸出檔已存在時覆蓋")
    args = ap.parse_args()

    src = Path(args.file)
    md_path = Path(args.out) if args.out else src.with_suffix(".knowledge.md")
    json_path = md_path.with_suffix(".json")
    if md_path.exists() and not args.overwrite:
        print(f"{md_path} 已存在（可能有人工修改）。要覆蓋請加 --overwrite，或用 --out 指定其他路徑。")
        return 1

    doc = load_document(src)
    adapter = GeminiLLMAdapter()
    print(f"=== 讀到 {len(doc.segments)} 行文字、{len(doc.tables)} 張表格")
    print(f"=== 呼叫 {adapter.model} 整理知識庫（文件內容會送到 Google Gemini API）…")
    try:
        result = generate_knowledge_base(doc, adapter)
    except LLMError as exc:
        print(f"失敗：{exc}")
        return 1
    for c in adapter.calls:
        print(f"    {c.model_version}  {c.latency_s}s  輸入 {c.input_tokens} tokens／輸出 {c.output_tokens} tokens")

    kb = result.kb
    md_path.write_text(render_markdown(kb, source_name=src.name), encoding="utf-8")
    json_path.write_text(json.dumps({
        "schema_version": "plan2sim.knowledge_base.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"file_name": src.name, "document_id": doc.document_id},
        "llm": {"model": adapter.model, "prompt_version": PROMPT_VERSION,
                "calls": [c.__dict__ for c in adapter.calls]},
        "verification": {"downgraded_to_unverified": result.downgraded},
        "knowledge_base": kb.model_dump(mode="json"),
        "llm_raw_output": result.raw,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    def count(items):
        from collections import Counter
        return Counter(i.status for i in items)
    sourced = [*kb.overview, *kb.timeline, *kb.venues, *kb.human_resources, *kb.equipment, *kb.budget,
               *kb.constraints, *kb.participant_profiles, *kb.contingency, *kb.timeline_notes]
    print(f"\n=== {kb.title}")
    print(f"    時程 {len(kb.timeline)} 段、場地 {len(kb.venues)} 個、情境 {len(kb.scenarios)} 個、"
          f"風險 {len(kb.risks)} 項")
    print(f"    來源標記：{dict(count(sourced))}")
    print(f"    資料不一致 {len(kb.data_issues)} 項、待補資料 {len(kb.required_data)} 項")
    if result.downgraded:
        print(f"    引文找不到、改標「待查證」{len(result.downgraded)} 項：")
        for d in result.downgraded:
            print(f"      - {d}")
    print(f"\n=== 已輸出 {md_path}、{json_path}")
    print(f"下一步：檢查／修改 {md_path.name} 後執行 python scripts/try_compile.py {md_path}")


if __name__ == "__main__":
    sys.exit(main())

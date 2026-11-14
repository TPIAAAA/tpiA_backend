"""手動測試：企劃書 → 事實 → EventSimIR → 模擬。

用法（在專案根目錄）：
    python scripts/try_compile.py my_plan.pdf                # 只用規則抽取（不連網）
    python scripts/try_compile.py my_plan.pdf --llm          # 加上 Gemini 抽取（會把文件內容送到 Google）
    python scripts/try_compile.py my_plan.pdf --llm --default-capacity 1
        # 文件沒寫場地容量時，用「每個場地同時 1 個活動」當 Assumption（會標成 assumed）
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_dotenv(path: Path):
    """簡易讀取 .env（不覆蓋已存在的環境變數），不另外安裝 python-dotenv。"""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(ROOT / ".env")

from app.compiler.compiler import Assumption, CompilationError, SimulationModelCompiler  # noqa: E402
from app.documents.extractors import (KeyValueFactExtractor, LLMFactExtractor,  # noqa: E402
                                      TableFactExtractor)
from app.documents.export import build_report, save_report  # noqa: E402
from app.documents.loaders import load_document  # noqa: E402
from app.documents.parser import DocumentParser  # noqa: E402
from app.simulation.engine import WorldEngine  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--llm", action="store_true", help="使用 Gemini 抽取（需要 .env 的 LLM_API_KEY）")
    ap.add_argument("--default-capacity", type=int, help="缺少場地容量時使用的假設值")
    ap.add_argument("--assume", action="append", default=[], metavar="FIELD=VALUE",
                    help="補缺漏的假設值，可重複，例如 --assume activities.1615_歸賦.duration_min=15")
    ap.add_argument("--json", help="另外把編譯出的 IR 單獨存成 JSON 檔")
    ap.add_argument("--save", help="完整讀取結果的 JSON 路徑（預設：<檔名>.extraction.json，放在企劃書旁邊）")
    args = ap.parse_args()

    doc = load_document(args.file)
    print(f"=== 讀到 {len(doc.segments)} 行文字、{len(doc.tables)} 張表格")

    extractors = [KeyValueFactExtractor(), TableFactExtractor()]
    llm_extractor = adapter = None
    if args.llm:
        from app.llm.adapter import GeminiLLMAdapter
        adapter = GeminiLLMAdapter()
        llm_extractor = LLMFactExtractor(adapter)
        extractors.append(llm_extractor)
        print(f"=== 呼叫 {adapter.model}（文件內容會送到 Google Gemini API）…")

    facts = DocumentParser(extractors).parse(args.file)
    if llm_extractor:
        for c in adapter.calls:
            print(f"    {c.model_version}  {c.latency_s}s  輸入 {c.input_tokens} tokens／輸出 {c.output_tokens} tokens")
    print(f"\n=== 抽出 {len(facts)} 筆事實")
    for f in facts:
        print(f"  {f.status:9} {f.field_path:45} {f.value!r}  ← p{f.source.page} {f.source.source_text[:40]}")
    if llm_extractor and llm_extractor.rejections:
        print(f"\n=== LLM 輸出被拒絕 {len(llm_extractor.rejections)} 筆")
        for r in llm_extractor.rejections:
            print(f"  {r.reason}：{json.dumps(r.raw, ensure_ascii=False)[:120]}")

    compiler = SimulationModelCompiler()
    assumptions = []
    for item in args.assume:
        path, _, raw = item.partition("=")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        assumptions.append(Assumption(path.strip(), value, "命令列 --assume 指定"))
    result, error = None, None
    try:
        result = compiler.compile_with_report(facts, assumptions)
    except CompilationError as e:
        error = e
        missing_caps = [i.field_path for i in e.issues
                        if i.code in ("missing", "marked_missing") and i.field_path.endswith(".capacity")]
        if args.default_capacity and missing_caps:
            assumptions = assumptions + [
                Assumption(p, args.default_capacity,
                           f"測試用：文件未寫容量，假設同時只容納 {args.default_capacity} 個活動")
                for p in missing_caps]
            try:
                result, error = compiler.compile_with_report(facts, assumptions), None
            except CompilationError as e2:
                error = e2

    save_path = Path(args.save) if args.save else Path(args.file).with_suffix(".extraction.json")
    report = build_report(doc, facts, result=result, error=error, assumptions=assumptions,
                          llm_extractor=llm_extractor, llm_adapter=adapter)
    print(f"\n=== 讀取結果已存到 {save_report(report, save_path)}")
    if error is not None:
        return _fail(error)

    ir = result.ir
    print(f"\n=== 編譯成功：{ir.name}（{len(ir.activities)} 個活動、{len(ir.resources)} 個資源、"
          f"{len(ir.agents)} 種角色）  {result.model_hash[:20]}…")
    for a in ir.activities:
        print(f"  {a.planned_start_min:6.0f} 分起 {a.duration_min:4.0f} 分  {a.id:20} @ {a.resource_id or '-'}"
              + (f"  依賴 {a.depends_on}" if a.depends_on else ""))
    for r in ir.resources:
        print(f"  資源 {r.id}: 容量 {r.capacity}")
    for g in ir.agents:
        print(f"  角色 {g.role}: {g.count} 人")
    print(f"\n需要人工確認：{len(result.needs_review)} 項（"
          + "、".join(f"{s} {sum(1 for x in result.needs_review if x.status == s)}"
                     for s in ("inferred", "estimated", "assumed")) + "）")
    for w in result.warnings:
        print(f"  警告 [{w.code}] {w.field_path}：{w.message}")

    sim = WorldEngine().run(ir)
    print(f"\n=== 模擬完成 {sim.completed_activities}/{sim.total_activities} 個活動，總時長 {sim.makespan_min:.0f} 分鐘")
    delayed = {k: v for k, v in sim.delays_min.items() if v > 0}
    print("有延誤的活動：", delayed or "無")
    if args.json:
        Path(args.json).write_text(ir.model_dump_json(indent=2), encoding="utf-8")
        print(f"IR 已存到 {args.json}")


def _fail(e: CompilationError):
    print(f"\n=== 編譯失敗（{len(e.issues)} 個問題）")
    for i in e.issues:
        src = f"（原文：{i.sources[0].source_text[:40]}）" if i.sources else ""
        print(f"  [{i.code}] {i.field_path}：{i.message}{src}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

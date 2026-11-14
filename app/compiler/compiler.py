"""學生 A：抽取結果 -> IR；不得自動把未知值冒充確定事實。

規則：
1. 每個欄位依 status 優先序挑值：confirmed > inferred > estimated；``missing`` 不提供值。
2. 同一優先序出現不同值 → 衝突，編譯失敗（不替使用者選）。
3. 必填欄位（name、資源容量、活動開始／時長、角色人數）沒有值時，
   只能由使用者明確提供的 ``Assumption`` 補上，否則編譯失敗並列出全部缺漏。
4. 選填欄位（活動資源、前置活動、行為模組）沒有值時用空值預設，並在報告中標示。
5. 每個 IR 欄位都留下 provenance（來源 EvidenceSpan 或 Assumption 理由），
   以及 model_hash，方便實驗重現與 UI 顯示「哪些值還需要人工確認」。

``compile()`` 維持原介面回傳 ``EventSimIR``；需要報告時用 ``compile_with_report()``。
EventSimIR 契約本身沒有修改。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.compiler.fields import (OPTIONAL_DEFAULTS, REQUIRED_FIELDS, FIELD_TYPES, FieldRef,
                                 coerce_value, make_path, parse_path)
from app.contracts.schemas import EventSimIR
from app.documents.parser import EvidenceSpan, ExtractedFact

STATUS_RANK = {"confirmed": 0, "inferred": 1, "estimated": 2}


@dataclass(frozen=True)
class Assumption:
    """人工提供的假設值：補缺漏或覆蓋衝突。rationale 必填，會進入 provenance。"""
    field_path: str
    value: object
    rationale: str
    author: str | None = None

    def __post_init__(self):
        if not self.rationale.strip():
            raise ValueError("Assumption 必須寫明理由")


@dataclass
class FieldResolution:
    field_path: str
    value: object
    origin: str  # fact / assumption / default
    status: str  # confirmed / inferred / estimated / assumed / default
    sources: list[EvidenceSpan] = field(default_factory=list)
    rationale: str | None = None


@dataclass
class CompilationIssue:
    field_path: str
    code: str  # missing / marked_missing / conflict / invalid_value / unknown_field / undefined_reference / ir_invalid / superseded / overridden
    message: str
    sources: list[EvidenceSpan] = field(default_factory=list)


class CompilationError(ValueError):
    def __init__(self, issues: list[CompilationIssue]):
        self.issues = issues
        lines = "\n".join(f"- [{i.code}] {i.field_path}: {i.message}" for i in issues)
        super().__init__(f"模型編譯失敗，共 {len(issues)} 個問題：\n{lines}")


@dataclass
class CompilationResult:
    ir: EventSimIR
    model_hash: str
    resolutions: dict[str, FieldResolution]
    warnings: list[CompilationIssue]

    @property
    def needs_review(self) -> list[FieldResolution]:
        """不是文件明確寫出的值：推論、估計、人工假設。UI 應請使用者確認。"""
        return [r for r in self.resolutions.values() if r.status in ("inferred", "estimated", "assumed")]


class SimulationModelCompiler:
    def compile(self, facts: list[ExtractedFact]) -> EventSimIR:
        return self.compile_with_report(facts).ir

    def compile_with_report(self, facts: list[ExtractedFact],
                            assumptions: list[Assumption] | None = None) -> CompilationResult:
        errors: list[CompilationIssue] = []
        warnings: list[CompilationIssue] = []

        grouped = self._group_facts(facts, errors, warnings)
        assumed = self._index_assumptions(assumptions or [], errors)

        # 實體出現順序：依 fact／assumption 第一次提到的順序，維持可重現
        entities: dict[str, dict[str, None]] = {k: {} for k in FIELD_TYPES}
        for ref in [r for r, _ in grouped.values()] + [r for r, _ in assumed.values()]:
            if ref.kind is not None:
                entities[ref.kind].setdefault(ref.entity_id, None)

        resolutions: dict[str, FieldResolution] = {}

        def resolve(ref: FieldRef, required: bool, default=None):
            path = ref.path
            ref_facts = grouped.get(path, (ref, []))[1]
            if path in assumed:
                a = assumed[path][1]
                if any(f.status != "missing" for f, _ in ref_facts):
                    warnings.append(CompilationIssue(path, "overridden",
                                                     f"文件值被人工假設覆蓋（理由：{a.rationale}）",
                                                     [f.source for f, _ in ref_facts]))
                resolutions[path] = FieldResolution(path, a.value, "assumption", "assumed",
                                                    rationale=a.rationale)
                return a.value
            picked = self._pick(path, ref_facts, errors, warnings)
            if picked is not None:
                resolutions[path] = picked
                return picked.value
            if required:
                marked = [f for f, _ in ref_facts if f.status == "missing"]
                if marked:
                    errors.append(CompilationIssue(path, "marked_missing",
                                                   "文件標示待定或無法解析，請補上 Assumption",
                                                   [f.source for f in marked]))
                elif not any(e.field_path == path for e in errors):
                    errors.append(CompilationIssue(path, "missing", "文件中找不到此必填欄位，請補上 Assumption"))
                return None
            resolutions[path] = FieldResolution(path, default, "default", "default")
            return default

        ir: dict = {"name": resolve(FieldRef(None, None, "name"), required=True)}

        # 活動先解析，才能知道被引用的資源
        activities = []
        for aid in entities["activities"]:
            item = {"id": aid}
            for attr in FIELD_TYPES["activities"]:
                item[attr] = resolve(FieldRef("activities", aid, attr),
                                     required=attr in REQUIRED_FIELDS["activities"],
                                     default=OPTIONAL_DEFAULTS["activities"].get(attr))
            activities.append(item)
            if item["resource_id"]:
                entities["resources"].setdefault(item["resource_id"], None)
            for dep in item["depends_on"] or []:
                if dep not in entities["activities"]:
                    errors.append(CompilationIssue(make_path("activities", aid, "depends_on"),
                                                   "undefined_reference", f"前置活動 {dep!r} 未在文件中定義",
                                                   self._sources(resolutions, make_path("activities", aid, "depends_on"))))

        resources = []
        for rid in entities["resources"]:
            resources.append({"id": rid, "capacity": resolve(FieldRef("resources", rid, "capacity"), required=True)})

        agents = []
        for role in entities["agents"]:
            agents.append({
                "role": role,
                "count": resolve(FieldRef("agents", role, "count"), required=True),
                "behavior_modules": resolve(FieldRef("agents", role, "behavior_modules"), required=False,
                                            default=OPTIONAL_DEFAULTS["agents"]["behavior_modules"]),
            })

        if errors:
            raise CompilationError(errors)

        ir.update(resources=resources, activities=activities, agents=agents)
        try:
            model = EventSimIR.model_validate(ir)
        except ValidationError as exc:
            raise CompilationError([
                CompilationIssue(".".join(str(p) for p in e["loc"]) or "ir", "ir_invalid", e["msg"])
                for e in exc.errors()
            ]) from exc

        return CompilationResult(ir=model, model_hash=model_hash(model),
                                 resolutions=resolutions, warnings=warnings)

    # ------------------------------------------------------------ internals

    @staticmethod
    def _group_facts(facts, errors, warnings) -> dict[str, tuple[FieldRef, list[tuple[ExtractedFact, object]]]]:
        grouped: dict[str, tuple[FieldRef, list]] = {}
        for f in facts:
            try:
                ref = parse_path(f.field_path)
            except ValueError as exc:
                warnings.append(CompilationIssue(f.field_path, "unknown_field", str(exc), [f.source]))
                continue
            value = None
            if f.status != "missing":
                try:
                    value = coerce_value(ref.value_type, f.value)
                except ValueError as exc:
                    errors.append(CompilationIssue(f.field_path, "invalid_value",
                                                   f"{exc}（取得 {f.value!r}）", [f.source]))
                    continue
            grouped.setdefault(ref.path, (ref, []))[1].append((f, value))
        return grouped

    @staticmethod
    def _index_assumptions(assumptions: list[Assumption], errors) -> dict[str, tuple[FieldRef, Assumption]]:
        out = {}
        for a in assumptions:
            try:
                ref = parse_path(a.field_path)
                value = coerce_value(ref.value_type, a.value)
            except ValueError as exc:
                errors.append(CompilationIssue(a.field_path, "invalid_value", f"Assumption：{exc}"))
                continue
            if ref.path in out:
                errors.append(CompilationIssue(ref.path, "conflict", "同一欄位有多個 Assumption"))
                continue
            out[ref.path] = (ref, Assumption(a.field_path, value, a.rationale, a.author))
        return out

    @staticmethod
    def _pick(path, ref_facts, errors, warnings) -> FieldResolution | None:
        candidates = [(f, v) for f, v in ref_facts if f.status in STATUS_RANK]
        if not candidates:
            return None
        best_rank = min(STATUS_RANK[f.status] for f, _ in candidates)
        best = [(f, v) for f, v in candidates if STATUS_RANK[f.status] == best_rank]
        distinct = {_canonical(v) for _, v in best}
        if len(distinct) > 1:
            errors.append(CompilationIssue(path, "conflict",
                                           "來源之間數值不一致：" + "、".join(sorted(distinct)) + "；請以 Assumption 指定",
                                           [f.source for f, _ in best]))
            return None
        value = best[0][1]
        lower = [(f, v) for f, v in candidates if STATUS_RANK[f.status] > best_rank and _canonical(v) != _canonical(value)]
        if lower:
            warnings.append(CompilationIssue(path, "superseded",
                                             f"較低可信度的不同數值被忽略：{', '.join(_canonical(v) for _, v in lower)}",
                                             [f.source for f, _ in lower]))
        return FieldResolution(path, value, "fact", best[0][0].status,
                               sources=_dedupe([f.source for f, _ in best]))

    @staticmethod
    def _sources(resolutions, path) -> list[EvidenceSpan]:
        r = resolutions.get(path)
        return list(r.sources) if r else []


def model_hash(model: EventSimIR) -> str:
    payload = json.dumps(model.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _dedupe(spans: list[EvidenceSpan]) -> list[EvidenceSpan]:
    return list(dict.fromkeys(spans))

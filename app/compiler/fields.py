"""ExtractedFact.field_path 的命名規則與型別轉換（Extractor 與 Compiler 共用）。

field_path 格式：
- ``name``
- ``resources.<resource_id>.capacity``
- ``activities.<activity_id>.{planned_start_min|duration_min|resource_id|depends_on}``
- ``agents.<role>.{count|behavior_modules}``

entity id 可以含有 ``.``；解析時取第一段為 kind、最後一段為屬性。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

FIELD_TYPES: dict[str, dict[str, str]] = {
    "resources": {"capacity": "int"},
    "activities": {
        "planned_start_min": "number",
        "duration_min": "number",
        "resource_id": "str",
        "depends_on": "str_list",
    },
    "agents": {"count": "int", "behavior_modules": "str_list"},
}

REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "resources": ("capacity",),
    "activities": ("planned_start_min", "duration_min"),
    "agents": ("count",),
}

# 選填欄位沒有任何來源時使用的預設值（會在報告中標成 origin="default"）
OPTIONAL_DEFAULTS: dict[str, dict[str, object]] = {
    "resources": {},
    "activities": {"resource_id": None, "depends_on": []},
    "agents": {"behavior_modules": []},
}


@dataclass(frozen=True)
class FieldRef:
    kind: str | None  # None 代表頂層欄位 name
    entity_id: str | None
    attr: str

    @property
    def path(self) -> str:
        return self.attr if self.kind is None else make_path(self.kind, self.entity_id, self.attr)

    @property
    def value_type(self) -> str:
        return "str" if self.kind is None else FIELD_TYPES[self.kind][self.attr]


def make_path(kind: str, entity_id: str, attr: str) -> str:
    return f"{kind}.{entity_id}.{attr}"


def parse_path(path: str) -> FieldRef:
    if path == "name":
        return FieldRef(None, None, "name")
    head, _, rest = path.partition(".")
    entity_id, _, attr = rest.rpartition(".")
    if head not in FIELD_TYPES or not entity_id or attr not in FIELD_TYPES[head]:
        raise ValueError(f"不合法的 field_path: {path!r}")
    return FieldRef(head, entity_id, attr)


def coerce_value(value_type: str, value: object) -> object:
    """把 fact 的值轉成 IR 需要的型別；不合法就丟 ValueError（不默默修正）。"""
    if value_type == "str":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("需要非空字串")
        return value.strip()
    if value_type == "str_list":
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)) or not all(isinstance(x, str) for x in value):
            raise ValueError("需要字串清單")
        return [x.strip() for x in value if x.strip()]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("需要數值")
    if not math.isfinite(value):
        raise ValueError("數值必須是有限值")
    if value_type == "int":
        if float(value) != int(value):
            raise ValueError("需要整數")
        return int(value)
    return float(value)

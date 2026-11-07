"""學生 A/C/E 共用的 LLM Adapter（非 digiRunner 自動整合）。"""
from typing import Protocol

class StructuredLLM(Protocol):
    def generate_json(self, purpose: str, context: dict, schema_name: str) -> dict:
        """回傳受驗證的 JSON，不可直接修改世界狀態。"""
        ...

class StudentLLMAdapter:
    def generate_json(self, purpose: str, context: dict, schema_name: str) -> dict:
        # TODO(A/C/E): prompt version, schema validation, timeout, cost, replay logging
        # 對接 digiRunner AI Gateway 前應先驗證所用開源版支援情況。
        raise NotImplementedError("請學生研究適合的模型呼叫與驗證設計")

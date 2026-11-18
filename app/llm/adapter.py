"""學生 A/C/E 共用的 LLM Adapter（非 digiRunner 自動整合）。

LLM_BASE_URL 需包含 /v1。目前透過 OpenAI 相容 API 呼叫部署在 Modal 的 Qwen 模型（見 modal_app/llm_server.py）。
"""
import json
import os
from typing import Protocol

import httpx


class StructuredLLM(Protocol):
    def generate_json(self, purpose: str, context: dict, schema_name: str) -> dict:
        """回傳受驗證的 JSON，不可直接修改世界狀態。"""
        ...


class LLMError(RuntimeError):
    pass


class StudentLLMAdapter:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        self.base_url = (base_url or os.environ.get("LLM_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.model = model or os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        # Modal cold start 需要排隊等 GPU、載入模型，至少要 600 秒
        self.timeout = timeout or float(os.environ.get("LLM_TIMEOUT_SECONDS", "600"))

    def generate_json(self, purpose: str, context: dict, schema_name: str) -> dict:
        # TODO(A/C/E): prompt version, schema validation, cost, replay logging
        if not self.base_url or not self.api_key:
            raise LLMError("未設定 LLM_BASE_URL / LLM_API_KEY")

        messages = [
            {
                "role": "system",
                "content": (
                    f"任務目的：{purpose}\n"
                    f"請只輸出一個符合 schema「{schema_name}」的 JSON 物件，不要有其他文字。"
                ),
            },
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ]
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "response_format": {"type": "json_object"},
                    "temperature": 0.2,
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"呼叫 LLM 失敗：{exc}") from exc

        content = resp.json()["choices"][0]["message"]["content"]
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM 回傳的不是合法 JSON：{content[:200]}") from exc
        if not isinstance(result, dict):
            raise LLMError("LLM 回傳的 JSON 不是物件")
        return result

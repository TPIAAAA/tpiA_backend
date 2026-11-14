import json

import httpx
import pytest

from app.documents.extractors import LLMFactExtractor
from app.documents.loaders import load_bytes
from app.llm.adapter import GeminiLLMAdapter, LLMError


def _gemini_reply(payload, finish="STOP"):
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload, ensure_ascii=False)}]},
                            "finishReason": finish}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
            "modelVersion": "gemini-test-001"}


def _adapter(handler, **kw):
    return GeminiLLMAdapter(api_key="test-key", model="gemini-test", log_dir=None,
                            client=httpx.Client(transport=httpx.MockTransport(handler)), **kw)


def test_adapter_sends_instructions_as_system_and_parses_json():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers["x-goog-api-key"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_gemini_reply({"facts": []}))

    adapter = _adapter(handler)
    out = adapter.generate_json("p", {"instructions": "RULES", "untrusted_document": ["x"]}, "s.v1")

    assert out == {"facts": []}
    assert "models/gemini-test:generateContent" in seen["url"]
    assert seen["key"] == "test-key"
    assert "RULES" in seen["body"]["systemInstruction"]["parts"][0]["text"]
    user_text = seen["body"]["contents"][0]["parts"][0]["text"]
    assert "RULES" not in user_text and "untrusted_document" in user_text
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert adapter.calls[0].input_tokens == 10 and adapter.calls[0].model_version == "gemini-test-001"


def test_adapter_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("app.llm.adapter.time.sleep", lambda s: None)
    replies = iter([httpx.Response(503, json={"error": {"message": "busy"}}),
                    httpx.Response(200, json=_gemini_reply({"ok": True}))])
    assert _adapter(lambda r: next(replies)).generate_json("p", {}, "s") == {"ok": True}


@pytest.mark.parametrize("response,message", [
    (httpx.Response(400, json={"error": {"message": "API key not valid"}}), "API key not valid"),
    (httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "not json"}]}}]}), "JSON"),
    (httpx.Response(200, json=_gemini_reply({}, finish="MAX_TOKENS")), "MAX_TOKENS"),
    (httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}), "SAFETY"),
])
def test_adapter_errors_are_explicit(response, message):
    with pytest.raises(LLMError, match=message):
        _adapter(lambda r: response).generate_json("p", {}, "s")


def test_adapter_requires_key():
    with pytest.raises(LLMError, match="LLM_API_KEY"):
        GeminiLLMAdapter(api_key="").generate_json("p", {}, "s")


def test_adapter_writes_replay_log(tmp_path):
    adapter = _adapter(lambda r: httpx.Response(200, json=_gemini_reply({"a": 1})))
    adapter.log_dir = str(tmp_path)
    adapter.generate_json("p", {"instructions": "x"}, "s")
    line = json.loads((tmp_path / "llm_calls.jsonl").read_text(encoding="utf-8"))
    assert line["response"] == {"a": 1} and line["prompt_version"]
    assert "test-key" not in json.dumps(line)


class FakeLLM:
    def __init__(self, response):
        self.response = response

    def generate_json(self, purpose, context, schema_name):
        return self.response


def test_llm_start_times_shift_to_earliest_and_quotes_may_span_lines():
    doc = load_bytes("08:00-08:25   報到   中廊\n08:25-08:45   始業式   崙暉樓   全體工作\n   人員\n".encode(), "p.txt")
    llm = FakeLLM({"facts": [
        {"field_path": "activities.0800_報到.planned_start_min", "value": 480, "status": "inferred",
         "source_ref": 0, "quote": "08:00-08:25 報到"},
        {"field_path": "activities.0825_始業式.planned_start_min", "value": 505, "status": "inferred",
         "source_ref": 1, "quote": "08:25-08:45 始業式 崙暉樓 全體工作 人員"},
    ]})
    facts = LLMFactExtractor(llm).extract(doc)
    assert [(f.field_path, f.value) for f in facts] == [
        ("activities.0800_報到.planned_start_min", 0), ("activities.0825_始業式.planned_start_min", 25)]


def test_quote_from_cell_split_across_lines_is_accepted_but_fabrication_is_not():
    doc = load_bytes("16:05-16:15   頒獎   崙暉樓   宇勝\n+   品君\n結業式\n".encode(), "p.txt")
    llm = FakeLLM({"facts": [
        {"field_path": "activities.1605_頒獎+結業式.duration_min", "value": 10, "status": "inferred",
         "source_ref": 0, "quote": "16:05-16:15 頒獎+結業式 崙暉樓"},
        {"field_path": "resources.崙暉樓.capacity", "value": 3, "status": "inferred",
         "source_ref": 0, "quote": "崙暉樓 可容納 3 場"},
    ]})
    ex = LLMFactExtractor(llm)
    facts = ex.extract(doc)
    assert [f.field_path for f in facts] == ["activities.1605_頒獎+結業式.duration_min"]
    assert len(ex.rejections) == 1


def test_filename_name_only_when_no_other_name(tmp_path):
    from app.documents.parser import DocumentParser
    p = tmp_path / "x.txt"
    p.write_text("hello", encoding="utf-8")
    llm = FakeLLM({"facts": [{"field_path": "name", "value": "營隊", "status": "inferred",
                              "source_ref": 0, "quote": "hello"}]})
    names = [f.value for f in DocumentParser([LLMFactExtractor(llm)]).parse(str(p)) if f.field_path == "name"]
    assert names == ["營隊"]


@pytest.mark.parametrize("quote,ok", [
    ("08:25-08:45 始業式 崙暉樓 全體工作人員", True),     # 「全體工作／人員」跨行
    ("09:30-10:10 時段一 各關卡教室", True),             # 「各關卡／教室」跨行
    ("08:25-08:45 ... 時段一", True),                    # 省略號
    ("08:25-08:45 始業式 大禮堂", False),                # 原文沒有「大禮堂」
    ("全體學生都要穿制服", False),                         # 捏造
])
def test_quote_check_handles_layout_wrapping(quote, ok):
    from app.documents.extractors import _quote_supported
    page = ["08:25-08:45  始業式   崙暉樓   全體工作   致詞(1分鐘)",
            "                              人員     介紹工作人員(7分鐘)",
            "09:30-10:10   時段一   各關卡   課程組   闖關順序及地點:",
            "                       教室              佩炘組(A):1 vs 2"]
    assert _quote_supported(quote, ["".join(page)]) is ok

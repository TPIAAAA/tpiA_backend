import json

import pytest
from fastapi.testclient import TestClient

from app.api.documents import get_llm
from app.llm.adapter import LLMError
from app.main import app
from tests.test_knowledge import PLAN, FakeLLM, _kb_json


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _use_llm(llm):
    app.dependency_overrides[get_llm] = lambda: llm


def test_knowledge_endpoint_returns_markdown_and_json(client):
    _use_llm(FakeLLM(_kb_json()))
    r = client.post("/api/v1/documents/knowledge",
                    files={"file": ("camp.txt", PLAN.encode(), "text/plain")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["markdown"].startswith("---\ntitle: 科學營")
    assert "# 10. AI Simulation Instructions" in body["markdown"]
    assert body["knowledge_base"]["title"] == "科學營"
    assert len(body["verification"]["downgraded_to_unverified"]) == 1
    assert body["source"]["file_name"] == "camp.txt"


def test_knowledge_then_compile_then_experiment_payload(client):
    _use_llm(FakeLLM(_kb_json()))
    md = client.post("/api/v1/documents/knowledge",
                     files={"file": ("camp.txt", PLAN.encode(), "text/plain")}).json()["markdown"]

    r = client.post("/api/v1/documents/compile", files={"file": ("camp.knowledge.md", md.encode(), "text/markdown")})
    assert r.status_code == 422
    issues = {i["field_path"] for i in r.json()["detail"]["issues"]}
    assert issues == {"activities.歸賦.duration_min", "resources.中廊.capacity", "resources.崙暉樓.capacity"}

    assumptions = [
        {"field_path": "activities.歸賦.duration_min", "value": 15, "rationale": "總召確認"},
        {"field_path": "resources.中廊.capacity", "value": 1, "rationale": "場地組確認"},
        {"field_path": "resources.崙暉樓.capacity", "value": 1, "rationale": "場地組確認"},
    ]
    r = client.post("/api/v1/documents/compile",
                    files={"file": ("camp.knowledge.md", md.encode(), "text/markdown")},
                    data={"assumptions": json.dumps(assumptions, ensure_ascii=False)})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["ir"]["activities"]) == 5
    assert body["model_hash"].startswith("sha256:")
    assert {"field_path": "resources.中廊.capacity", "value": 1, "status": "assumed",
            "rationale": "場地組確認"} in body["needs_review"]
    # IR 可直接作為 experiments 的 model（同一個 Pydantic 契約）
    from app.contracts.schemas import ExperimentCreate
    ExperimentCreate.model_validate({"model": body["ir"], "seed": 42})


@pytest.mark.parametrize("files,data,status", [
    ({"file": ("plan.pptx", b"x", "application/octet-stream")}, {}, 415),
    ({"file": ("plan.txt", b"", "text/plain")}, {}, 400),
    ({"file": ("plan.txt", b"hello", "text/plain")}, {"assumptions": "not json"}, 400),
    ({"file": ("plan.txt", b"hello", "text/plain")}, {"assumptions": '[{"field_path": "x"}]'}, 400),
])
def test_compile_rejects_bad_input(client, files, data, status):
    assert client.post("/api/v1/documents/compile", files=files, data=data).status_code == status


def test_knowledge_endpoint_reports_llm_failure(client):
    class Broken:
        def generate_json(self, *a):
            raise LLMError("Gemini API 錯誤 503：busy")
    _use_llm(Broken())
    r = client.post("/api/v1/documents/knowledge", files={"file": ("camp.txt", PLAN.encode(), "text/plain")})
    assert r.status_code == 502 and "503" in r.json()["detail"]


def test_openapi_lists_document_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/documents/knowledge" in paths and "/api/v1/documents/compile" in paths

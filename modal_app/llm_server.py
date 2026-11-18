"""在 Modal GPU 上以 vLLM 提供 Qwen 模型的 OpenAI 相容 API。

部署前（只需一次）：
    uvx modal setup
    uvx modal secret create llm-api-key LLM_API_KEY=<自己產生的一組亂數>

部署：
    uvx modal deploy modal_app/llm_server.py

測試（會叫醒容器並送一個請求）：
    uvx modal run modal_app/llm_server.py

完整說明見 docs/MODAL_LLM.md。
"""
import os

import modal

MODEL_NAME = os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
GPU = os.environ.get("LLM_GPU", "L4")  # 7B 用 L4（約 $0.8/小時）即可；14B 以上改 "L40S"、"A100-80GB" 或 "H100"
MAX_MODEL_LEN = 8192
PORT = 8000

# 部署檔在 Modal 容器裡會被重新 import，容器內沒有本機的環境變數，
# 所以把 LLM_MODEL 寫進 image，確保容器跑的模型和部署時指定的一致。
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm")
    .env({"LLM_MODEL": MODEL_NAME})
)

# 快取模型權重與 vLLM 編譯結果，避免每次 cold start 重新下載
hf_cache = modal.Volume.from_name("hf-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)

app = modal.App("tpia-llm")


@app.function(
    image=image,
    gpu=GPU,
    volumes={
        "/root/.cache/huggingface": hf_cache,
        "/root/.cache/vllm": vllm_cache,
    },
    secrets=[modal.Secret.from_name("llm-api-key")],
    scaledown_window=300,  # 閒置 5 分鐘自動關機，避免持續計費
    timeout=60 * 20,
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=PORT, startup_timeout=60 * 10)
def serve():
    import subprocess

    cmd = [
        "vllm", "serve", MODEL_NAME,
        "--served-model-name", MODEL_NAME,
        "--host", "0.0.0.0",
        "--port", str(PORT),
        "--api-key", os.environ["LLM_API_KEY"],
        "--max-model-len", str(MAX_MODEL_LEN),
    ]
    subprocess.Popen(cmd)


@app.local_entrypoint()
def smoke_test():
    """`modal run modal_app/llm_server.py`：送一個 JSON 請求確認服務正常。"""
    import json
    import urllib.request

    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise SystemExit("請先在本機設定環境變數 LLM_API_KEY（與 Modal secret 相同）")

    url = serve.get_web_url().rstrip("/") + "/v1/chat/completions"
    body = json.dumps({
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": '只回傳 JSON：{"ok": true}'}],
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    print(f"POST {url}（cold start 可能要等幾分鐘）")
    with urllib.request.urlopen(req, timeout=60 * 10) as resp:
        print(json.loads(resp.read())["choices"][0]["message"]["content"])

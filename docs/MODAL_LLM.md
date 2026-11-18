# 用 Modal 的 GPU 跑 Qwen 模型

在雲端 GPU 上架一台 Qwen 模型（`Qwen/Qwen2.5-7B-Instruct`），讓後端的 `StudentLLMAdapter`（[app/llm/adapter.py](../app/llm/adapter.py)）呼叫它。

架構：

```
FastAPI / Celery（本機 Docker） ──HTTP──▶ Modal GPU（vLLM + Qwen）
          app/llm/adapter.py                modal_app/llm_server.py
```

- 模型只在 Modal 上跑，後端的 Docker image 不需要裝 `torch` 或下載模型。
- 部署好的服務是 **OpenAI 相容 API**，也可以用 `openai` 套件或其他支援 OpenAI 格式的工具呼叫。

第一次完整做完大約 30 分鐘，大部分時間在等部署和下載模型。以下指令都在 **PowerShell** 執行，工作目錄是 `tpiA_backend/`。

## 1. 安裝 uv（只要做一次）

後面的 `uvx modal` 指令需要 uv。先檢查有沒有裝過：

```powershell
uv --version
```

有版本號就跳到步驟 2。沒有的話執行（整行一起複製）：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

裝完把 PowerShell（或 VS Code）關掉再重開，再執行一次 `uv --version` 確認。

## 2. 註冊 Modal 帳號

到 https://modal.com 註冊，可以用 GitHub 或 Google 帳號登入。免費方案每月有 $30 美元額度。預設用的 L4 GPU 大約 $0.8 美元／小時，只有在處理請求時才開機計費。

## 3. 讓這台電腦登入 Modal

```powershell
uvx modal setup
```

會打開瀏覽器，按確認授權就好。

## 4. 設定模型伺服器的密碼

沒有密碼的話，任何知道網址的人都能用你的 GPU，所以一定要設。先產生一組隨機密碼：

```powershell
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

複製印出來的那串，存進 Modal（`<你的密碼>` 換成那串，不用加角括號）：

```powershell
uvx modal secret create llm-api-key LLM_API_KEY=<你的密碼>
```

⚠️ 名稱必須是 `llm-api-key`，變數名必須是 `LLM_API_KEY`，部署檔用這兩個名字讀密碼。這組密碼等一下還要用，先記下來。

## 5. 部署模型

```powershell
$env:PYTHONIOENCODING="utf-8"
uvx modal deploy modal_app/llm_server.py
```

第一行用來避免 Windows 印出 ✓ 時出現 `UnicodeEncodeError`。第一次部署大約 5～10 分鐘，成功時最後會出現：

```
✓ Created web function serve => https://<你的帳號>--tpia-llm-serve.modal.run
✓ App deployed in ...s! 🎉
```

把這個網址複製下來（有些帳號的網址會多一段地區，照印出來的完整複製即可）。

## 6. 設定後端的 `.env`

```
LLM_BASE_URL=https://<步驟 5 的網址>/v1
LLM_API_KEY=<步驟 4 的密碼>
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct
LLM_TIMEOUT_SECONDS=600
```

[docker-compose.yml](../docker-compose.yml) 已經把這四個變數傳給 `api` 和 `worker`，改完 `.env` 重新啟動即可：

```powershell
docker compose up -d --build
```

## 7. 測試連線

**方法 A：直接打已部署的 API（建議）**

```powershell
$h = @{ Authorization = "Bearer <你的密碼>" }
$body = @{ model = "Qwen/Qwen2.5-7B-Instruct"; messages = @(@{ role = "user"; content = "你好" }) } | ConvertTo-Json -Depth 5
$r = Invoke-WebRequest -UseBasicParsing -Uri "https://<步驟 5 的網址>/v1/chat/completions" -Method Post -Headers $h `
  -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec 900
([Text.Encoding]::UTF8.GetString($r.RawContentStream.ToArray()) | ConvertFrom-Json).choices[0].message.content
```

⚠️ `<你的密碼>` 和 `<步驟 5 的網址>` 要換成實際的值（網址不含 `/v1`，例如 `https://<帳號>--tpia-llm-serve.us-east.modal.run`），直接貼範本會出現 `Invalid URI`。

> 這裡刻意不用 `Invoke-RestMethod`：Windows PowerShell 5.1 會把 UTF-8 的回應解成亂碼（像 `ä½ å¥½`），伺服器本身沒問題。

看到 `choices` 裡有模型的回答就是成功。

**方法 B：用部署檔內建的測試**

```powershell
$env:LLM_API_KEY="<你的密碼>"
uvx modal run modal_app/llm_server.py
```

印出類似 `{"ok": true}` 就代表成功。注意：`modal run` 會另外開一個**臨時**的服務來測試（網址和步驟 5 的不同），跑完就關掉。它能確認部署檔本身沒問題，但測不到步驟 5 部署的那個服務，而且每次都要重新冷啟動。

第一次呼叫要等 5～15 分鐘：排隊等 GPU、下載約 15 GB 的模型、再載入 GPU。畫面停住是正常的。模型下載後會存在 Modal Volume（`hf-cache`）裡，之後冷啟動大約 1～2 分鐘。GPU 開著的期間，每次呼叫只要幾秒。

## 8. 在程式裡呼叫

**後端（已經寫好）**：直接用 adapter，回傳的是 JSON 物件（dict）：

```python
from app.llm.adapter import StudentLLMAdapter

llm = StudentLLMAdapter()  # 讀 .env 的 LLM_* 變數
result = llm.generate_json(
    purpose="根據事件摘要產生風險評估",
    context={"event": "..."},
    schema_name="RiskAssessment",
)
```

呼叫失敗、逾時或回傳的不是合法 JSON 時，會丟出 `app.llm.adapter.LLMError`。

**其他 Python 程式**：也可以用 `openai` 套件（`pip install openai python-dotenv`）：

```python
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],  # 含 /v1
    api_key=os.environ["LLM_API_KEY"],
    timeout=600,  # 冷啟動要等好幾分鐘，預設值太短會失敗
)

response = client.chat.completions.create(
    model=os.environ["LLM_MODEL"],
    messages=[
        {"role": "system", "content": "你是一個助手。"},
        {"role": "user", "content": "你好"},
    ],
    temperature=0,
)
print(response.choices[0].message.content)
```

注意：

- **timeout 至少 600 秒**，不然第一次呼叫會在模型開機途中逾時。
- **`model` 要完全一樣**：`Qwen/Qwen2.5-7B-Instruct`。
- **長度上限**：prompt 加回應最多 8192 token（部署檔的 `MAX_MODEL_LEN`）。
- **同時請求**：一台 GPU 最多同時處理 32 個請求，超過的會排隊。

## 9. 用完記得關掉

GPU 閒置 5 分鐘就會自動關機，關機後不計費。想完全停掉服務：

```powershell
uvx modal app stop tpia-llm
```

之後要再用，重新執行步驟 5 的 deploy 就好。模型有快取，很快就能完成。

## 想改設定

設定都在 [modal_app/llm_server.py](../modal_app/llm_server.py) 最上面，改完要重新 deploy：

| 設定 | 說明 |
|---|---|
| `MODEL_NAME` | 換模型（填 Hugging Face 上的模型 ID）。換了之後 `.env` 的 `LLM_MODEL` 也要改成一樣 |
| `GPU` | 預設 `L4`。14B 以上的模型要換 `L40S`、`A100-80GB` 或 `H100`，費用也會變高 |
| `MAX_MODEL_LEN` | prompt 很長時調大，會用掉更多 GPU 記憶體 |
| `scaledown_window` | 閒置幾秒後關機（預設 300） |

`MODEL_NAME` 和 `GPU` 也可以在 deploy 前用環境變數覆蓋，不必改檔案：

```powershell
$env:LLM_MODEL="Qwen/Qwen2.5-14B-Instruct"; $env:LLM_GPU="L40S"
uvx modal deploy modal_app/llm_server.py
```

`tpia-llm`（App 名稱）、`llm-api-key`（密碼）、`hf-cache` / `vllm-cache`（快取）這些名稱只存在你自己的 Modal 帳號裡，不會和別人衝突，不用改。如果要改 secret 名稱，部署檔裡的 `modal.Secret.from_name(...)` 要跟步驟 4 一起改。

## 常見問題

| 狀況 | 原因與解法 |
|---|---|
| `HTTP 404: modal-http: invalid function call` | 模型沒有部署或已經停掉，重新執行步驟 5 |
| `HTTP 401` | 程式用的密碼和步驟 4 存的不一樣 |
| `HTTP 404`，訊息提到 model | `LLM_MODEL` 和部署的 `MODEL_NAME` 不一樣 |
| `HTTP 404`，路徑是 `/chat/completions` | `LLM_BASE_URL` 少了 `/v1` |
| `LLMError: 未設定 LLM_BASE_URL / LLM_API_KEY` | `.env` 沒填，或改完沒重新 `docker compose up -d` |
| 呼叫逾時 | timeout 太短，調到 600 秒以上；或正在排隊等 GPU |
| 等了很久都沒反應 | 用 `uvx modal app logs tpia-llm` 看進度 |
| 部署時出現 `UnicodeEncodeError` | 先執行 `$env:PYTHONIOENCODING="utf-8"` 再部署 |
| 部署時找不到 secret | 步驟 4 沒做，或 secret 名稱不是 `llm-api-key` |
| 想看額度用了多少 | Modal 網站右上角的 Usage / Billing |

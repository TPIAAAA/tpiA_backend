# Plan2Sim Backend — MySQL / FastAPI / Agent Simulation

> 獨立後端 Repository。由導師建立共用 API、模擬核心與合約；學生自行研究 Agent Decision、LLM-to-IR、風險演算法。**這是起始框架，不是已完成的模擬產品。**

## 技術堆疊

Python 3.11、FastAPI、SQLAlchemy 2、PyMySQL、**MySQL 8.4**、Redis、Celery、Pydantic、pytest。可選啟動 digiRunner Open Source 作為外部 REST API Gateway。

## 1. 本機以 Docker 啟動（推薦）

```bash
cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
docker compose up --build -d
```

服務位置：FastAPI `http://localhost:8000/docs`、Health `http://localhost:8000/api/v1/health`、MySQL `127.0.0.1:3307`（從電腦連線；容器內是 `mysql:3306`）、Redis 只在 compose 內部網路。

`.env` 的 MySQL 密碼是僅供本機使用的範例。部署之前請更換 root 與應用程式密碼。MySQL 密碼若包含 `@`、`#`、`/` 等 URL 特殊字元，需先對 DATABASE_URL 內密碼做 URL percent-encoding。若 MySQL volume 已初始化，**更改 `.env` 不會自動更改資料庫內既有帳號密碼**；須進行 SQL 變更或重建純測試資料庫。禁止將真實憑證提交 Git。

### 直接測試 API

```bash
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/simulations/demo/run \
  -H 'Content-Type: application/json' -d '{"seed":42}'
```

PowerShell：

```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:8000/api/v1/health
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/simulations/demo/run -ContentType application/json -Body '{"seed":42}'
```

### 非同步實驗

先從 `/api/v1/models/demo` 取得模型，再呼叫 `POST /api/v1/experiments`，後端以 Celery 建立 Job，結果由 `GET /api/v1/experiments/{id}` 查詢。完整請求格式見 `/docs`。

## 2. FastAPI 在本機執行、MySQL 由 Docker 提供

```bash
# 先啟動 MySQL / Redis
docker compose up -d mysql redis
python -m venv .venv
# 啟用虛擬環境後：
pip install -r requirements.txt
```

環境變數設定（密碼與本機開發設定需對應）：

```bash
export DATABASE_URL='mysql+pymysql://plan2sim:dev_change_me@127.0.0.1:3307/plan2sim?charset=utf8mb4'
export CELERY_BROKER_URL='redis://127.0.0.1:6379/0'
export CELERY_RESULT_BACKEND='redis://127.0.0.1:6379/1'
export CELERY_ALWAYS_EAGER=1  # 本機測試直接同步執行任務，不需要連接 Redis
uvicorn app.main:app --reload
```

如果要在本機使用真正的非同步 Celery Worker，需另行對本機提供 Redis 連線並將 `CELERY_ALWAYS_EAGER` 設回 `0`；完整的非同步環境建議直接使用 Docker Compose。

## 3. digiRunner 開源版整合

```bash
docker compose --profile gateway up -d digirunner
```

管理介面（依安裝版本）：`http://localhost:31080/dgrv4/login`。請按 [`docs/DIGIRUNNER.md`](docs/DIGIRUNNER.md) 在管理台**手動註冊** API Proxy，Target 使用 Docker 內部位址 `http://api:8000`。Compose 並不自動註冊路由，且 digiRunner 不執行 Simulation Workers。

## 4. 測試與 CI

```bash
pip install -r requirements.txt
DATABASE_URL='sqlite:///./test.db' CELERY_ALWAYS_EAGER=1 pytest -q tests
```

SQLite 只用於快速單元測試，**不是正式／開發資料庫**。GitHub Actions 另設 `mysql-integration` job，以 MySQL 8.4 執行測試。`.github/workflows/ci.yml` 說明實際測試環境。

## 5. Repository 內容

```text
plan2sim-backend/
├── app/
│   ├── agents/           # Agent Protocol、Policy TODO
│   ├── api/              # API routes
│   ├── compiler/         # EventSim-IR compiler TODO
│   ├── contracts/        # 共用 IR / Observation / Action
│   ├── documents/        # 文件解析 TODO
│   ├── experiments/      # Scenario TODO
│   ├── llm/              # LLM Adapter TODO
│   ├── optimization/     # 最佳化 TODO
│   ├── risks/            # 風險分析 TODO
│   ├── simulation/       # 最小 heapq world engine
│   └── workers/          # Celery
├── tests/
├── docs/
├── .github/workflows/
├── docker-compose.yml   # MySQL + Redis + API + Worker + 選用 Gateway
└── .env.example
```

## 6. 與獨立前端 Repo 串接

前端請使用獨立的 `plan2sim-frontend` repo，設定 `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`。後端預設 `CORS_ORIGINS=http://localhost:3000`。前端只透過版本化 API 存取資料；**不連 MySQL / Redis**。後端 API 規格以 `/openapi.json` 為準。跨 repo breaking change 要先溝通，詳見 [`docs/CONTRACTS.md`](docs/CONTRACTS.md)。

## 7. 教學範例限制

Demo 只有資源容量、事件與活動依賴；尚不代表真的生成 200 位具真實行為的參與者。Agent、文檔轉換、風險、最佳化等演算法為學生研究範圍。

## 8. 建立獨立 GitHub Repository

此 ZIP 是已拆分好的 **Git repository 工作目錄**，未自動建立 GitHub 遠端倉庫。解壓到自己的工作區後：

```bash
git init -b main
git add .
git commit -m "Initialize Plan2Sim backend with MySQL"
# 然後在 GitHub 建立 plan2sim-backend，依 GitHub 提供的指令設定 origin 並 push
```

**不要把 `.env`、本機資料庫或密碼加入 Git。** 資料庫 migration 與正式權限機制仍是後續開發任務，

## 9. 企劃書 → 知識庫 → 模擬模型（Document＋Compiler）

所有企劃書統一整理成 **Activity Knowledge Base** markdown，經人工檢查後再編譯成 `EventSimIR`，最後交給既有的 experiments API 模擬。

```text
企劃書（PDF／Word／Excel／CSV／Markdown／純文字）
   │  ① 以 LLM 整理（約 40–60 秒，會把文件內容送到 Google Gemini）
   ▼
<檔名>.knowledge.md   ← 統一格式，給人檢查、可直接修改
<檔名>.knowledge.json ← 結構化資料＋LLM 原始輸出＋引文驗證紀錄
   │  ② 以規則編譯（不呼叫 LLM、結果可重現）
   ▼
EventSimIR ──③──▶ POST /api/v1/experiments
```

### LLM 設定

在 `.env` 加上（真正的金鑰只放 `.env`，不可 commit）：

```bash
LLM_API_KEY=你的 Google AI Studio 金鑰
LLM_MODEL=gemini-3.5-flash
# 選填：保存每次 LLM 的輸入輸出供重播（內容含文件原文，該資料夾不可 commit）
LLM_LOG_DIR=
```

Docker Compose 會把這三個變數傳進 api／worker 容器。在 Docker 外直接執行 Python 時，需先載入 `.env`，例如 `set -a; source .env; set +a`（`scripts/` 底下的腳本會自動讀取 `.env`）。

### 命令列使用

```bash
# ① 企劃書 → 知識庫（輸出檔已存在時不會覆蓋，要覆蓋請加 --overwrite）
python scripts/build_knowledge.py my_plan.pdf

# ② 知識庫 → EventSimIR → 模擬（同時輸出 <檔名>.extraction.json）
python scripts/try_compile.py my_plan.knowledge.md \
  --assume "activities.歸賦.duration_min=15" --default-capacity 1
```

- `--assume 欄位=值`：補上文件缺少的值，可重複使用
- `--default-capacity N`：文件沒寫場地容量時，假設每個場地同時容納 N 個活動（僅供測試）
- 也可以直接對原始企劃書執行 `try_compile.py <檔案> --llm`，跳過知識庫步驟

### API

| 端點 | 用途 | 輸入（multipart/form-data） |
|---|---|---|
| `POST /api/v1/documents/knowledge` | 企劃書 → 知識庫（呼叫 LLM，約 40–60 秒） | `file` |
| `POST /api/v1/documents/compile` | 知識庫 → EventSimIR（只用規則） | `file`、選填 `assumptions`（JSON 陣列） |

```bash
# ① 產生知識庫，回應中的 markdown 欄位即為知識庫全文
curl -F "file=@my_plan.pdf" http://localhost:8000/api/v1/documents/knowledge

# ② 編譯；缺值時回傳 422，detail.issues 列出所有問題
curl -F "file=@my_plan.knowledge.md" \
     -F 'assumptions=[{"field_path":"resources.崙暉樓.capacity","value":1,"rationale":"場地組確認"}]' \
     http://localhost:8000/api/v1/documents/compile
```

- compile 成功時回傳 `ir`、`model_hash`、`needs_review`（推論／估計／人工假設，需請使用者確認）、`warnings`、`report`。
- 將 `ir` 作為 `model` 送到 `POST /api/v1/experiments` 即可執行模擬。
- 錯誤碼：
  - 415：不支援的檔案格式
  - 413：檔案超過 20 MB
  - 400：空檔或 assumptions 格式錯誤
  - 422：編譯失敗
  - 503：未設定 LLM 金鑰
  - 502：LLM 呼叫失敗
- knowledge 端點為同步處理，前端的 HTTP timeout 建議設定 120 秒以上。

### 知識庫標記

| 標記 | 意義 |
|---|---|
| `[p.N]` | 企劃書第 N 頁明確寫出（confirmed） |
| `[推算：…]` | 由文件數字或名單推算，需人工確認（inferred） |
| `[待補]` | 文件未提供；編譯時必須以 assumption 補上 |
| `[待查證]` | LLM 給的引文在原文中找不到，需人工核對 |

知識庫的時程表（`Start | End | Activity | Venue | …`）與場地表（`Venue | Usage | Capacity | …`）可直接被規則編譯器讀取。若人工修改，請保留這兩張表的表頭。

### 相關程式

```text
app/documents/   loaders（讀檔）、extractors（規則／LLM 抽取）、export（輸出 JSON）
app/knowledge/   schema（知識庫格式）、generator（LLM＋引文驗證）、render（輸出 markdown）
app/compiler/    fields（欄位路徑）、compiler（事實 → EventSimIR、缺值／衝突檢查）
app/llm/         adapter（Gemini REST、重試、token 紀錄、重播 log）
app/api/documents.py   上述兩個 API 端點
scripts/         build_knowledge.py、try_compile.py
```

### 測試

```bash
DATABASE_URL='sqlite:///./test.db' CELERY_ALWAYS_EAGER=1 pytest -q tests
```

LLM 相關測試都使用假的回應，不會呼叫 Gemini，也不需要金鑰。

### 限制與注意事項

- **LLM 整理的結果必須人工檢查。** 引文驗證只確認摘錄的原文存在，不保證表格中每一欄都和原文一致（例如負責人、人數推算）。同一份文件每次執行的結果也可能略有不同。
- PDF 只讀文字層，不支援掃描檔（沒有 OCR）。
- `EventSimIR` 一個活動只能對應一個場地，因此「多個教室同時進行的闖關輪替」目前無法模擬；擴充需經全組契約審查（ADR）。
- 上傳的文件、知識庫和假設目前都不會存進資料庫。
- 企劃書通常含個資：依 `docs/RESEARCH_GUARDRAILS.md` 第 7 點，送到外部 LLM 前須取得團隊核准；企劃書及產生的 `*.knowledge.*`、`*.extraction.json` 不可 commit。

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

**不要把 `.env`、本機資料庫或密碼加入 Git。** 資料庫 migration 與正式權限機制仍是後續開發任務。

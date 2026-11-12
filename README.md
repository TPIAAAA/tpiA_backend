# Plan2Sim Backend — 活動模擬與風險決策平台後端

> **目前狀態：研究／教學起始框架，不是已完成的 Plan2Sim 產品。**
>
> 本 repository 已打通最小的 API、資料庫、同步／非同步模擬與 CI 骨架；文件理解、模型編譯、真實 Agent 行為、情境實驗、風險分析、最佳化及決策報告仍待實作。

產品需求與長期設計以 [Plan2Sim 系統設計文件](https://docs.google.com/document/d/1-bWjf-o2V5uw3KFQVQRwwzUFUH72w_IFCWD_FKGQ6bg/edit) 為基礎。本 README 以 **repository 目前實際程式碼** 為準，將目標設計和已完成能力分開描述。

## 1. 專案目標

Plan2Sim 的完整目標是把活動企劃、時間表、場地、角色及資源資料轉換成可執行的 EventSim-IR，建立異質性 Agent 群體，執行可重現的活動模擬，並以 Baseline／Stress／Alternative 等情境比較風險與改善方案。

完整產品預期涵蓋：

- 文件匯入、結構化抽取、來源追溯與假設確認。
- EventSim-IR 編譯、靜態驗證與模型版本管理。
- 資源、時間、空間、資訊及角色行為的模擬。
- Participant、Staff、Leader 等 Agent 的異質性與局部觀察。
- Scenario、Monte Carlo、敏感度、風險與改善方案驗證。
- digiRunner API Gateway、權限、觀測、非同步工作與決策報告。

目前 repository 只完成上述目標的第一層技術骨架。請勿把 demo 結果視為真實活動預測，也不要把尚未校準的模擬頻率解讀為真實世界發生機率。

## 2. 完成度圖例

| 標記 | 定義 |
|---|---|
| ✅ 已完成 | 已有可執行程式及對應測試或明確操作路徑。 |
| 🟡 部分完成 | 已有契約、資料結構或最小流程，但未達產品需求。 |
| ⬜ 未完成 | 只有介面／TODO，或尚未建立。 |
| ⚠️ 待實測 | 已有設定或容器入口，但尚未完成端到端驗收。 |

## 3. 目前可運作的系統

### 3.1 FastAPI 應用與 API

✅ 已完成：

- FastAPI 應用啟動、CORS 設定與 `/api/v1` 路由註冊。
- Health API。
- 取得內建 demo EventSim-IR。
- 同步執行 demo 模擬。
- Project 建立與列表。
- Experiment 建立、排入 Celery、狀態與結果查詢。
- OpenAPI／Swagger UI 由 FastAPI 自動提供。

目前端點：

| Method | Path | 狀態 | 說明 |
|---|---|---:|---|
| `GET` | `/api/v1/health` | ✅ | 服務健康檢查。 |
| `GET` | `/api/v1/models/demo` | ✅ | 回傳內建的 EventSim-IR demo。 |
| `POST` | `/api/v1/simulations/demo/run` | ✅ | 同步執行教學 demo；不包含 Agent 行為。 |
| `POST` | `/api/v1/projects` | ✅ | 建立只含 `id`、`name`、`created_at` 的 Project。 |
| `GET` | `/api/v1/projects` | ✅ | 依建立時間列出 Project。 |
| `POST` | `/api/v1/experiments` | ✅ | 建立 Experiment 並呼叫 Celery task；回傳 HTTP 202。 |
| `GET` | `/api/v1/experiments/{id}` | ✅ | 查詢 `PENDING／RUNNING／DONE／FAILED` 與結果。 |

⬜ 尚未完成的主要 API：

- 文件上傳、抽取結果與來源定位。
- Assumption 編輯與核准。
- 正式 Model 編譯、版本與 validation report。
- Agent Template／Behavior Parameter 編輯。
- Scenario set、批次 run、事件重播與 KPI。
- 情境比較、Risk Finding、Recommendation 與報告匯出。
- Authentication、RBAC、project-level authorization 與 audit log。

### 3.2 EventSim-IR 與共用契約

🟡 已有的最小契約位於 `app/contracts/schemas.py`：

- `ResourceSpec`：資源 ID 與容量。
- `ActivitySpec`：預定開始時間、持續時間、資源與前置活動。
- `AgentTemplate`：角色、數量與行為模組名稱。
- `EventSimIR`：資源、活動及 Agent Template 的集合。
- `AgentProfile`、`AgentState`、`Observation`、`ActionProposal`。
- `EventLog`、`SimulationResult`、Experiment request／response。

目前 IR validator 已能拒絕：

- 重複的 resource ID 或 activity ID。
- 引用不存在的 resource。
- 引用不存在的前置 activity。
- activity 自我依賴或循環依賴。

尚未涵蓋：

- EventProject、Model／Scenario version、model hash 與 schema migration。
- 場地、通道、移動時間、可及性及空間容量圖。
- 工作窗口、持續時間分布、服務速率與資源替代規則。
- Assumption、unit、confidence、source pointer 與使用者核准狀態。
- Communication／Social Graph、完整 Action 白名單與權限規則。
- validation report、source mapping 與 model quality status。

### 3.3 WorldEngine 教學模擬

✅／🟡 `app/simulation/engine.py` 已有最小離散事件引擎：

- 使用 `heapq` 排程 `READY` 與 `DONE` 事件。
- 依模擬時間推進，不使用 wall-clock sleep。
- 檢查 activity 前置依賴。
- 依 resource capacity 決定可否開始。
- 釋放已完成 activity 使用的資源。
- 產生 `ACTIVITY_STARTED`／`ACTIVITY_FINISHED` EventLog。
- 回傳 makespan、完成數、事件與各 activity 延誤。
- 相同模型目前可得到一致的事件結果。

目前限制：

- 引擎是教學用自訂 `heapq` scheduler，尚未使用需求文件規劃的 SimPy adapter。
- `seed` 目前保留在 API／結果中，但引擎尚未使用隨機行為。
- 只有 activity、dependency、duration 與 resource capacity。
- 沒有 Authoritative World State 的完整 entity／space／message／belief 狀態。
- 沒有移動、排隊服務率、取消、恢復流程、外部事件注入或空間路徑。
- Agent 尚未進入 WorldEngine 的事件循環；demo 的 200 位 participant 只存在於 IR metadata。
- EventLog 尚未持久化為可重播的 run event stream。

### 3.4 Agent 與人因行為

🟡 已完成契約骨架：

- `AgentPolicy` Protocol。
- `NoOpPolicy` 測試政策，只回傳 `WAIT`。
- `AgentProfile`、`AgentState`、`Observation` 與 `ActionProposal`。
- `ActionValidator` 可拒絕 action／state 的 agent ID 不一致。
- Participant、Staff、Population Generator 的模組位置已建立。

⬜ 尚未完成：

- ParticipantPolicy 與 StaffPolicy 的實際決策策略。
- Synthetic Population 與相關參數抽樣。
- Agent 的 Goal、Belief、局部 Observation、動態狀態與可行行動生成。
- 群組、Social Graph、Communication Graph 與資訊延遲／誤解。
- 抵達、導航、等待、場次選擇、求助、休息及公告反應等行為模組。
- Agent action 與 WorldEngine 的 validate／execute／state update 閉環。
- 參數資料來源、微觀校準、消融實驗、公平性與無障礙驗證。

### 3.5 MySQL 與資料持久化

✅ 已完成：

- SQLAlchemy 2 + PyMySQL 連線設定。
- MySQL idle connection 的 `pool_pre_ping` 與 `pool_recycle=3600`。
- `Project` table。
- `Experiment` table，保存 seed、model JSON、result JSON、status 與 error。
- MySQL 8.4 Docker service 與 named volume。
- 測試中檢查 MySQL dialect DDL 及 JSON round-trip。

🟡／⬜ 尚未完成：

- 目前用 `Base.metadata.create_all()` 建表，尚未導入 Alembic migration。
- 沒有 owner、permission、document、extraction、assumption、model、agent template、scenario、run、event log、metric、risk、recommendation 等正式資料表。
- 沒有 Object Storage／本機檔案儲存層保存原始文件與大型事件紀錄。
- 沒有資料保留期限、備份、加密、租戶隔離與刪除流程。
- 需求文件建議 PostgreSQL；本 repository 已透過 ADR 選擇 MySQL 8.4。若要改回 PostgreSQL，需先做 ADR、migration 與相容性測試。

### 3.6 Redis、Celery 與非同步 Experiment

✅ 已完成的最小流程：

1. `POST /api/v1/experiments` 將模型與 seed 寫入 MySQL。
2. API 呼叫 `run_experiment.delay(experiment_id)`。
3. Redis 作為 Celery broker／result backend。
4. Worker 將狀態改為 `RUNNING`。
5. Worker 驗證 EventSim-IR 並執行 `WorldEngine`。
6. 成功時寫入 `DONE` 與 result JSON；例外時寫入 `FAILED` 與 error。

⬜ 尚未完成：

- idempotency key、重試上限、dead-letter／失敗任務管理。
- 任務取消、逾時、priority、resource quota 與不同專案隔離。
- 批次情境、Monte Carlo、worker 水平擴充與 queue routing。
- run-level table、progress、event stream、metrics 與 tracing。
- API／job／run 的 correlation ID。

## 4. 現況架構

```mermaid
flowchart LR
    Client[前端／curl／OpenAPI Client]
    Gateway[digiRunner<br/>選用且需手動註冊]
    API[FastAPI API]
    Redis[(Redis<br/>Celery broker/result)]
    Worker[Celery Worker]
    Engine[WorldEngine<br/>EventSim-IR]
    MySQL[(MySQL 8.4<br/>Project/Experiment)]
    Stubs[研究擴充點<br/>Document/LLM/Agent/Risk/Optimization]

    Client -->|REST /api/v1| API
    Client -. optional proxy .-> Gateway
    Gateway -. manual route .-> API
    API -->|同步 demo| Engine
    API -->|Project/Experiment CRUD| MySQL
    API -. enqueue .-> Redis
    Redis -. Celery task .-> Worker
    Worker --> Engine
    Worker -->|狀態與結果| MySQL
    Stubs -. 未來整合／目前未接入 .-> Engine
```

重要邊界：

- 獨立前端只能透過 FastAPI／Gateway 存取後端，不直接連 MySQL 或 Redis。
- digiRunner 是 API Gateway，不是 database、queue、Agent runtime 或 WorldEngine。
- API 與 Worker 共用同一份 EventSim-IR／SimulationResult 契約及 WorldEngine 程式碼。
- 研究模組目前多為介面或 `NotImplementedError`，不在 demo 的執行路徑上。

## 5. 對照完整需求的模組進度

| 模組 | 狀態 | 現在已有 | 主要缺口 |
|---|---:|---|---|
| M01 Document Ingestion | ⬜ | `DocumentParser` 與 evidence dataclass 的位置。 | PDF／Word／Excel 上傳、解析、表格／頁碼、檔案雜湊與版本。 |
| M02 Document Understanding | ⬜ | `StructuredLLM`／`StudentLLMAdapter` 介面。 | LLM provider、schema extraction、prompt isolation、validation、cost／trace。 |
| M03 Assumption & Provenance | 🟡 | `EvidenceSpan`、`ExtractedFact.status`。 | 持久化、source pointer、confidence、approved status、UI 與版本。 |
| M04 Model Compiler | 🟡 | 最小 EventSim-IR Pydantic schema。 | `SimulationModelCompiler.compile()`、完整 IR、source mapping、model hash。 |
| M05 Model Validator | 🟡 | ID、resource reference、dependency、cycle 驗證。 | 空間、時序窗口、排班、權限、單位、缺漏與可執行性報告。 |
| M06 Agent Configuration | 🟡 | Agent contracts、NoOpPolicy、模組骨架。 | population、角色政策、行為模組、群組／社交／局部資訊。 |
| M07 World Simulation | 🟡 | heapq DES、activity dependency、capacity、EventLog。 | SimPy adapter、Agent loop、空間、訊息、完整世界狀態與重播。 |
| M08 Communication & Social | ⬜ | 契約文件中的設計原則。 | Message Engine、Communication Graph、Social Graph、傳播延遲。 |
| M09 Scenario & Experiment | 🟡 | 單一模型／seed 的 Celery Experiment；`Scenario` dataclass。 | Baseline／Stress／Alternative、批次、Monte Carlo、CRN、敏感度。 |
| M10 Risk & Causal Analysis | ⬜ | `RiskFinding`／`RiskAnalyzer` 骨架。 | KPI、風險規則、事件鏈、反事實驗證、統計與 evidence refs。 |
| M11 Optimization | ⬜ | `ImprovementProposal`／`ResourceOptimizer` 骨架。 | OR-Tools／constraint search、Pareto 比較、配對重新模擬。 |
| M12 Dashboard & Export | ⬜ | FastAPI `/docs`；前端為獨立 repository。 | Workspace、Inspector、Builder、Replay、Risk Dashboard、報告匯出。 |

## 6. digiRunner 整合狀態

🟡 已有：

- Compose 的 `gateway` profile 與 digiRunner Open Source image。
- 管理介面 port `127.0.0.1:31080`。
- `docs/DIGIRUNNER.md` 的手動 API 註冊流程。
- FastAPI health、demo model 與 experiment API 可作為代理目標。

⚠️ 尚未完成端到端驗收：

- Compose 不會自動建立 Proxy Path。
- 尚未證明 Gateway health proxy 已成功。
- API enable／disable、Auth／API key、RBAC、監控、correlation ID 尚未驗收。
- Rate limit、timeout、SSE／WebSocket 及 upload size 需依固定 image tag 實測。
- AI Gateway 是否能在選定的開源版本使用仍待核實。
- 尚未完成需求文件 G1–G7 的 Feature Verification Matrix。

啟動 Gateway：

```bash
docker compose --profile gateway up -d digirunner
```

管理介面通常位於 `http://localhost:31080/dgrv4/login`。完成初次登入後應立即修改預設密碼，並依 `docs/DIGIRUNNER.md` 將 Target 指向 Docker network 內的 `http://api:8000`。

## 7. 快速啟動

### 7.1 完整 Docker Compose

需求：Docker Desktop／Docker Engine 與 Compose plugin。

```bash
cp .env.example .env
docker compose up --build -d
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

服務位置：

| 服務 | 位址 | 備註 |
|---|---|---|
| FastAPI Swagger | `http://localhost:8000/docs` | API 文件與手動測試。 |
| FastAPI Health | `http://localhost:8000/api/v1/health` | 宿主機可直接存取。 |
| MySQL | `127.0.0.1:3307` | 宿主機連線；容器內使用 `mysql:3306`。 |
| Redis | compose internal network | 預設不映射宿主機 port。 |
| digiRunner | `http://localhost:31080/dgrv4/login` | 只有 `gateway` profile 啟動時提供。 |

快速檢查：

```bash
curl http://localhost:8000/api/v1/health
curl -X POST http://localhost:8000/api/v1/simulations/demo/run \
  -H 'Content-Type: application/json' \
  -d '{"seed":42}'
```

PowerShell：

```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:8000/api/v1/health
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/v1/simulations/demo/run `
  -ContentType application/json `
  -Body '{"seed":42}'
```

### 7.2 FastAPI 在本機、MySQL／Redis 在 Docker

```bash
docker compose up -d mysql redis
python -m venv .venv
# 啟用虛擬環境後
pip install -r requirements.txt
```

設定環境變數：

```bash
export DATABASE_URL='mysql+pymysql://plan2sim:dev_change_me@127.0.0.1:3307/plan2sim?charset=utf8mb4'
export CELERY_BROKER_URL='redis://127.0.0.1:6379/0'
export CELERY_RESULT_BACKEND='redis://127.0.0.1:6379/1'
export CELERY_ALWAYS_EAGER=1
uvicorn app.main:app --reload
```

若要在本機使用真正的非同步 Worker，需提供可連線的 Redis，將 `CELERY_ALWAYS_EAGER` 設為 `0`，並另外啟動：

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

## 8. 非同步 Experiment 範例

先取得 demo model：

```bash
curl http://localhost:8000/api/v1/models/demo
```

再把取得的模型放入 `POST /api/v1/experiments`：

```json
{
  "model": {
    "name": "example",
    "resources": [{"id": "room", "capacity": 1}],
    "activities": [
      {
        "id": "session",
        "planned_start_min": 0,
        "duration_min": 30,
        "resource_id": "room",
        "depends_on": []
      }
    ],
    "agents": []
  },
  "seed": 42
}
```

API 回傳 Experiment ID 後，以 `GET /api/v1/experiments/{id}` 輪詢。現在沒有 progress 百分比，也沒有 SSE／WebSocket 推播。

## 9. 測試與 CI

現有測試覆蓋：

- Health、demo model 與同步 demo API。
- activity dependency、resource capacity 與結果可重現性。
- EventSim-IR 循環依賴拒絕。
- Agent contract 與 NoOpPolicy。
- MySQL 8.4 DDL、connection recycle、Project persistence、Experiment JSON round-trip。

本機快速測試：

```bash
pip install -r requirements.txt
DATABASE_URL='sqlite:///./test.db' CELERY_ALWAYS_EAGER=1 pytest -q tests
```

CI 包含：

1. SQLite／Celery eager 的 unit test job。
2. MySQL 8.4 service 的 integration test job。

尚未建立的測試：

- 真實 Redis／Celery worker 端到端測試。
- digiRunner proxy／auth／rate-limit smoke test。
- 文件到 IR 的 integration／property test。
- Agent state transition、simulation invariants 與 replay test。
- Monte Carlo reproducibility、performance、load、security 與 empirical validation。

SQLite 只用於快速測試，不是開發或正式儲存方案。

## 10. 與完整設計文件的已知差異

| 項目 | 設計文件目標 | 目前 repository |
|---|---|---|
| Repository | 建議 monorepo | 前後端分為獨立 repositories。 |
| Database | PostgreSQL + Object Storage | MySQL 8.4；尚無 Object Storage。 |
| Simulation clock | SimPy 主時鐘 | 自訂 `heapq` 教學引擎。 |
| Workers | Document／Model／Simulation／Analysis／Optimization 分工 | 單一 Celery simulation task。 |
| EventSim-IR | 完整 Project／Space／Event／Behavior／Assumption | 最小 Resource／Activity／AgentTemplate。 |
| Agents | 異質性、局部資訊、社交與行為模組 | 契約、NoOpPolicy 與 TODO 骨架。 |
| Experiments | Baseline／Stress／Alternative／Monte Carlo | 單一 model + seed 執行。 |
| Risk／Optimization | KPI、風險鏈、對照驗證、OR-Tools | 介面骨架，未接入。 |
| API Gateway | 對外 API 治理、授權、觀測 | 選用容器及手動指南，未完成驗收。 |
| UI／Report | 7 個主要畫面、重播、比較與報告 | 本 repository 不含前端；後端尚無 report API。 |

這些差異不一定都是缺陷。例如 MySQL 與獨立 repositories 是目前 ADR 已採納的架構決策；若要改變，需先評估契約、migration、部署與團隊分工。

## 11. 建議開發順序

### Phase 1：完成可驗收的模型閉環

- 文件上傳與基本 PDF／Word／表格解析。
- EvidenceSpan、Assumption、source mapping 的持久化。
- `SimulationModelCompiler` 與擴充 EventSim-IR。
- validation report、model version 與 Alembic migration。
- 一份真實校園活動資料可從文件走到可執行模型。

### Phase 2：擴充 World 與 Agent

- 導入 SimPy adapter 或明確保留 heapq 引擎的 ADR。
- 建立區域圖、移動、資源取得／釋放、事件重播。
- Participant／Staff policy、Synthetic Population 與 Action Validator。
- 局部 Observation、群組與 Communication Engine。

### Phase 3：完成情境、風險與比較

- Baseline／Stress／Alternative 與 Monte Carlo batch。
- Common Random Numbers、敏感度、KPI 與 paired comparison。
- RiskFinding evidence chain 與反事實驗證。
- Constraint optimizer 與重新模擬驗證。

### Phase 4：平台治理與產品化

- digiRunner G1–G7 驗收、Auth／RBAC、correlation ID 與 tracing。
- Object Storage、資料保留、備份、取消、retry、quota。
- 前端 Model Builder、Replay、Risk Dashboard、Decision Comparison。
- 報告匯出、效能／資安／實證校準與外部驗證。

每個 Phase 的完成條件應是可重跑的測試與 demo，不是只有類別、畫面或文件存在。

## 12. Repository 結構

```text
tpiA_backend/
├── app/
│   ├── agents/           # Agent contracts、NoOpPolicy 與研究 TODO
│   ├── api/              # FastAPI routes
│   ├── compiler/         # Model Compiler 介面，尚未實作
│   ├── contracts/        # EventSim-IR、Agent、Experiment 共用 schema
│   ├── core/             # 環境設定
│   ├── documents/        # 文件 evidence dataclass 與 parser TODO
│   ├── experiments/      # Scenario dataclass 與生成 TODO
│   ├── llm/              # LLM Adapter 介面，尚未串接 provider
│   ├── optimization/     # ImprovementProposal 與 optimizer TODO
│   ├── risks/            # RiskFinding 與 analyzer TODO
│   ├── simulation/       # heapq WorldEngine、demo model、ActionValidator
│   ├── workers/          # Celery app 與 run_experiment task
│   ├── db.py             # SQLAlchemy engine、Project、Experiment
│   └── main.py           # FastAPI application entry point
├── docs/                 # 契約、ADR、研究界線、Gateway、分工與路線圖
├── tests/                # API、engine 與 MySQL tests
├── .github/workflows/    # SQLite unit + MySQL integration CI
├── docker-compose.yml    # MySQL、Redis、API、Worker、選用 digiRunner
├── Dockerfile
└── requirements.txt
```

## 13. 前端串接

前端位於獨立 repository，開發環境可設定：

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

後端預設：

```text
CORS_ORIGINS=http://localhost:3000
```

後端 OpenAPI (`/openapi.json`) 是目前跨 repository API 契約的 Source of Truth。Breaking change 需先更新契約、測試及前端，並依 `docs/DECISIONS.md` 提交 ADR。

## 14. 研究與安全界線

- 未經校準時，只能聲明「在指定模型與假設下」的結果。
- 不以性別、年齡、障礙等單一屬性推導性格、能力或行為。
- Agent／LLM 只能提出 ActionProposal，不能直接修改世界狀態或資源。
- 真實個資、企劃內部文件與密鑰不得提交 Git 或傳給未核准的模型。
- digiRunner 與應用層各自負責不同安全邊界；Gateway 不取代資料授權。
- 真實部署前必須更換 `.env` 範例密碼、使用 TLS、最小權限、密鑰輪替與映像掃描。

更多細節請閱讀：

- `docs/CONTRACTS.md`
- `docs/DECISIONS.md`
- `docs/DIGIRUNNER.md`
- `docs/RESEARCH_GUARDRAILS.md`
- `docs/ROADMAP.md`
- `docs/TEAM_HANDOFF.md`

## 15. 目前最重要的事實

現在可以展示的是：**一個有 API、MySQL、Redis/Celery、最小 EventSim-IR 與可重現 activity/resource demo 的後端骨架。**

現在還不能宣稱的是：**已能從真實企劃自動建立完整活動數位分身、模擬 200–1000 位具人因行為的 Agent、發現可信的湧現風險，或自動提出並驗證最佳改善方案。**

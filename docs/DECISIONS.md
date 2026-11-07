# Architecture Decision Records (ADR)

重大架構變更、資料契約修改、Gateway 調整均需在 PR 裡附上 ADR。

- 決策編號、日期、負責人、背景與取捨
- 受影響的端點、Schema、測試與回退計畫

## 已採納的決策

- ADR-001：前後端分為 `plan2sim-frontend` 與 `plan2sim-backend` 兩個獨立 Git repository。
- ADR-002：後端使用 MySQL 8.4 + SQLAlchemy 2 + PyMySQL；Redis 僅用於工作佇列。
- ADR-003：Agent 僅提交 ActionProposal，由 World Engine 驗證，禁止直接修改世界狀態。
- ADR-004：digiRunner 為 API Gateway，不是 World Engine；API 需依選定版本手動註冊。
- ADR-005：教學 Demo 暫採 heapq 事件時鐘；學生可透過 adapter 評估 SimPy，但須維持契約相容。
- ADR-006：跨 repo 合約由後端 FastAPI OpenAPI 作為 Source of Truth；任何破壞式修改需協調前端。

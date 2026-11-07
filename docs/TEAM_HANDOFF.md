# 五人分工與交接規則

導師先備好：兩個獨立 repo、backend docker compose、Gateway 安裝、API contracts、資料庫連線、簡單世界時計、測試框架、CI、範例 UI。

A — Document & Model Compiler：學生負責 PDF/Word extract、來源追溯、Assumption Manager、LLM-to-IR、Schema 品質；不得直接修改 B 的事件核心。

B — World / Simulation：學生負責時程/資源/空間、唯一世界狀態、Agent ActionValidator、可重播 EventLog；可導入 SimPy，但不破壞對外 API 合約。

C — Agent / Human Behavior：學生負責 Profile Sampling、ParticipantPolicy、StaffPolicy、局部觀察、Social Graph、群體及動態決策；不得讓 Agent 直接修改其他人的狀態。

D — Scenario / Risk / Optimization：學生負責 Monte Carlo、stress injection、KPI、Event Causality 候選圖、OR-Tools、成對重跑、研究實驗。

E — Frontend / Platform（跨兩個 repo）：學生負責資料與實驗操作 UI、API Client、MySQL migration、Celery operations、digiRunner API 註冊與治理、部署與監控。

所有人：維護自動化測試、每週一次整合、每個 PR 寫明如何驗收；各組不設計平行的 schema。

## PR 完成條件

- 只有自己模組的改動，跨契約需附 ADR。
- 新功能附 pytest 或前端基本測試；CI 綠燈。
- `README` 有如何啟動／測試的命令。
- 有演算法假設或行為機率時，留下 parameter source、random seed 與實驗可重現性描述。
- Review 至少 1 人，跨核心接口至少 2 人（例如 B+C）。

# 導師版：框架交付與學生開發節奏

## 導師預先完成（建議 2–4 週）

Week 1：建立兩個 Repo、Docker、MySQL、Redis、FastAPI、Next.js、digiRunner 基本容器。
Week 2：定義 EventSim-IR、Observation、ActionProposal、EventLog；跑通同步／非同步 Demo。
Week 3：建立 CI、單元測試、工單模板、README、各模組 TODO；Demo 經 Gateway 呼叫。
Week 4：五人共同 code review、確定資料與研究情境、由學生各提出第一份技術設計。

## 學生 18 個月主線

M1–M3：真實活動資料、IR 與世界模型設計，先完成有人／空間／活動多流程 PoC。
M4–M6：文件抽取與編譯連到既有 World；可完成企劃 → 模擬 → 初步 KPI。
M7–M9：異質性 Agent、局部認知、動態目標、群組互動。
M10–M12：異常情境、重複實驗、跨活動風險候選鏈、視覺化。
M13–M15：最佳化、模型校準、Baselines、消融實驗。
M16–M18：效能、部署、測試、論文與完整展示。

## 第一個 Sprint 每人可獨立領取的任務

- A：定義 2 種非排隊活動類型；實作 IR parser 模擬與 validator。
- B：讓 WorldEngine 同時管理 2 類資源與依賴關係，提供可重播事件。
- C：實作 `ParticipantPolicy` 的兩個不同決策策略，設計可比較實驗；**導師不要替他做**。
- D：建立 2 個替代 Scenario，對相同 seed 比較時程與資源結果。
- E：將 Model／Experiment API 串到 UI，完成 digiRunner Proxy API 的真實驗證。

## 設計審查（Design Review）

每位學生提交：需求問題 → 假設 → 資料格式 → 方案比較 → 風險 → 測試 → MVP 範圍。
導師主要檢查**介面、可重現性、是否能整合**，不要先指定唯一演算法。

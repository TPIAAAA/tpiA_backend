# digiRunner Open Source 整合指南

本專案把 digiRunner 放在 **外部 REST API → FastAPI** 的 Gateway 層。Gateway 本身不處理 Agent 思考、世界時計、SQL 或任務佇列。

## 起步

1. `docker compose --profile gateway up -d digirunner`
2. 開啟 `http://localhost:31080/dgrv4/login`
3. 用官方說明完成初次登入後 **立即修改預設密碼**，僅在本機開發環境使用。
4. 依官方「Registering Your First APIs」手動註冊 FastAPI 的測試代理，例如：
   - 來源路徑（Proxy Path）自行指定 `/plan2sim/api/v1/health`
   - 目標 API（Target URL）為 `http://api:8000/api/v1/health`（若在同一 Compose network）
   - method = `GET`
5. 在 Gateway 控制台確認 API 啟用、測試原路徑，並記錄實際代理 URL。
6. 再擴充到 `/api/v1/models/demo`、`/api/v1/experiments` 等路徑。

**注意：** 上面的 `/plan2sim/...` 是團隊建議的 Proxy Path，不是 digiRunner 內建路徑。不同版本的 UI 欄位／路由形式以實際安裝版本為準。Docker Compose 只負責起容器，**不會自動註冊**這些 APIs。

## Feature Verification Matrix（務必實測）

| 功能 | 最低驗收 | 狀態 |
|---|---|---|
| Gateway 起動 | 管理介面可開啟 | TODO |
| API proxy | Gateway 正確轉到 FastAPI health | TODO |
| API enable/disable | 改設定後路由行為符合預期 | TODO |
| Auth / API key | 未授權與授權請求可區分 | TODO |
| Monitoring / logs | 對應 request id 可追溯 | TODO |
| Rate limit | 應用情境下能實際驗證（若該版支援） | 待核實 |
| AI Gateway | 模型 API 代理與使用紀錄（若該版支援） | 待核實 |

## 不可混用的網路名稱

從獨立前端 repo 的 Browser 呼叫：`http://localhost:8000`（開發階段），或完成註冊及 CORS 驗證後觀察到的 Gateway 對外路由。
digiRunner 與 FastAPI 位於**後端 repo 的 Compose network**。從 digiRunner Docker 容器呼叫 FastAPI：**`http://api:8000`**，不是容器內的 `localhost:8000`。
對外公開時需要正式 HTTPS、Gateway 及應用層存取控制，並避免資料庫與 Redis 對外暴露。

## 官方來源

- 開源 repo：https://github.com/TPIsoftwareOSPO/digiRunner-Open-Source
- Docker 安裝：https://docs.tpi.dev/get-started/installation/docker
- API 註冊：https://docs.tpi.dev/get-started/registering-your-first-apis-with-digirunner

功能與授權細節依團隊固定的映像版本與官方文件實測；不要將企業版能力當成開源版已提供的能力。

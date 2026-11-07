# 共用契約 — 全組必須先看

以下 Python 模型在 `app/contracts/schemas.py`，API 文件也會在 `/docs` 自動生成。

## EventSimIR

- `resources`: `ResourceSpec(id,capacity)`
- `activities`: `ActivitySpec(id,planned_start_min,duration_min,resource_id?,depends_on[])`
- `agents`: `AgentTemplate(role,count,behavior_modules[])`
- `validate_ir()` 靜態拒絕未定義資源、前置活動及循環依賴。

## Agent contract

```python
class AgentPolicy(Protocol):
    def decide(self, profile: AgentProfile, state: AgentState,
               observation: Observation) -> ActionProposal: ...
```

`Observation` 只放 Agent 有權知道的資訊；`ActionProposal` 不能直接修改 `WorldState`。

### 不應隨意變更

- `agent_id`, `sim_time_min`, `action_type`, `payload`
- `resource_id`, `activity_id`, `event_type`
- `experiment_id`, `status`, `result`

需要修改時請提出 PR + ADR，並通知 A/B/C/D/E 進行相容性檢查。

## 最小驗收

1. Demo IR 有三種以上活動、兩種以上資源。
2. 未定義的資源、循環依賴不能通過驗證。
3. 同時只有有限容量的活動能佔用資源。
4. 同模型相同 seed 的 demo 事件序列可重現。
5. AgentPolicy 的輸入與輸出需通過 Pydantic 型別驗證。

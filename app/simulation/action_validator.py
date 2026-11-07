"""World 入口保護：學生 B 後續擴充資源、動線、權限與狀態檢查。"""
from app.contracts.schemas import ActionProposal, AgentState

class ActionValidator:
    def validate(self, action: ActionProposal, state: AgentState) -> bool:
        if action.agent_id != state.agent_id:
            return False
        # TODO(B): available resources, destination accessibility, task preconditions
        # NOTE: demo 目前未接到複雜 Agent action 執行流程。
        return True

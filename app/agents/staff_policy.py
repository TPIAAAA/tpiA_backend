"""學生 C：工作人員 SOP、權限、調度與通訊。"""
from app.contracts.schemas import AgentProfile, AgentState, Observation, ActionProposal

class StaffPolicy:
    def decide(self, profile: AgentProfile, state: AgentState, observation: Observation) -> ActionProposal:
        # TODO(C): SOP / finite-state machine / delegation constraints
        raise NotImplementedError("學生 C：請自行設計工作人員行為")

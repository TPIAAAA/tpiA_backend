"""AgentPolicy 最小契約，供學生自由設計決策演算法。"""
from typing import Protocol
from app.contracts.schemas import AgentProfile, AgentState, Observation, ActionProposal, ActionType


class AgentPolicy(Protocol):
    def decide(self, profile: AgentProfile, state: AgentState, observation: Observation) -> ActionProposal:
        """只提出行動，不得自行更改 World 的權威狀態。"""
        ...


class NoOpPolicy:
    """僅供測試管線，不代表真實參與者行為。"""
    def decide(self, profile: AgentProfile, state: AgentState, observation: Observation) -> ActionProposal:
        return ActionProposal(agent_id=profile.agent_id, action_type=ActionType.WAIT)

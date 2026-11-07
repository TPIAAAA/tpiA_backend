"""學生 C 的研究起點。導師刻意不實作行為細節。"""
from app.contracts.schemas import AgentProfile, AgentState, Observation, ActionProposal


class ParticipantPolicy:
    def decide(self, profile: AgentProfile, state: AgentState, observation: Observation) -> ActionProposal:
        # TODO(C): 加入異質性偏好、局部資訊、動態目標、社會互動等。
        # TODO(C): 比較 FSM / utility-based / probabilistic / optional LLM。
        # TODO(C): 每次決策須可追溯並使用個別隨機種子。
        raise NotImplementedError("請由 Agent 研究成員實作")

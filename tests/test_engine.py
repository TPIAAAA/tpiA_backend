import pytest
from pydantic import ValidationError
from app.simulation.examples import demo_model
from app.simulation.engine import WorldEngine
from app.contracts.schemas import EventSimIR, AgentProfile, AgentState, Observation, ActionType
from app.agents.base import NoOpPolicy


def test_demo_runs_all_activities_and_dependencies():
    result = WorldEngine().run(demo_model())
    assert result.completed_activities == result.total_activities == 4
    assert result.delays_min["keynote"] >= 5
    assert result.delays_min["workshop_A"] >= 10
    assert len(result.events) == 8


def test_same_input_repeatable():
    a = WorldEngine().run(demo_model(), seed=42)
    b = WorldEngine().run(demo_model(), seed=42)
    assert a.model_dump() == b.model_dump()


def test_resource_capacity_one_serializes_events():
    ir = EventSimIR.model_validate({
        "name": "single-room", "resources": [{"id": "room", "capacity": 1}],
        "activities": [
            {"id": "A", "planned_start_min": 0, "duration_min": 5, "resource_id": "room"},
            {"id": "B", "planned_start_min": 0, "duration_min": 3, "resource_id": "room"},
        ],
    })
    result = WorldEngine().run(ir)
    assert result.delays_min["B"] == 5
    assert result.makespan_min == 8


def test_invalid_ir_rejected():
    with pytest.raises(ValidationError):
        EventSimIR.model_validate({"name": "bad", "activities": [
            {"id": "A", "planned_start_min": 0, "duration_min": 1,
             "depends_on": ["B"]},
            {"id": "B", "planned_start_min": 0, "duration_min": 1,
             "depends_on": ["A"]},
        ]})


def test_agent_contract_is_separate():
    profile = AgentProfile(agent_id="p1", role="participant")
    state = AgentState(agent_id="p1")
    observation = Observation(agent_id="p1", sim_time_min=0)
    proposal = NoOpPolicy().decide(profile, state, observation)
    assert proposal.action_type == ActionType.WAIT

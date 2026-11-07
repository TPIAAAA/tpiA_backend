from app.contracts.schemas import EventSimIR


def demo_model() -> EventSimIR:
    return EventSimIR.model_validate({
        "name": "校園交流日（教學示範，不含真人 Agent）",
        "resources": [
            {"id": "registration_desks", "capacity": 2},
            {"id": "main_hall", "capacity": 1},
            {"id": "classrooms", "capacity": 2},
        ],
        "activities": [
            {"id": "checkin", "planned_start_min": 0, "duration_min": 20, "resource_id": "registration_desks"},
            {"id": "keynote", "planned_start_min": 15, "duration_min": 30,
             "resource_id": "main_hall", "depends_on": ["checkin"]},
            {"id": "workshop_A", "planned_start_min": 40, "duration_min": 25,
             "resource_id": "classrooms", "depends_on": ["keynote"]},
            {"id": "workshop_B", "planned_start_min": 40, "duration_min": 20,
             "resource_id": "classrooms", "depends_on": ["keynote"]},
        ],
        "agents": [
            {"role": "participant", "count": 200, "behavior_modules": ["arrival", "navigation", "attendance"]},
            {"role": "staff", "count": 8, "behavior_modules": ["assignment", "service"]},
        ],
    })

from app.workers.celery_app import celery_app
from app.db import SessionLocal, Experiment, init_db
from app.contracts.schemas import EventSimIR
from app.simulation.engine import WorldEngine


@celery_app.task(name="run_experiment")
def run_experiment(experiment_id: str) -> None:
    init_db()
    with SessionLocal() as db:
        exp = db.get(Experiment, experiment_id)
        if exp is None:
            return
        exp.status = "RUNNING"
        db.commit()
        try:
            model = EventSimIR.model_validate(exp.model_json)
            result = WorldEngine().run(model, seed=exp.seed)
            exp.result_json = result.model_dump(mode="json")
            exp.status = "DONE"
        except Exception as exc:
            exp.status = "FAILED"
            exp.error = f"{type(exc).__name__}: {exc}"
        db.commit()

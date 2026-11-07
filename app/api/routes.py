from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db import get_db, Project, Experiment
from app.contracts.schemas import (EventSimIR, RunRequest, SimulationResult,
                                   ExperimentCreate, ExperimentInfo)
from app.simulation.examples import demo_model
from app.simulation.engine import WorldEngine
from app.workers.tasks import run_experiment

router = APIRouter(prefix="/api/v1")


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


@router.get("/health")
def health():
    return {"status": "ok", "service": "plan2sim-api"}


@router.get("/models/demo", response_model=EventSimIR)
def model_demo():
    return demo_model()


@router.post("/simulations/demo/run", response_model=SimulationResult)
def run_demo(req: RunRequest):
    """同步的教學 smoke test。不包括 Agent 行為。"""
    return WorldEngine().run(demo_model(), seed=req.seed)


@router.post("/projects", status_code=201)
def create_project(req: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(id=str(uuid4()), name=req.name)
    db.add(p)
    db.commit()
    return {"id": p.id, "name": p.name}


@router.get("/projects")
def list_projects(db: Session = Depends(get_db)):
    return [{"id": x.id, "name": x.name} for x in db.query(Project).order_by(Project.created_at.desc()).all()]


@router.post("/experiments", response_model=ExperimentInfo, status_code=202)
def create_experiment(req: ExperimentCreate, db: Session = Depends(get_db)):
    exp = Experiment(id=str(uuid4()), seed=req.seed, status="PENDING",
                     model_json=req.model.model_dump(mode="json"))
    db.add(exp)
    db.commit()
    try:
        run_experiment.delay(exp.id)
    except Exception as exc:
        exp.status = "FAILED"
        exp.error = f"Queue unavailable: {type(exc).__name__}"
        db.commit()
        raise HTTPException(status_code=503, detail="任務佇列不可用") from exc
    db.refresh(exp)
    return ExperimentInfo(id=exp.id, status=exp.status, seed=exp.seed,
                          result=exp.result_json, error=exp.error)


@router.get("/experiments/{experiment_id}", response_model=ExperimentInfo)
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    exp = db.get(Experiment, experiment_id)
    if not exp:
        raise HTTPException(404, detail="Experiment not found")
    return ExperimentInfo(id=exp.id, status=exp.status, seed=exp.seed,
                          result=exp.result_json, error=exp.error)

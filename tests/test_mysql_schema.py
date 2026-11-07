from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql
from app.db import Project, Experiment, engine


def test_models_compile_for_mysql_84():
    project_ddl = str(CreateTable(Project.__table__).compile(dialect=mysql.dialect()))
    experiment_ddl = str(CreateTable(Experiment.__table__).compile(dialect=mysql.dialect()))
    assert "projects" in project_ddl
    assert "experiments" in experiment_ddl
    assert "JSON" in experiment_ddl


def test_connection_has_recycling_enabled():
    assert engine.pool._recycle == 3600


def test_project_can_be_saved_and_reloaded():
    from uuid import uuid4
    from app.db import SessionLocal, init_db

    init_db()
    project_id = str(uuid4())
    with SessionLocal() as db:
        db.add(Project(id=project_id, name="測試活動"))
        db.commit()
    with SessionLocal() as db:
        loaded = db.get(Project, project_id)
        assert loaded is not None
        assert loaded.name == "測試活動"


def test_experiment_json_roundtrip():
    from uuid import uuid4
    from app.db import SessionLocal, init_db

    init_db()
    exp_id = str(uuid4())
    ir = {"name": "迎新模擬", "agents": [{"role": "participant", "count": 12}]}
    with SessionLocal() as db:
        db.add(Experiment(id=exp_id, seed=42, status="PENDING", model_json=ir))
        db.commit()
    with SessionLocal() as db:
        loaded = db.get(Experiment, exp_id)
        assert loaded is not None
        assert loaded.model_json == ir

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_demo():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        model = client.get("/api/v1/models/demo")
        assert model.status_code == 200
        run = client.post("/api/v1/simulations/demo/run", json={"seed": 42})
        assert run.status_code == 200
        assert run.json()["completed_activities"] == 4

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_health_check_reports_service_and_environment() -> None:
    app = create_app(Settings(environment="test", _env_file=None))

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test"}

import asyncio

import httpx

from app.config import Settings
from app.main import create_app


def test_health_check_reports_service_and_environment() -> None:
    app = create_app(Settings(environment="test", _env_file=None))
    transport = httpx.ASGITransport(app=app)

    async def request_health() -> httpx.Response:
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test"}

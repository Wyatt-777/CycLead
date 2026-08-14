"""Local FastAPI application factory."""

from fastapi import FastAPI

from app import __version__
from app.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API shell without embedding discovery business logic in routes."""

    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="CycleLead AI",
        version=__version__,
        description="Evidence-first bicycle-industry lead discovery MVP.",
    )

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        """Report service availability and the active local environment."""

        return {"status": "ok", "environment": resolved_settings.environment}

    return app


app = create_app()

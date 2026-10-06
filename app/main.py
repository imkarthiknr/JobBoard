"""Application factory."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_settings
from app.web.routes import router as web_router
from app.web.routes import templates


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.project_title,
        version=settings.project_version,
        description="Post and discover jobs. REST API + server-rendered web UI.",
    )

    app.mount(
        "/static", StaticFiles(directory=Path(__file__).parent / "web" / "static"), name="static"
    )
    app.include_router(api_router)
    app.include_router(web_router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(StarletteHTTPException)
    async def html_errors_for_web(request: Request, exc: StarletteHTTPException):
        """JSON errors for the API, friendly HTML pages for the web UI."""
        path = request.url.path
        if path.startswith(("/api", "/docs", "/openapi", "/static", "/health")):
            return await http_exception_handler(request, exc)
        return templates.TemplateResponse(
            request, "error.html", {"user": None, "status": exc.status_code}, exc.status_code
        )

    return app


app = create_app()

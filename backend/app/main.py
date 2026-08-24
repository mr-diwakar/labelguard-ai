"""LabelGuard AI backend entry point."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import health
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, error_payload
from app.core.logging_config import configure_logging, get_logger
from app.core.request_logging import RequestLoggingMiddleware
from app.database.connection import dispose_engine

logger = get_logger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("stage=startup")
    yield
    dispose_engine()
    logger.info("stage=shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Builds the application. Accepting settings keeps tests able to run against
    an explicit configuration instead of whatever the environment happens to be.
    """
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        description="AI-assisted Legal Metrology compliance inspection platform.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings

    app.add_middleware(RequestLoggingMiddleware)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    _register_exception_handlers(app)

    # Unprefixed copy for process supervisors and load balancers; clients use the
    # versioned route so the probe never breaks when the API version changes.
    app.include_router(health.router, tags=["health"])
    app.include_router(api_router)

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        logger.warning("stage=error code=%s status=%s", exc.code, exc.status_code)
        return JSONResponse(status_code=exc.status_code, content=error_payload(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = {
            "errors": [
                {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]} for error in exc.errors()
            ]
        }
        logger.warning("stage=error code=VALIDATION_ERROR status=422")
        return JSONResponse(
            status_code=422,
            content=error_payload("VALIDATION_ERROR", "The request could not be validated.", details),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
        message = "The requested resource was not found." if exc.status_code == 404 else "The request could not be completed."
        logger.warning("stage=error code=%s status=%s", code, exc.status_code)
        return JSONResponse(status_code=exc.status_code, content=error_payload(code, message))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        # The exception object is logged here only. The client never sees it.
        logger.exception("stage=error code=INTERNAL_ERROR status=500")
        return JSONResponse(
            status_code=500,
            content=error_payload("INTERNAL_ERROR", "An unexpected error occurred. The request was not processed."),
        )


app = create_app()


if __name__ == "__main__":
    import uvicorn

    runtime_settings = get_settings()

    uvicorn.run(
        "app.main:app",
        host=runtime_settings.host,
        port=runtime_settings.port,
        reload=runtime_settings.is_development,
    )

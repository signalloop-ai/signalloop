from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from signalloop_api.ai import router as ai_router
from signalloop_api.attempts import router as attempts_router
from signalloop_api.config import settings
from signalloop_api.rate_limit import RateLimitMiddleware
from signalloop_api.reports import router as reports_router
from signalloop_api.submissions import router as submissions_router


def create_app() -> FastAPI:
    app = FastAPI(title="SignalLoop API", version="0.1.0")
    app.add_middleware(
        RateLimitMiddleware,
        enabled=settings.rate_limit_enabled,
        max_requests=settings.rate_limit_per_minute,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Request validation failed",
                "errors": jsonable_encoder(exc.errors()),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Exception handlers return responses directly, bypassing middleware.
        # Manually add CORS headers so browsers can read the 500 error body
        # instead of seeing a CORS failure that obscures the real problem.
        origin = request.headers.get("origin")
        headers: dict[str, str] = {}
        if origin and origin in settings.cors_origins:
            headers["access-control-allow-origin"] = origin
            headers["vary"] = "Origin"
        return JSONResponse(
            status_code=500,
            content={"detail": "Unexpected server error"},
            headers=headers if headers else None,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(attempts_router)
    app.include_router(ai_router)
    app.include_router(submissions_router)
    app.include_router(reports_router)

    return app


app = create_app()

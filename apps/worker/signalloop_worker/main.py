from os import getenv
from tempfile import TemporaryDirectory

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from signalloop_worker.runner import run_hidden_tests_in_workspace, run_public_tests_in_workspace
from signalloop_worker.schemas import HiddenTestRunRequest, HiddenTestRunResult, PublicTestRunRequest, PublicTestRunResult


def parse_cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in getenv(
            "WORKER_CORS_ORIGINS",
            "http://127.0.0.1:3000,http://localhost:3000",
        ).split(",")
        if origin.strip()
    ]


WORKER_CORS_ORIGINS = parse_cors_origins()


def create_app() -> FastAPI:
    app = FastAPI(title="SignalLoop Worker", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=WORKER_CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/run-public-tests", response_model=PublicTestRunResult)
    def run_public_tests(payload: PublicTestRunRequest) -> PublicTestRunResult:
        try:
            with TemporaryDirectory(prefix="signalloop-public-run-") as workspace:
                from pathlib import Path

                return run_public_tests_in_workspace(payload, Path(workspace))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/run-hidden-tests", response_model=HiddenTestRunResult)
    def run_hidden_tests(payload: HiddenTestRunRequest) -> HiddenTestRunResult:
        try:
            with TemporaryDirectory(prefix="signalloop-hidden-run-") as workspace:
                from pathlib import Path

                return run_hidden_tests_in_workspace(payload, Path(workspace))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/run-candidate-verification", response_model=HiddenTestRunResult)
    def run_candidate_verification(payload: HiddenTestRunRequest) -> HiddenTestRunResult:
        """Run candidate-written test files against the original starter code.

        Caller supplies original implementation files as `files` and the
        candidate's new/modified test files as `hidden_tests`. Tests that fail
        prove the candidate's tests catch real bugs in the starter code.
        """
        try:
            with TemporaryDirectory(prefix="signalloop-candidate-verify-") as workspace:
                from pathlib import Path

                return run_hidden_tests_in_workspace(payload, Path(workspace))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return app


app = create_app()

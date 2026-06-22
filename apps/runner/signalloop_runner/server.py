"""HTTP server mode for the assessment runner.

Used when deployed as an always-on service (Render web service or ECS Service)
instead of ad-hoc Fargate batch tasks. Wraps the same run_tests() logic the
batch runner uses, so behaviour is identical — no Docker-in-Docker needed.

Start with:
    uvicorn signalloop_runner.server:app --host 0.0.0.0 --port 9000
"""

from time import monotonic

from fastapi import FastAPI

from signalloop_runner.main import result_from_exception, run_tests


app = FastAPI(title="SignalLoop Runner", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run-public-tests")
def run_public_tests(request: dict) -> dict:
    t0 = monotonic()
    try:
        result = run_tests({
            "files": request["files"],
            "command": request.get("command", ["python", "-m", "pytest", "tests"]),
            "timeout_seconds": request.get("timeout_seconds", 60),
        })
    except Exception as exc:
        result = result_from_exception(exc)
    result.setdefault("timings", {})["worker_total_ms"] = int((monotonic() - t0) * 1000)
    return result


@app.post("/run-hidden-tests")
def run_hidden_tests(request: dict) -> dict:
    t0 = monotonic()
    try:
        result = run_tests({
            "files": request["files"],
            "hidden_tests": request.get("hidden_tests", {}),
            "command": request.get("command", ["python", "-m", "pytest", "tests/test_hidden_api.py"]),
            "timeout_seconds": request.get("timeout_seconds", 60),
        })
    except Exception as exc:
        result = result_from_exception(exc)
    result.setdefault("timings", {})["worker_total_ms"] = int((monotonic() - t0) * 1000)
    return result


@app.post("/run-candidate-verification")
def run_candidate_verification(request: dict) -> dict:
    t0 = monotonic()
    try:
        result = run_tests({
            "files": request["files"],
            "hidden_tests": request.get("hidden_tests", {}),
            "command": request.get("command", ["python", "-m", "pytest", "tests/", "-v"]),
            "timeout_seconds": request.get("timeout_seconds", 60),
        })
    except Exception as exc:
        result = result_from_exception(exc)
    result.setdefault("timings", {})["worker_total_ms"] = int((monotonic() - t0) * 1000)
    return result

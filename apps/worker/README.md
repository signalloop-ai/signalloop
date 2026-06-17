# SignalLoop Worker

Docker-based execution worker for public and backend-orchestrated hidden assessment tests.

## Local commands

```sh
uv sync
uv run pytest
docker build -f docker/python-assessment.Dockerfile -t signalloop-python-assessment:3.11 .
uv run uvicorn signalloop_worker.main:app --reload --port 9000
```

## Run public tests

```sh
curl -X POST http://127.0.0.1:9000/run-public-tests \
  -H 'Content-Type: application/json' \
  -d '{"files":{"task_api/main.py":"...","tests/test_public_api.py":"..."},"timeout_seconds":20}'
```

The worker writes the supplied files to a temporary workspace and runs public tests in a Docker container. Hidden/evaluator files are rejected from public runs. The default runtime image is `signalloop-python-assessment:3.11`, built from `docker/python-assessment.Dockerfile`.

## Run hidden tests

```sh
curl -X POST http://127.0.0.1:9000/run-hidden-tests \
  -H 'Content-Type: application/json' \
  -d '{"files":{"task_api/main.py":"..."},"hidden_tests":{"test_hidden_api.py":"..."},"timeout_seconds":60}'
```

The hidden endpoint is for the backend API, not the browser. Hidden test output is returned to the API for persistence and later evidence reporting, but is not exposed to candidates.

Local development uses this Docker worker. Production execution is expected to move to AWS ECS/Fargate per-run tasks per `../../docs/decisions/0006-local-docker-and-production-fargate-execution.md`.

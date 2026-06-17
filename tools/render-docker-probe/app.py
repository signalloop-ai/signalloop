from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

from fastapi import FastAPI


app = FastAPI(title="Render Docker Runtime Probe")


def run_command(command: list[str], timeout_seconds: int = 20) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except Exception as exc:  # pragma: no cover - diagnostic endpoint only
        return {
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }

    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "probe": "/probe"}


@app.get("/probe")
def probe() -> dict[str, Any]:
    docker_path = shutil.which("docker")
    docker_socket = "/var/run/docker.sock"

    result: dict[str, Any] = {
        "docker_cli_path": docker_path,
        "docker_socket_exists": os.path.exists(docker_socket),
        "docker_socket_readable": os.access(docker_socket, os.R_OK),
        "docker_socket_writable": os.access(docker_socket, os.W_OK),
    }

    if docker_path is None:
        result["docker_version"] = {
            "ok": False,
            "message": "docker CLI is not available in the runtime image",
        }
        result["docker_run_hello_world"] = {
            "ok": False,
            "message": "skipped because docker CLI is missing",
        }
        return result

    result["docker_version"] = run_command(["docker", "version"], timeout_seconds=10)
    result["docker_run_hello_world"] = run_command(
        ["docker", "run", "--rm", "hello-world"],
        timeout_seconds=30,
    )
    return result

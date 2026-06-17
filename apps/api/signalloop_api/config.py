from functools import lru_cache
from os import environ, getenv
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class Settings:
    def __init__(self) -> None:
        api_dir = Path(__file__).resolve().parents[1]
        repo_root = api_dir.parents[1]
        load_env_file(repo_root / ".env")

        self.database_url = normalize_database_url(
            getenv(
                "DATABASE_URL",
                "postgresql+psycopg://postgres:postgres@localhost:5432/signalloop",
            )
        )
        self.repo_root = Path(getenv("SIGNALLOOP_REPO_ROOT", str(repo_root))).resolve()
        self.assessment_packs_root = self.repo_root / "assessment_packs"
        self.public_base_url = getenv("PUBLIC_BASE_URL", "http://localhost:3000")
        self.execution_worker_url = getenv("EXECUTION_WORKER_URL", "http://localhost:9000")
        self.assessment_runtime_image = getenv("ASSESSMENT_RUNTIME_IMAGE", "signalloop-python-assessment:3.11")
        self.worker_request_timeout_seconds = parse_int(getenv("WORKER_REQUEST_TIMEOUT_SECONDS"), default=90)
        self.worker_request_retries = parse_int(getenv("WORKER_REQUEST_RETRIES"), default=1)
        self.openai_api_key = getenv("OPENAI_API_KEY")
        self.openai_model = getenv("OPENAI_MODEL", "gpt-5")
        self.clerk_secret_key = getenv("CLERK_SECRET_KEY")
        self.environment = getenv("SIGNALLOOP_ENV", "local")
        self.rate_limit_enabled = parse_bool(getenv("RATE_LIMIT_ENABLED"), default=True)
        self.rate_limit_per_minute = parse_int(getenv("RATE_LIMIT_PER_MINUTE"), default=120)
        self.cors_origins = [
            origin.strip()
            for origin in getenv(
                "CORS_ORIGINS",
                "http://127.0.0.1:3000,http://localhost:3000",
            ).split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

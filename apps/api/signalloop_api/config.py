from functools import lru_cache
from base64 import urlsafe_b64decode
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


def parse_csv(value: str | None) -> list[str]:
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def derive_clerk_issuer_from_publishable_key(value: str | None) -> str | None:
    if not value or "_" not in value:
        return None
    encoded = value.rsplit("_", 1)[-1]
    padding = "=" * (-len(encoded) % 4)
    try:
        decoded = urlsafe_b64decode(encoded + padding).decode("utf-8").rstrip("$")
    except Exception:
        return None
    if not decoded:
        return None
    if decoded.startswith("http://") or decoded.startswith("https://"):
        return decoded
    return f"https://{decoded}"


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
        self.execution_backend = getenv("EXECUTION_BACKEND", "http_worker")
        self.execution_worker_url = getenv("EXECUTION_WORKER_URL", "http://localhost:9000")
        self.assessment_runtime_image = getenv("ASSESSMENT_RUNTIME_IMAGE", "signalloop-python-assessment:3.11")
        self.worker_request_timeout_seconds = parse_int(getenv("WORKER_REQUEST_TIMEOUT_SECONDS"), default=90)
        self.worker_request_retries = parse_int(getenv("WORKER_REQUEST_RETRIES"), default=1)
        self.aws_region = getenv("AWS_REGION")
        self.aws_ecs_cluster = getenv("AWS_ECS_CLUSTER")
        self.aws_ecs_runner_task_definition = getenv("AWS_ECS_RUNNER_TASK_DEFINITION")
        self.aws_ecs_runner_container = getenv("AWS_ECS_RUNNER_CONTAINER", "runner")
        self.aws_ecs_subnet_ids = parse_csv(getenv("AWS_ECS_SUBNET_IDS"))
        self.aws_ecs_security_group_ids = parse_csv(getenv("AWS_ECS_SECURITY_GROUP_IDS"))
        self.aws_ecs_assign_public_ip = getenv("AWS_ECS_ASSIGN_PUBLIC_IP", "DISABLED")
        self.aws_ecs_waiter_delay_seconds = parse_int(getenv("AWS_ECS_WAITER_DELAY_SECONDS"), default=6)
        self.aws_ecs_waiter_max_attempts = parse_int(getenv("AWS_ECS_WAITER_MAX_ATTEMPTS"), default=20)
        self.signalloop_run_bucket = getenv("SIGNALLOOP_RUN_BUCKET")
        self.s3_bucket = getenv("S3_BUCKET") or self.signalloop_run_bucket
        self.snapshot_interval_seconds = parse_int(getenv("SNAPSHOT_INTERVAL_SECONDS"), default=300)
        self.openai_api_key = getenv("OPENAI_API_KEY")
        self.openai_model = getenv("OPENAI_MODEL", "gpt-4o")
        self.openai_classifier_model = getenv("OPENAI_CLASSIFIER_MODEL", "gpt-4o-mini")
        self.clerk_secret_key = getenv("CLERK_SECRET_KEY")
        self.environment = getenv("SIGNALLOOP_ENV", "local")
        self.clerk_publishable_key = getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
        self.clerk_jwt_issuer = getenv("CLERK_JWT_ISSUER") or derive_clerk_issuer_from_publishable_key(
            self.clerk_publishable_key
        )
        self.clerk_jwks_url = getenv("CLERK_JWKS_URL") or (
            f"{self.clerk_jwt_issuer.rstrip('/')}/.well-known/jwks.json"
            if self.clerk_jwt_issuer
            else None
        )
        self.super_admin_emails = [
            e.strip().lower()
            for e in getenv("SUPER_ADMIN_EMAILS", "").split(",")
            if e.strip()
        ]
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

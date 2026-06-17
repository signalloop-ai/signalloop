from os import getenv

from signalloop_api.config import load_env_file, normalize_database_url, parse_bool, parse_int


def test_postgres_url_uses_installed_psycopg_driver() -> None:
    assert (
        normalize_database_url("postgresql://postgres:postgres@localhost/signalloop")
        == "postgresql+psycopg://postgres:postgres@localhost/signalloop"
    )


def test_non_postgres_urls_are_unchanged() -> None:
    assert normalize_database_url("sqlite:////tmp/signalloop.db") == "sqlite:////tmp/signalloop.db"


def test_load_env_file_keeps_existing_environment_values(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("SIGNALLOOP_TEST_VALUE=from_file\nSIGNALLOOP_EXISTING=from_file\n")
    monkeypatch.delenv("SIGNALLOOP_TEST_VALUE", raising=False)
    monkeypatch.setenv("SIGNALLOOP_EXISTING", "from_env")

    load_env_file(env_file)

    assert getenv("SIGNALLOOP_TEST_VALUE") == "from_file"
    assert getenv("SIGNALLOOP_EXISTING") == "from_env"


def test_parse_bool_accepts_common_truthy_values() -> None:
    assert parse_bool("true") is True
    assert parse_bool("1") is True
    assert parse_bool("yes") is True
    assert parse_bool("false") is False
    assert parse_bool(None, default=True) is True


def test_parse_int_falls_back_for_invalid_values() -> None:
    assert parse_int("42", default=5) == 42
    assert parse_int("not-a-number", default=5) == 5
    assert parse_int(None, default=5) == 5

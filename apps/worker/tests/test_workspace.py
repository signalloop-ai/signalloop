from pathlib import Path

import pytest

from signalloop_worker.workspace import (
    validate_hidden_test_path,
    validate_relative_path,
    write_hidden_tests,
    write_workspace,
)


def test_write_workspace_materializes_files(tmp_path: Path) -> None:
    write_workspace(
        tmp_path,
        {
            "task_api/main.py": "print('hello')\n",
            "tests/test_public.py": "def test_ok():\n    assert True\n",
        },
    )

    assert (tmp_path / "task_api" / "main.py").read_text() == "print('hello')\n"
    assert (tmp_path / "tests" / "test_public.py").exists()


@pytest.mark.parametrize(
    "path_value",
    [
        "/absolute.py",
        "../escape.py",
        "evaluator/hidden_tests/test_hidden.py",
        "hidden_tests/test_hidden.py",
        ".git/config",
        ".venv/bin/python",
    ],
)
def test_validate_relative_path_rejects_unsafe_or_evaluator_paths(path_value: str) -> None:
    with pytest.raises(ValueError):
        validate_relative_path(path_value)


def test_write_hidden_tests_maps_evaluator_files_into_tests_directory(tmp_path: Path) -> None:
    write_hidden_tests(tmp_path, {"test_hidden_api.py": "def test_hidden():\n    assert True\n"})

    assert (tmp_path / "tests" / "test_hidden_api.py").exists()
    assert not (tmp_path / "hidden_tests").exists()


@pytest.mark.parametrize(
    "path_value",
    [
        "/absolute.py",
        "../escape.py",
        ".git/config.py",
        ".venv/test_hidden.py",
        "notes.txt",
    ],
)
def test_validate_hidden_test_path_rejects_unsafe_paths(path_value: str) -> None:
    with pytest.raises(ValueError):
        validate_hidden_test_path(path_value)

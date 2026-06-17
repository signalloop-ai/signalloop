from pathlib import Path, PurePosixPath


DISALLOWED_PARTS = {"..", "", "evaluator", "hidden_tests", "__pycache__", ".pytest_cache", ".git", ".venv"}
DISALLOWED_FILENAMES = {".gitkeep"}
ALLOWED_HIDDEN_TEST_SUFFIX = ".py"


def validate_relative_path(path_value: str) -> PurePosixPath:
    path = PurePosixPath(path_value)
    if path.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {path_value}")
    if any(part in DISALLOWED_PARTS for part in path.parts):
        raise ValueError(f"Disallowed path in public test run: {path_value}")
    if path.name in DISALLOWED_FILENAMES:
        raise ValueError(f"Disallowed file in public test run: {path_value}")
    return path


def write_workspace(root: Path, files: dict[str, str]) -> None:
    for path_value, content in files.items():
        relative_path = validate_relative_path(path_value)
        target = root / Path(*relative_path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def validate_hidden_test_path(path_value: str) -> PurePosixPath:
    path = PurePosixPath(path_value)
    if path.is_absolute():
        raise ValueError(f"Absolute hidden test paths are not allowed: {path_value}")
    if any(part in {"..", "", "__pycache__", ".pytest_cache", ".git", ".venv"} for part in path.parts):
        raise ValueError(f"Disallowed hidden test path: {path_value}")
    if path.name in DISALLOWED_FILENAMES or not path.name.endswith(ALLOWED_HIDDEN_TEST_SUFFIX):
        raise ValueError(f"Disallowed hidden test file: {path_value}")
    return path


def write_hidden_tests(root: Path, hidden_tests: dict[str, str]) -> None:
    for path_value, content in hidden_tests.items():
        relative_path = validate_hidden_test_path(path_value)
        target = root / "tests" / relative_path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

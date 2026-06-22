from pathlib import Path


IGNORED_DIRS = {"__pycache__", ".pytest_cache", ".venv", ".git", ".uv-cache"}
IGNORED_FILENAMES = {".gitkeep", "uv.lock", "FINAL_EXPLANATION.md"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def apply_placeholders(files: dict[str, str], substitutions: dict[str, str]) -> dict[str, str]:
    if not substitutions:
        return files
    result = {}
    for path, content in files.items():
        for key, value in substitutions.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        result[path] = content
    return result


def load_candidate_files(candidate_path: Path, substitutions: dict[str, str] | None = None) -> dict[str, str]:
    root = candidate_path.resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Candidate path not found: {root}")

    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS for part in relative_parts):
            continue
        if path.name in IGNORED_FILENAMES:
            continue
        if path.suffix in IGNORED_SUFFIXES:
            continue
        files["/".join(relative_parts)] = path.read_text(encoding="utf-8")
    return apply_placeholders(files, substitutions or {})


def load_hidden_test_files(evaluator_path: Path) -> dict[str, str]:
    hidden_tests_path = evaluator_path.resolve() / "hidden_tests"
    if not hidden_tests_path.exists() or not hidden_tests_path.is_dir():
        raise FileNotFoundError(f"Hidden tests path not found: {hidden_tests_path}")

    files: dict[str, str] = {}
    for path in sorted(hidden_tests_path.rglob("*.py")):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(hidden_tests_path).parts
        if any(part in IGNORED_DIRS for part in relative_parts):
            continue
        if path.name in IGNORED_FILENAMES:
            continue
        files["/".join(relative_parts)] = path.read_text(encoding="utf-8")
    return files

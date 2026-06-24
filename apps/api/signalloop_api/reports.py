import logging
from datetime import datetime
from difflib import SequenceMatcher
from re import DOTALL, MULTILINE, findall, finditer, match as re_match
from typing import Protocol

try:
    import boto3
    from botocore.exceptions import ClientError as BotoClientError
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from signalloop_api.attempts import DEFAULT_PACKS
from signalloop_api.auth import get_current_employer
from signalloop_api.audit import record_audit_event
from signalloop_api.config import settings
from signalloop_api.database import get_session
from signalloop_api.integrity_config import INTEGRITY_THRESHOLDS
from signalloop_api.models import AIInteraction, AssessmentAttempt, CodeSnapshot, Employer, EvidenceReport, ProctoringEvent, TestRun
from signalloop_api.schemas import EvidenceReportResponse

logger = logging.getLogger(__name__)


router = APIRouter()


class CandidateVerificationRunner(Protocol):
    def run(self, original_files: dict[str, str], candidate_tests: dict[str, str]) -> dict:
        ...


class ExecutionProviderVerificationRunner:
    def run(self, original_files: dict[str, str], candidate_tests: dict[str, str]) -> dict:
        from signalloop_api.execution import get_execution_provider
        return get_execution_provider().run_candidate_verification(original_files, candidate_tests)


def get_candidate_verification_runner() -> CandidateVerificationRunner:
    return ExecutionProviderVerificationRunner()


# Single source of truth for all scoring weights.
# Change values here to rebalance the rubric — nothing else needs to change.
RUBRIC = {
    "public_issue_resolution": 15,
    "private_issue_generalization": 20,
    "feature_design_implementation": 20,
    "candidate_tests": 15,
    "ai_collaboration": 15,
    "regression_code_quality": 15,
}

SEEDED_ISSUE_AREAS = [
    "duplicate email (case-insensitive + whitespace trimming)",
    "blank or whitespace-only task title (with title trimming)",
    "task priority defaulting, normalization, and validation",
    "owner-only read and delete access",
    "unknown actor access (resource existence leakage)",
    "status transition enforcement (TODO → IN_PROGRESS → DONE)",
    "idempotent owner delete (second delete returns 404)",
]


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def latest_snapshot(snapshots: list[CodeSnapshot], kind: str) -> CodeSnapshot | None:
    for snapshot in reversed(snapshots):
        if snapshot.kind == kind:
            return snapshot
    return None


def test_file_paths(files: dict[str, str]) -> set[str]:
    return {path for path in files if path.startswith("tests/") and path.endswith(".py")}


def _count_test_fns(content: str) -> int:
    return len(findall(r"^\s*def\s+test_[a-zA-Z0-9_]+\s*\(", content, flags=MULTILINE))


def _extract_test_fn_bodies(content: str) -> dict[str, str]:
    """Return {test_name: body_text} for each def test_* in content."""
    lines = content.splitlines(keepends=True)
    fn_bodies: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []
    for line in lines:
        m = re_match(r"^\s*def (test_[a-zA-Z0-9_]+)\s*\(", line)
        if m:
            if current_name is not None:
                fn_bodies[current_name] = "".join(current_lines)
            current_name = m.group(1)
            current_lines = [line]
        elif current_name is not None:
            current_lines.append(line)
    if current_name is not None:
        fn_bodies[current_name] = "".join(current_lines)
    return fn_bodies


def _count_http_assertions(content: str) -> int:
    return len(findall(r"assert\s+.+\.status_code\s*==", content))


def candidate_test_evidence(initial_files: dict[str, str], final_files: dict[str, str]) -> dict:
    initial_tests = test_file_paths(initial_files)
    final_tests = test_file_paths(final_files)
    added = sorted(final_tests - initial_tests)
    modified = sorted(path for path in final_tests & initial_tests if final_files.get(path) != initial_files.get(path))

    # Extract per-function bodies from initial (existing files) and final (touched files).
    initial_bodies: dict[str, str] = {}
    for p in initial_tests & final_tests:
        initial_bodies.update(_extract_test_fn_bodies(initial_files.get(p, "")))

    final_bodies: dict[str, str] = {}
    for p in added + modified:
        final_bodies.update(_extract_test_fn_bodies(final_files.get(p, "")))

    new_names = set(final_bodies) - set(initial_bodies)
    common_names = set(final_bodies) & set(initial_bodies)
    functions_added = len(new_names)
    functions_modified = sum(1 for n in common_names if final_bodies[n] != initial_bodies[n])

    # Keep total for scoring heuristic back-compat.
    test_function_count = functions_added

    http_assertion_count = sum(_count_http_assertions(final_files.get(p, "")) for p in added) + sum(
        max(0, _count_http_assertions(final_files.get(p, "")) - _count_http_assertions(initial_files.get(p, "")))
        for p in modified
    )

    touched_content = "\n".join(final_files.get(path, "") for path in added + modified)
    edge_case_terms = [
        "400", "403", "404", "409", "422",
        "actor_user_id", "duplicate", "blank", "priority", "transition", "delete",
    ]
    edge_case_signal_count = sum(1 for term in edge_case_terms if term in touched_content)
    return {
        "added_test_files": added,
        "modified_test_files": modified,
        "candidate_test_file_count": len(added) + len(modified),
        "functions_added": functions_added,
        "functions_modified": functions_modified,
        "candidate_test_function_count": test_function_count,
        "http_assertion_count": http_assertion_count,
        "edge_case_signal_count": edge_case_signal_count,
    }


def extract_test_names(files: dict[str, str]) -> set[str]:
    names: set[str] = set()
    for path, content in files.items():
        if path.startswith("tests/"):
            names.update(findall(r"^def (test_[a-zA-Z0-9_]+)\s*\(", content, flags=MULTILINE))
    return names


def parse_pytest_output(run: TestRun | None) -> dict:
    if run is None:
        return {"collected": 0, "passed": 0, "failed": 0, "failure_names": [], "status": "missing"}

    output = "\n".join(part for part in [run.stdout or "", run.stderr or ""] if part)
    collected_match = findall(r"collected (\d+) items?", output)
    passed_match = findall(r"(\d+) passed", output)
    failed_names = sorted(set(findall(r"_{2,}\s+([a-zA-Z0-9_]+)\s+_{2,}", output)))
    failed_count = len(failed_names)
    collected = int(collected_match[-1]) if collected_match else failed_count
    passed = int(passed_match[-1]) if passed_match else max(collected - failed_count, 0)
    if run.status == "passed" and collected == 0:
        collected = 1
        passed = 1
    return {
        "collected": collected,
        "passed": passed,
        "failed": failed_count,
        "failure_names": failed_names,
        "status": run.status,
    }


def text_has_any(text: str, terms: list[str]) -> bool:
    haystack = text.lower()
    return any(term in haystack for term in terms)


def extract_code_blocks(text: str) -> list[str]:
    # Fenced blocks: ```optional-lang\n...\n```
    blocks = [m.group(1).strip() for m in finditer(r"```(?:\w+)?\n(.*?)```", text, flags=DOTALL)]
    # Only return blocks substantial enough to be meaningful (3+ lines, 40+ chars).
    return [b for b in blocks if len(b.splitlines()) >= 3 and len(b) >= 40]


def detect_pasted_ai_code(
    ai_interactions: list[AIInteraction],
    initial_files: dict[str, str],
    final_files: dict[str, str],
) -> dict:
    initial_code = "\n".join(initial_files.values())
    matches = []
    for interaction in ai_interactions:
        if interaction.role != "assistant":
            continue
        for block in extract_code_blocks(interaction.message):
            # Skip if the block was already in the starter code (AI quoted existing code).
            if block in initial_code:
                continue
            found_in = [path for path, content in final_files.items() if block in content]
            if found_in:
                matches.append({
                    "found_in_files": found_in,
                    "code_preview": block[:300] + ("..." if len(block) > 300 else ""),
                    "ai_message_at": iso(interaction.created_at),
                })
    return {
        "pasted_ai_code_count": len(matches),
        "matches": matches,
    }


PASTE_LINE_THRESHOLD = 25  # consecutive new lines in one snapshot interval suggesting an external paste


def detect_large_paste_events(snapshots: list[CodeSnapshot]) -> dict:
    flagged = []
    for idx in range(1, len(snapshots)):
        before_snap = snapshots[idx - 1]
        after_snap = snapshots[idx]
        for path, after_content in after_snap.files.items():
            before_content = before_snap.files.get(path, "")
            if before_content == after_content:
                continue
            before_lines = before_content.splitlines()
            after_lines = after_content.splitlines()
            matcher = SequenceMatcher(None, before_lines, after_lines, autojunk=False)
            for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
                if tag in ("insert", "replace"):
                    added = after_lines[j1:j2]
                    if len(added) >= PASTE_LINE_THRESHOLD:
                        preview_lines = added[:20]
                        preview = "\n".join(preview_lines)
                        if len(added) > 20:
                            preview += f"\n... ({len(added) - 20} more lines)"
                        flagged.append({
                            "file": path,
                            "lines_added": len(added),
                            "snapshot_kind": after_snap.kind,
                            "at": iso(after_snap.created_at),
                            "code_preview": preview,
                        })
    return {
        "large_paste_count": len(flagged),
        "events": flagged,
    }


def score_category(name: str, points: int, max_points: int, evidence: str) -> dict:
    return {"category": name, "points": points, "max_points": max_points, "evidence": evidence}


def count_fixed_tests(test_names: list[str], failure_names: list[str]) -> int:
    return sum(1 for test_name in test_names if test_name not in failure_names)


def calculate_scores(
    *,
    test_runs: list[TestRun],
    hidden_summary: dict,
    candidate_tests: dict,
    ai_interactions: list[AIInteraction],
    final_explanation: str,
    decision_log: str,
    snapshots: list[CodeSnapshot],
    initially_failing_tests: list[str],
    feature_design_tests: list[str],
    original_test_names: set[str] | None = None,
    rubric: dict | None = None,
    candidate_verification_summary: dict | None = None,
) -> dict:
    r = rubric or RUBRIC
    public_runs = [run for run in test_runs if run.run_type == "public"]
    pub = parse_pytest_output(public_runs[-1] if public_runs else None)
    hid_collected = hidden_summary["collected"]
    hid_passed = hidden_summary["passed"]
    hid_ratio = hid_passed / hid_collected if hid_collected else 0

    if not public_runs:
        pub_score = 0
        pub_evidence = "No public test run recorded."
    elif not initially_failing_tests:
        pub_score = 0
        pub_evidence = "No initially-failing tests configured for this assessment pack."
    else:
        tests_fixed = [t for t in initially_failing_tests if t not in pub["failure_names"]]
        pub_score = round(r["public_issue_resolution"] * len(tests_fixed) / len(initially_failing_tests))
        pub_evidence = f"{len(tests_fixed)}/{len(initially_failing_tests)} initially-failing tests now pass: {tests_fixed or 'none'}."

    if hidden_summary["status"] == "passed":
        hidden_score = r["private_issue_generalization"]
    elif hid_collected:
        hidden_score = round(r["private_issue_generalization"] * hid_ratio)
    else:
        hidden_score = 0

    combined_failures = sorted(set(pub["failure_names"] + hidden_summary["failure_names"]))
    if feature_design_tests:
        feature_fixed = count_fixed_tests(feature_design_tests, combined_failures)
        feature_score = round(r["feature_design_implementation"] * feature_fixed / len(feature_design_tests))
        feature_evidence = f"{feature_fixed}/{len(feature_design_tests)} configured feature/design checks passed."
    else:
        feature_score = 0
        feature_evidence = "No feature/design checks configured for this assessment pack."

    if not public_runs:
        reg_score = 0
        reg_evidence = "No public test run recorded; regression could not be assessed."
    else:
        regressed = [
            t for t in pub["failure_names"]
            if t not in initially_failing_tests
            and (original_test_names is None or t in original_test_names)
        ]
        originally_passing_count = (
            len(original_test_names - set(initially_failing_tests))
            if original_test_names is not None
            else None
        )
        if not regressed:
            reg_score = r["regression_code_quality"]
            base = f"/{originally_passing_count}" if originally_passing_count is not None else ""
            reg_evidence = f"0{base} originally-passing tests regressed."
        elif originally_passing_count:
            fraction_intact = max(0.0, 1 - len(regressed) / originally_passing_count)
            reg_score = round(r["regression_code_quality"] * fraction_intact)
            reg_evidence = f"{len(regressed)}/{originally_passing_count} originally-passing tests regressed: {regressed}."
        else:
            reg_score = 0
            reg_evidence = f"{len(regressed)} regression(s) detected: {regressed}."

    test_count = candidate_tests["candidate_test_file_count"]
    test_functions = candidate_tests.get("candidate_test_function_count", 0)

    verification_available = (
        candidate_verification_summary is not None
        and candidate_verification_summary.get("status") not in (None, "missing", "error")
    )
    if verification_available:
        pub_failure_set = set(pub["failure_names"])
        verification_failures = set(candidate_verification_summary.get("failure_names", []))  # type: ignore[union-attr]
        proving_count = len(verification_failures - pub_failure_set)
        if proving_count >= 3:
            cand_test_score = r["candidate_tests"]
        elif proving_count >= 2:
            cand_test_score = round(r["candidate_tests"] * 0.75)
        elif proving_count >= 1:
            cand_test_score = round(r["candidate_tests"] * 0.4)
        else:
            cand_test_score = 0
        cand_test_evidence = f"{proving_count} proving test(s) — fail on original starter, pass on fixed code."
    else:
        http_assertions = candidate_tests.get("http_assertion_count", 0)
        edge_signals = candidate_tests.get("edge_case_signal_count", 0)
        if test_functions >= 3 and http_assertions >= 2 and edge_signals >= 2:
            cand_test_score = r["candidate_tests"]
        elif test_functions >= 1 and http_assertions >= 1:
            cand_test_score = round(r["candidate_tests"] * 0.75)
        elif test_count == 1:
            cand_test_score = round(r["candidate_tests"] * 0.4)
        else:
            cand_test_score = 0
        cand_test_evidence = f"Candidate added/modified {test_count} test file(s), with {test_functions} test function(s). (Verification run not available; scored by heuristic.)"

    candidate_ai_count = sum(1 for i in ai_interactions if i.role == "candidate")
    disallowed_count = sum(
        1 for i in ai_interactions
        if i.role == "assistant" and i.policy_tags and any(
            tag in {"enumerate_defects", "full_solution", "final_explanation"} for tag in i.policy_tags
        )
    )
    if candidate_ai_count == 0:
        ai_score = round(r["ai_collaboration"] * 0.5)  # neutral floor — no signal, not penalised
        ai_evidence = "No AI messages sent; collaboration signal is limited but not automatically failing."
    elif disallowed_count == 0:
        ai_score = r["ai_collaboration"]  # full credit — used well
        ai_evidence = f"{candidate_ai_count} candidate prompts, no policy redirects."
    elif disallowed_count == 1:
        ai_score = round(r["ai_collaboration"] * 0.4)  # below floor — one redirect
        ai_evidence = f"{candidate_ai_count} candidate prompts, {disallowed_count} policy redirect."
    elif disallowed_count <= 3:
        ai_score = round(r["ai_collaboration"] * 0.2)  # heavy penalty — repeated redirects
        ai_evidence = f"{candidate_ai_count} candidate prompts, {disallowed_count} policy redirects."
    else:
        ai_score = 0  # systematic policy abuse
        ai_evidence = f"{candidate_ai_count} candidate prompts, {disallowed_count} policy redirects — systematic policy abuse."

    categories = [
        score_category("Public issue resolution", pub_score, r["public_issue_resolution"], pub_evidence),
        score_category("Private issue generalization", hidden_score, r["private_issue_generalization"],
            f"Hidden test status: {hidden_summary['status']}; estimated {hid_passed}/{hid_collected} passed."),
        score_category("Feature/design implementation", feature_score, r["feature_design_implementation"], feature_evidence),
        score_category("Candidate-written tests", cand_test_score, r["candidate_tests"], cand_test_evidence),
        score_category("AI collaboration", ai_score, r["ai_collaboration"], ai_evidence),
        score_category("Regression/code quality", reg_score, r["regression_code_quality"], reg_evidence),
    ]

    total = sum(cat["points"] for cat in categories)
    max_total = sum(r.values())
    return {"total": total, "max_points": max_total, "categories": categories, "rubric": r}


def recommendation_for_score(total: int) -> str:
    if total >= 80:
        return "strong_advance"
    if total >= 60:
        return "advance_with_followups"
    if total >= 40:
        return "needs_review"
    return "do_not_advance"


def build_follow_up_questions(
    hidden_summary: dict,
    candidate_tests: dict,
    ai_interactions: list,
    disallowed_count: int,
    pasted_code: dict,
    paste_events: dict,
    final_explanation: str,
    decision_log: str,
    scores: list,
) -> list[str]:
    questions = []

    # Hidden test failures — name the specific area that failed
    failed_names = hidden_summary.get("failure_names", [])
    if failed_names:
        area_hint = failed_names[0].replace("test_", "").replace("_", " ")
        questions.append(
            f"One of the failing hidden behaviors involves {area_hint}. "
            "Walk through how you would diagnose and fix that."
        )
    else:
        questions.append(
            "Which area of the codebase would you consider highest risk and why?"
        )

    # Authorization decision — always relevant since it's a required design decision
    explanation_text = (final_explanation + " " + decision_log).lower()
    if "403" in explanation_text or "404" in explanation_text:
        questions.append(
            "You mentioned 403 or 404 in your explanation. Walk through how you chose "
            "between them and how a non-owner vs. an unknown actor should be treated differently."
        )
    else:
        questions.append(
            "What did you decide about unauthorized access — 403 or 404 — and why? "
            "How does that choice differ for a non-owner vs. an unknown actor?"
        )

    # Status transition decision — second required design decision
    if "transition" in explanation_text or "in_progress" in explanation_text or "todo" in explanation_text:
        questions.append(
            "You referenced status transitions. Explain the policy you chose and how you enforced it in the code."
        )
    else:
        questions.append(
            "Did you enforce status transition order (TODO → IN_PROGRESS → DONE)? "
            "What was your reasoning?"
        )

    # Candidate tests
    if candidate_tests["candidate_test_file_count"] == 0:
        questions.append(
            "You did not add any test files. Which behavior would you test first "
            "and what would that test look like?"
        )
    else:
        added = candidate_tests.get("added_test_files", [])
        if added:
            fname = added[0].split("/")[-1]
            questions.append(
                f"You added {fname}. Walk through what it covers and what edge case "
                "you were most concerned about."
            )

    # AI policy redirects
    if disallowed_count > 0:
        questions.append(
            f"Your AI session triggered {disallowed_count} policy redirect(s). "
            "What were you trying to accomplish, and how did you proceed after the redirect?"
        )

    # AI code paste
    if pasted_code.get("pasted_ai_code_count", 0) > 0:
        questions.append(
            "Some code from your AI session appears verbatim in your submission. "
            "Walk through that code — do you understand each line, and what would you change?"
        )

    # Large external paste
    if paste_events.get("large_paste_count", 0) > 0:
        questions.append(
            "A large block of code appeared in a single snapshot. "
            "Where did it come from and how did you verify it was correct?"
        )

    # Brief or absent submission review
    if len((final_explanation + decision_log).strip()) < 80:
        questions.append(
            "Your submission review was very brief. "
            "Summarize the most important change you made and why you made it."
        )

    return questions


def parse_submission_review(final_explanation: str, decision_log: str) -> dict:
    fields = {
        "what_changed": "",
        "tradeoffs_or_product_decisions": decision_log,
        "verification": "",
        "improvements_with_more_time": "",
        "additional_notes": "",
    }
    prefix_map = {
        "What changed:": "what_changed",
        "Tradeoffs/product decisions:": "tradeoffs_or_product_decisions",
        "Verification:": "verification",
        "Improve next:": "improvements_with_more_time",
        "Additional notes:": "additional_notes",
    }
    for section in final_explanation.split("\n\n"):
        for prefix, key in prefix_map.items():
            if section.startswith(prefix):
                value = section.removeprefix(prefix).strip()
                fields[key] = "" if value == "Not answered." else value
    if not any(fields.values()) and final_explanation.strip():
        fields["what_changed"] = final_explanation.strip()
    # Old form had four required fields; new form has one ("what changed", notes is optional).
    if fields["tradeoffs_or_product_decisions"] or fields["verification"] or fields["improvements_with_more_time"]:
        required = [
            fields["what_changed"],
            fields["tradeoffs_or_product_decisions"],
            fields["verification"],
            fields["improvements_with_more_time"],
        ]
    else:
        required = [fields["what_changed"]]
    return {
        **fields,
        "required_answer_count": sum(1 for value in required if value.strip()),
        "required_question_count": len(required),
    }


def ai_integrity_risk(ai_interactions: list[AIInteraction], pasted_code: dict, paste_events: dict, submission_review: dict) -> dict:
    assistant_redirects = [
        interaction.policy_tags or []
        for interaction in ai_interactions
        if interaction.role == "assistant" and interaction.policy_tags
    ]
    flattened_tags = [tag for tags in assistant_redirects for tag in tags]
    prompt_injection_count = sum(1 for tag in flattened_tags if tag == "prompt_injection")
    severe_redirect_count = sum(
        1
        for tag in flattened_tags
        if tag in {"full_solution", "final_explanation", "anti_decomposition", "prompt_injection"}
    )
    total_redirect_count = len(assistant_redirects)
    copied_code_count = pasted_code.get("pasted_ai_code_count", 0)
    large_paste_count = paste_events.get("large_paste_count", 0)
    weak_review = submission_review["required_answer_count"] < submission_review["required_question_count"]

    if prompt_injection_count or copied_code_count >= 2 or severe_redirect_count >= 3:
        label = "critical"
    elif copied_code_count or large_paste_count >= 3 or severe_redirect_count >= 2:
        label = "high"
    elif severe_redirect_count or total_redirect_count or large_paste_count or weak_review:
        label = "medium"
    else:
        label = "low"

    return {
        "label": label,
        "signals": {
            "policy_redirect_count": total_redirect_count,
            "severe_redirect_count": severe_redirect_count,
            "prompt_injection_count": prompt_injection_count,
            "pasted_ai_code_count": copied_code_count,
            "large_paste_event_count": large_paste_count,
            "weak_submission_review": weak_review,
        },
        "score_impact": "none_phase_2",
    }


def _weight_points(value: int, low_max: int, medium_max: int) -> int:
    if value <= 0:
        return 0
    if value <= low_max:
        return 1
    if value <= medium_max:
        return 2
    return 3


def _weight_label(pts: int) -> str:
    if pts == 0:
        return "none"
    if pts == 1:
        return "low"
    if pts == 2:
        return "medium"
    return "high"


def compute_integrity_score(
    ai_interactions: list[AIInteraction],
    pasted_code: dict,
    paste_events: dict,
    submission_review: dict,
    proctoring_events: list[ProctoringEvent],
    thresholds: dict | None = None,
) -> dict:
    t = thresholds or INTEGRITY_THRESHOLDS

    # ── Proctoring signals ───────────────────────────────────────────────────
    focus_events = [e for e in proctoring_events if e.event_type == "focus_returned"]
    focus_loss_count = len(focus_events)
    focus_loss_duration_secs = sum(
        int((e.event_metadata or {}).get("duration_seconds", 0)) for e in focus_events
    )
    fullscreen_exit_count = sum(1 for e in proctoring_events if e.event_type == "fullscreen_exit")

    # ── AI signals ────────────────────────────────────────────────────────────
    assistant_tags = [
        tag
        for i in ai_interactions
        if i.role == "assistant" and i.policy_tags
        for tag in i.policy_tags
    ]
    severe_redirect_count = sum(
        1 for tag in assistant_tags
        if tag in {"full_solution", "final_explanation", "anti_decomposition", "prompt_injection"}
    )
    prompt_injection_count = sum(1 for tag in assistant_tags if tag == "prompt_injection")
    large_paste_count = paste_events.get("large_paste_count", 0)

    # ── Weight points per signal ──────────────────────────────────────────────
    focus_count_pts = _weight_points(
        focus_loss_count, t["focus_loss_low_max"], t["focus_loss_medium_max"]
    )
    focus_dur_pts = (
        0 if focus_loss_duration_secs <= 0
        else 1 if focus_loss_duration_secs <= t["focus_loss_duration_medium_secs"]
        else 2 if focus_loss_duration_secs <= t["focus_loss_duration_high_secs"]
        else 3
    )
    fullscreen_pts = _weight_points(
        fullscreen_exit_count, t["fullscreen_exit_low_max"], t["fullscreen_exit_medium_max"]
    )
    paste_pts = _weight_points(
        large_paste_count, t["large_paste_low_max"], t["large_paste_medium_max"]
    )
    ai_violation_pts = (
        0 if severe_redirect_count < t["ai_violation_medium_min"]
        else 1 if severe_redirect_count < t["ai_violation_high_min"]
        else 3
    )

    total_pts = focus_count_pts + focus_dur_pts + fullscreen_pts + paste_pts + ai_violation_pts

    # ── Label from total points ───────────────────────────────────────────────
    if total_pts >= t["label_critical_min"]:
        label = "critical"
    elif total_pts >= t["label_high_min"]:
        label = "high"
    elif total_pts >= t["label_medium_min"]:
        label = "medium"
    else:
        label = "low"

    # ── Promotion rules (override point total) ────────────────────────────────
    if prompt_injection_count >= t["prompt_injection_high_min"]:
        if label not in {"critical"}:
            label = "high"
    if severe_redirect_count >= 5:
        if label not in {"critical"}:
            label = "high"
    if fullscreen_exit_count >= 2 and focus_loss_count >= t["focus_loss_medium_max"]:
        if label not in {"critical"}:
            label = "high"

    contributing_factors = [
        {"signal": "focus_loss_count", "value": focus_loss_count, "weight": _weight_label(focus_count_pts)},
        {"signal": "focus_loss_duration_seconds", "value": focus_loss_duration_secs, "weight": _weight_label(focus_dur_pts)},
        {"signal": "fullscreen_exits", "value": fullscreen_exit_count, "weight": _weight_label(fullscreen_pts)},
        {"signal": "large_paste_count", "value": large_paste_count, "weight": _weight_label(paste_pts)},
        {"signal": "ai_violation_count", "value": severe_redirect_count, "weight": _weight_label(ai_violation_pts)},
        {"signal": "prompt_injection_count", "value": prompt_injection_count, "weight": "high" if prompt_injection_count >= t["prompt_injection_high_min"] else "none"},
    ]

    return {
        "label": label,
        "contributing_factors": contributing_factors,
        "total_weight_points": total_pts,
    }


def build_favo(
    scores: dict,
    candidate_tests: dict,
    ai_interactions: list[AIInteraction],
    submission_review: dict,
    public_run_count: int,
    hidden_summary: dict,
) -> dict:
    categories = {category["category"]: category for category in scores["categories"]}
    feature_max = scores.get("rubric", {}).get("feature_design_implementation", 20)
    feature_threshold = round(feature_max * 0.7)
    return {
        "frame": {
            "label": "strong" if categories["Feature/design implementation"]["points"] >= feature_threshold else "developing",
            "evidence": categories["Feature/design implementation"]["evidence"],
        },
        "ask": {
            "label": "present" if any(i.role == "candidate" for i in ai_interactions) else "limited",
            "evidence": f"{sum(1 for i in ai_interactions if i.role == 'candidate')} candidate prompt(s) captured.",
        },
        "verify": {
            "label": "strong" if public_run_count and candidate_tests["candidate_test_file_count"] else "limited",
            "evidence": (
                f"{public_run_count} public run(s), {candidate_tests['candidate_test_file_count']} candidate test file(s), "
                f"hidden status {hidden_summary['status']}."
            ),
        },
        "own": {
            "label": "present" if submission_review["required_answer_count"] >= 2 else "limited",
            "evidence": (
                f"{submission_review['required_answer_count']}/{submission_review['required_question_count']} "
                "submission-review questions answered."
            ),
        },
    }


def llm_assisted_review_status() -> dict:
    return {
        "status": "not_run",
        "reason": (
            "LLM-assisted report review is intentionally disabled in the local deterministic test path. "
            "Enable only after adding a bounded report-review prompt and ADR-approved safety boundary."
        ),
        "provider_configured": bool(settings.openai_api_key),
    }


def build_timeline(
    attempt: AssessmentAttempt,
    snapshots: list[CodeSnapshot],
    test_runs: list[TestRun],
    ai_interactions: list[AIInteraction],
) -> list[dict]:
    events: list[dict] = [
        {"at": iso(attempt.created_at), "type": "attempt_created", "summary": f"Attempt status: {attempt.status}"},
        {"at": iso(attempt.started_at), "type": "attempt_started", "summary": "Candidate opened invite"},
        {"at": iso(attempt.submitted_at), "type": "attempt_submitted", "summary": "Candidate submitted final solution"},
    ]
    events.extend(
        {"at": iso(snapshot.created_at), "type": f"snapshot:{snapshot.kind}", "summary": f"{len(snapshot.files)} files captured"}
        for snapshot in snapshots
    )
    events.extend(
        {"at": iso(run.created_at), "type": f"test_run:{run.run_type}", "summary": f"{run.status} in {run.duration_ms}ms"}
        for run in test_runs
    )
    events.extend(
        {"at": iso(interaction.created_at), "type": f"ai:{interaction.role}", "summary": ", ".join(interaction.policy_tags or []) or "message logged"}
        for interaction in ai_interactions
    )
    return sorted((event for event in events if event["at"]), key=lambda event: event["at"])


def _build_proctoring_signals(
    attempt: AssessmentAttempt,
    proctoring_events: list[ProctoringEvent],
    paste_events: dict,
) -> dict:
    focus_events = [e for e in proctoring_events if e.event_type == "focus_returned"]
    fullscreen_exit_count = sum(1 for e in proctoring_events if e.event_type == "fullscreen_exit")
    focus_loss_duration_secs = sum(
        int((e.event_metadata or {}).get("duration_seconds", 0)) for e in focus_events
    )

    focus_events_list = [
        {
            "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            "duration_seconds": int((e.event_metadata or {}).get("duration_seconds", 0)),
        }
        for e in focus_events
    ]

    snapshot_events = [e for e in proctoring_events if e.event_type == "snapshot"]
    snapshots_out: list[dict] = []
    if snapshot_events and _BOTO3_AVAILABLE and settings.s3_bucket:
        try:
            s3 = boto3.client("s3")
            for ev in snapshot_events:
                meta = ev.event_metadata or {}
                s3_key = meta.get("s3_key")
                if not s3_key:
                    continue
                try:
                    url = s3.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": settings.s3_bucket, "Key": s3_key},
                        ExpiresIn=3600,
                    )
                    snapshots_out.append({
                        "timestamp": ev.occurred_at.isoformat() if ev.occurred_at else None,
                        "trigger": meta.get("trigger", "periodic"),
                        "url": url,
                    })
                except Exception:
                    pass
        except Exception:
            pass
    elif snapshot_events:
        # Local dev: snapshots stored as inline data URLs (no S3 configured)
        for ev in snapshot_events:
            meta = ev.event_metadata or {}
            data_url = meta.get("data_url")
            if not data_url:
                continue
            snapshots_out.append({
                "timestamp": ev.occurred_at.isoformat() if ev.occurred_at else None,
                "trigger": meta.get("trigger", "periodic"),
                "url": data_url,
            })

    return {
        "webcam_consented": attempt.webcam_consent,
        "focus_loss_count": len(focus_events),
        "focus_loss_duration_seconds": focus_loss_duration_secs,
        "fullscreen_exit_count": fullscreen_exit_count,
        "large_paste_count": paste_events.get("large_paste_count", 0),
        "focus_events": focus_events_list,
        "snapshots": snapshots_out,
    }


def build_report(
    attempt: AssessmentAttempt,
    snapshots: list[CodeSnapshot],
    test_runs: list[TestRun],
    ai_interactions: list[AIInteraction],
    proctoring_events: list[ProctoringEvent] | None = None,
) -> dict:
    final_submission = attempt.final_submission
    if final_submission is None:
        raise ValueError("Final submission is required before generating an evidence report")

    initial = latest_snapshot(snapshots, "initial")
    final = final_submission.code_snapshot
    hidden_runs = [run for run in test_runs if run.run_type == "hidden"]
    hidden_run = hidden_runs[-1] if hidden_runs else None
    hidden_summary = parse_pytest_output(hidden_run)
    initial_files = initial.files if initial else {}
    candidate_tests = candidate_test_evidence(initial_files, final.files)
    pasted_code = detect_pasted_ai_code(ai_interactions, initial_files, final.files)
    paste_events = detect_large_paste_events(snapshots)
    pack_config = DEFAULT_PACKS.get(attempt.assessment_pack.slug, {})
    initially_failing_tests = pack_config.get("initially_failing_tests", [])
    feature_design_tests = pack_config.get("feature_design_tests", [])
    seeded_issue_areas = pack_config.get("seeded_issue_areas", SEEDED_ISSUE_AREAS)
    pack_rubric = pack_config.get("rubric", RUBRIC)
    verification_runs = [run for run in test_runs if run.run_type == "candidate_verification"]
    verification_summary = parse_pytest_output(verification_runs[-1] if verification_runs else None)
    original_test_names = extract_test_names(initial_files)
    scores = calculate_scores(
        test_runs=test_runs,
        hidden_summary=hidden_summary,
        candidate_tests=candidate_tests,
        ai_interactions=ai_interactions,
        final_explanation=final_submission.final_explanation,
        decision_log=final_submission.decision_log,
        snapshots=snapshots,
        initially_failing_tests=initially_failing_tests,
        feature_design_tests=feature_design_tests,
        original_test_names=original_test_names,
        rubric=pack_rubric,
        candidate_verification_summary=verification_summary,
    )
    recommendation = recommendation_for_score(scores["total"])
    submission_review = parse_submission_review(
        final_submission.final_explanation,
        final_submission.decision_log,
    )

    public_runs = [run for run in test_runs if run.run_type == "public"]
    pub_summary = parse_pytest_output(public_runs[-1] if public_runs else None)
    time_used_minutes = None
    if attempt.started_at and attempt.submitted_at:
        time_used_minutes = round((attempt.submitted_at - attempt.started_at).total_seconds() / 60, 2)
    disallowed_count = sum(
        1 for i in ai_interactions
        if i.role == "assistant" and i.policy_tags and any(
            tag in {"enumerate_defects", "full_solution", "final_explanation"} for tag in i.policy_tags
        )
    )
    integrity_risk = ai_integrity_risk(ai_interactions, pasted_code, paste_events, submission_review)
    integrity_score = compute_integrity_score(
        ai_interactions, pasted_code, paste_events, submission_review, proctoring_events or []
    )
    # Keep ai_integrity_risk label in sync with the unified score for backwards compat.
    integrity_risk["label"] = integrity_score["label"]
    proctoring_signals = _build_proctoring_signals(attempt, proctoring_events or [], paste_events)
    favo = build_favo(
        scores=scores,
        candidate_tests=candidate_tests,
        ai_interactions=ai_interactions,
        submission_review=submission_review,
        public_run_count=len(public_runs),
        hidden_summary=hidden_summary,
    )

    return {
        "metadata": {
            "attempt_id": attempt.id,
            "candidate_email": attempt.candidate_email,
            "assessment": {
                "slug": attempt.assessment_pack.slug,
                "title": attempt.assessment_pack.title,
                "version": attempt.assessment_pack.version,
            },
            "submitted_at": iso(attempt.submitted_at),
            "timing": {
                "timing_mode": attempt.timing_mode,
                "duration_minutes": attempt.duration_minutes,
                "time_used_minutes": time_used_minutes,
                "started_at": iso(attempt.started_at),
                "submitted_at": iso(attempt.submitted_at),
                "expires_at": iso(attempt.expires_at),
                "submission_mode": attempt.submission_mode or "manual",
            },
            "evaluator_feedback_mode": attempt.evaluator_feedback_mode,
        },
        "executive_summary": {
            "summary": (
                f"Candidate submitted {len(final.files)} files. "
                f"Public tests: {pub_summary['passed']}/{pub_summary['collected']} passed. "
                f"Hidden tests: {hidden_summary['status']} ({hidden_summary['passed']}/{hidden_summary['collected']} estimated passed). "
                f"Score: {scores['total']}/{scores['max_points']}."
            ),
            "evidence_limits": [
                "Scores are deterministic estimates from captured process evidence.",
                "Manual evaluator review remains required before hiring decisions.",
            ],
        },
        "overall_recommendation": recommendation,
        "scores": scores,
        "rubric_weights": pack_rubric,
        "public_test_results": {
            "last_run_summary": pub_summary,
            "run_count": len(public_runs),
            "initially_failing_tests": initially_failing_tests,
        },
        "hidden_test_results": {
            "seeded_issue_areas": seeded_issue_areas,
            "summary": hidden_summary,
        },
        "feature_design_implementation": next(
            (category for category in scores["categories"] if category["category"] == "Feature/design implementation"),
            None,
        ),
        "candidate_tests": candidate_tests,
        "ai_collaboration": {
            "message_count": len(ai_interactions),
            "candidate_prompt_count": sum(1 for i in ai_interactions if i.role == "candidate"),
            "policy_redirect_count": disallowed_count,
            "pasted_ai_code": pasted_code,
            "large_paste_events": paste_events,
            "flagged_prompts": [
                {
                    "message": ai_interactions[i - 1].message if i > 0 and ai_interactions[i - 1].role == "candidate" else None,
                    "policy_tags": interaction.policy_tags,
                    "at": iso(interaction.created_at),
                }
                for i, interaction in enumerate(ai_interactions)
                if interaction.role == "assistant"
                and interaction.policy_tags
                and any(tag in {"no_issue_identified", "enumerate_defects", "full_solution", "final_explanation"} for tag in interaction.policy_tags)
            ],
            "all_candidate_messages": [
                {
                    "message": interaction.message,
                    "at": iso(interaction.created_at),
                }
                for interaction in ai_interactions
                if interaction.role == "candidate"
            ],
        },
        "ai_integrity_risk": integrity_risk,
        "integrity_score": integrity_score,
        "proctoring_signals": proctoring_signals,
        "favo": favo,
        "llm_assisted_review": llm_assisted_review_status(),
        "process_evidence": {
            "snapshot_count": len(snapshots),
            "test_run_count": len(test_runs),
            "test_runs": [
                {
                    "id": run.id,
                    "type": run.run_type,
                    "status": run.status,
                    "duration_ms": run.duration_ms,
                    "timings": (run.results or {}).get("timings", {}),
                }
                for run in test_runs
            ],
        },
        "submitted_code": {
            "file_count": len(final.files),
            "files": dict(sorted(final.files.items(), key=lambda kv: (
                0 if kv[0].startswith("task_api/") else
                1 if kv[0].startswith("tests/") else
                2
            ))),
        },
        "explanation_submitted": {
            "final_explanation": final_submission.final_explanation,
            "decision_log": final_submission.decision_log,
        },
        "submission_review": submission_review,
        "timeline": build_timeline(attempt, snapshots, test_runs, ai_interactions),
        "follow_up_questions": build_follow_up_questions(
            hidden_summary=hidden_summary,
            candidate_tests=candidate_tests,
            ai_interactions=ai_interactions,
            disallowed_count=disallowed_count,
            pasted_code=pasted_code,
            paste_events=paste_events,
            final_explanation=final_submission.final_explanation,
            decision_log=final_submission.decision_log,
            scores=scores,
        ),
    }


def evidence_response(evidence_report: EvidenceReport) -> EvidenceReportResponse:
    return EvidenceReportResponse(
        attempt_id=evidence_report.attempt_id,
        report_id=evidence_report.id,
        recommendation=evidence_report.recommendation,
        score_total=evidence_report.score_total,
        report=evidence_report.report,
    )


def load_report_inputs(  # noqa: E501
    session: Session, attempt_id: int
) -> tuple[AssessmentAttempt, list[CodeSnapshot], list[TestRun], list[AIInteraction], list[ProctoringEvent]]:
    attempt = session.get(AssessmentAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    snapshots = session.scalars(
        select(CodeSnapshot).where(CodeSnapshot.attempt_id == attempt.id).order_by(CodeSnapshot.id)
    ).all()
    test_runs = session.scalars(
        select(TestRun).where(TestRun.attempt_id == attempt.id).order_by(TestRun.id)
    ).all()
    ai_interactions = session.scalars(
        select(AIInteraction).where(AIInteraction.attempt_id == attempt.id).order_by(AIInteraction.id)
    ).all()
    proctoring_events = session.scalars(
        select(ProctoringEvent).where(ProctoringEvent.attempt_id == attempt.id).order_by(ProctoringEvent.occurred_at)
    ).all()
    return attempt, list(snapshots), list(test_runs), list(ai_interactions), list(proctoring_events)


def ensure_employer_owns_attempt(attempt: AssessmentAttempt, employer: Employer) -> None:
    if attempt.employer_id != employer.id:
        raise HTTPException(status_code=404, detail="Attempt not found")


def run_candidate_verification_if_possible(
    session: Session,
    attempt: AssessmentAttempt,
    snapshots: list[CodeSnapshot],
    verification_runner: CandidateVerificationRunner,
) -> TestRun | None:
    initial = latest_snapshot(snapshots, "initial")
    final_submission = attempt.final_submission
    if initial is None or final_submission is None:
        return None

    initial_files = initial.files
    final_files = final_submission.code_snapshot.files

    original_impl_files = {
        path: content for path, content in initial_files.items()
        if not path.startswith("tests/")
    }
    initial_tests = {
        path: content for path, content in initial_files.items()
        if path.startswith("tests/") and path.endswith(".py")
    }
    candidate_test_files = {
        path: content
        for path, content in final_files.items()
        if path.startswith("tests/") and path.endswith(".py")
        and (path not in initial_tests or content != initial_tests[path])
    }

    if not original_impl_files or not candidate_test_files:
        return None

    try:
        result = verification_runner.run(original_impl_files, candidate_test_files)
        run = TestRun(
            attempt_id=attempt.id,
            run_type="candidate_verification",
            status=result.get("status", "error"),
            stdout=result.get("stdout", ""),
            stderr=result.get("stderr", ""),
            duration_ms=result.get("duration_ms", 0),
            results=result,
        )
        session.add(run)
        session.flush()
        return run
    except Exception as exc:
        logger.warning("Candidate verification run failed: %s", exc)
        return None


@router.post(
    "/assessment-attempts/{attempt_id}/evidence-report",
    response_model=EvidenceReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_evidence_report(
    attempt_id: int,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
    verification_runner: CandidateVerificationRunner = Depends(get_candidate_verification_runner),
) -> EvidenceReportResponse:
    attempt, snapshots, test_runs, ai_interactions, proctoring_events = load_report_inputs(session, attempt_id)
    ensure_employer_owns_attempt(attempt, current_employer)
    if not any(r.run_type == "candidate_verification" for r in test_runs):
        verification_run = run_candidate_verification_if_possible(
            session, attempt, snapshots, verification_runner
        )
        if verification_run is not None:
            test_runs.append(verification_run)
    try:
        report = build_report(attempt, snapshots, test_runs, ai_interactions, proctoring_events)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    recommendation = report["overall_recommendation"]
    score_total = report["scores"]["total"]
    evidence_report = session.scalar(select(EvidenceReport).where(EvidenceReport.attempt_id == attempt.id))
    if evidence_report is None:
        evidence_report = EvidenceReport(
            attempt_id=attempt.id,
            report=report,
            recommendation=recommendation,
            score_total=score_total,
        )
        session.add(evidence_report)
    else:
        evidence_report.report = report
        evidence_report.recommendation = recommendation
        evidence_report.score_total = score_total
        flag_modified(evidence_report, "report")

    record_audit_event(
        session,
        "evidence_report.generated",
        actor_type="employer",
        attempt_id=attempt.id,
        event_metadata={"recommendation": recommendation, "score_total": score_total},
    )
    session.commit()
    session.refresh(evidence_report)
    return evidence_response(evidence_report)


@router.get("/assessment-attempts/{attempt_id}/evidence-report", response_model=EvidenceReportResponse)
def get_evidence_report(
    attempt_id: int,
    session: Session = Depends(get_session),
    current_employer: Employer = Depends(get_current_employer),
) -> EvidenceReportResponse:
    attempt = session.get(AssessmentAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    ensure_employer_owns_attempt(attempt, current_employer)
    evidence_report = session.scalar(select(EvidenceReport).where(EvidenceReport.attempt_id == attempt_id))
    if evidence_report is None:
        raise HTTPException(status_code=404, detail="Evidence report not found")
    return evidence_response(evidence_report)

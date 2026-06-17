from datetime import datetime
from difflib import SequenceMatcher
from re import DOTALL, findall, finditer

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from signalloop_api.attempts import DEFAULT_PACKS
from signalloop_api.audit import record_audit_event
from signalloop_api.database import get_session
from signalloop_api.models import AIInteraction, AssessmentAttempt, CodeSnapshot, EvidenceReport, TestRun
from signalloop_api.schemas import EvidenceReportResponse


router = APIRouter()

# Single source of truth for all scoring weights.
# Change values here to rebalance the rubric — nothing else needs to change.
RUBRIC = {
    "public_test_coverage": 20,   # public tests passing at submission
    "hidden_test_coverage": 30,   # hidden seeded issues fixed (6 tests × 5 pts)
    "regression": 15,             # existing behavior not broken by candidate changes
    "candidate_tests": 15,        # tests the candidate wrote or modified
    "ai_collaboration": 10,       # disciplined AI use (no enumerate-all prompts)
    "explanation": 10,            # explanation and design decision notes
}

SEEDED_ISSUE_AREAS = [
    "duplicate email (case-insensitive + whitespace trimming)",
    "blank or whitespace-only task title (with title trimming)",
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


def candidate_test_evidence(initial_files: dict[str, str], final_files: dict[str, str]) -> dict:
    initial_tests = test_file_paths(initial_files)
    final_tests = test_file_paths(final_files)
    added = sorted(final_tests - initial_tests)
    modified = sorted(path for path in final_tests & initial_tests if final_files.get(path) != initial_files.get(path))
    return {
        "added_test_files": added,
        "modified_test_files": modified,
        "candidate_test_file_count": len(added) + len(modified),
    }


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


PASTE_LINE_THRESHOLD = 8  # consecutive new lines in one snapshot interval suggesting an external paste


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
) -> dict:
    public_runs = [run for run in test_runs if run.run_type == "public"]
    pub = parse_pytest_output(public_runs[-1] if public_runs else None)
    hid_collected = hidden_summary["collected"]
    hid_passed = hidden_summary["passed"]
    hid_ratio = hid_passed / hid_collected if hid_collected else 0

    # Public test coverage (20 pts) — points only for the tests that start failing.
    # A test is "fixed" if it was initially failing but is no longer in the failure list.
    if not public_runs:
        pub_score = 0
        pub_evidence = "No public test run recorded."
    elif not initially_failing_tests:
        pub_score = 0
        pub_evidence = "No initially-failing tests configured for this assessment pack."
    else:
        tests_fixed = [t for t in initially_failing_tests if t not in pub["failure_names"]]
        pub_score = round(RUBRIC["public_test_coverage"] * len(tests_fixed) / len(initially_failing_tests))
        pub_evidence = f"{len(tests_fixed)}/{len(initially_failing_tests)} initially-failing tests now pass: {tests_fixed or 'none'}."

    # Hidden test coverage (30 pts) — 5 pts per hidden test passed.
    if hidden_summary["status"] == "passed":
        hidden_score = RUBRIC["hidden_test_coverage"]
    elif hid_collected:
        hidden_score = round(RUBRIC["hidden_test_coverage"] * hid_ratio)
    else:
        hidden_score = 0

    # Regression (15 pts) — any test NOT in initially_failing_tests that now fails is a regression.
    if not public_runs:
        reg_score = 0
        reg_evidence = "No public test run recorded; regression could not be assessed."
    else:
        regressed = [t for t in pub["failure_names"] if t not in initially_failing_tests]
        if not regressed:
            reg_score = RUBRIC["regression"]
            reg_evidence = "No regression detected in previously-passing tests."
        elif len(regressed) == 1:
            reg_score = round(RUBRIC["regression"] * 0.4)
            reg_evidence = f"1 regression detected: {regressed}."
        else:
            reg_score = 0
            reg_evidence = f"{len(regressed)} regressions detected: {regressed}."

    # Candidate-written tests (15 pts).
    test_count = candidate_tests["candidate_test_file_count"]
    if test_count >= 2:
        cand_test_score = RUBRIC["candidate_tests"]
    elif test_count == 1:
        cand_test_score = round(RUBRIC["candidate_tests"] * 0.6)
    else:
        cand_test_score = 0

    # AI collaboration (10 pts) — disciplined use, no "enumerate all defects" prompts.
    candidate_ai_count = sum(1 for i in ai_interactions if i.role == "candidate")
    disallowed_count = sum(
        1 for i in ai_interactions
        if i.role == "assistant" and i.policy_tags and any(
            tag in {"enumerate_defects", "full_solution", "final_explanation"} for tag in i.policy_tags
        )
    )
    if candidate_ai_count > 0 and disallowed_count == 0:
        ai_score = RUBRIC["ai_collaboration"]
        ai_evidence = f"{candidate_ai_count} candidate prompts, no policy redirects."
    elif candidate_ai_count > 0:
        ai_score = round(RUBRIC["ai_collaboration"] * 0.6)
        ai_evidence = f"{candidate_ai_count} candidate prompts, {disallowed_count} policy redirect(s)."
    else:
        ai_score = 0
        ai_evidence = "No AI messages sent; collaboration signal absent."

    # Explanation and decisions (10 pts).
    explanation_text = (final_explanation + " " + decision_log).strip()
    has_decisions = text_has_any(explanation_text, ["403", "404", "transition", "todo", "in_progress", "done", "tradeoff"])
    has_length = len(explanation_text) >= 80
    if has_decisions and has_length:
        exp_score = RUBRIC["explanation"]
        exp_evidence = "Explanation covers design decisions and has sufficient length."
    elif has_decisions or has_length:
        exp_score = round(RUBRIC["explanation"] * 0.6)
        exp_evidence = "Explanation is partial — either missing design decisions or very brief."
    else:
        exp_score = round(RUBRIC["explanation"] * 0.2)
        exp_evidence = "Explanation is absent or too brief to assess."

    categories = [
        score_category("Public test coverage", pub_score, RUBRIC["public_test_coverage"], pub_evidence),
        score_category("Hidden test coverage", hidden_score, RUBRIC["hidden_test_coverage"],
            f"Hidden test status: {hidden_summary['status']}; estimated {hid_passed}/{hid_collected} passed."),
        score_category("Regression", reg_score, RUBRIC["regression"], reg_evidence),
        score_category("Candidate-written tests", cand_test_score, RUBRIC["candidate_tests"],
            f"Candidate added/modified {test_count} test file(s)."),
        score_category("AI collaboration", ai_score, RUBRIC["ai_collaboration"], ai_evidence),
        score_category("Explanation and decisions", exp_score, RUBRIC["explanation"], exp_evidence),
    ]

    total = sum(cat["points"] for cat in categories)
    max_total = sum(RUBRIC.values())
    confidence = "high" if hid_collected else "medium" if public_runs else "low"
    return {"total": total, "max_points": max_total, "categories": categories, "confidence": confidence}


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

    # Brief or absent explanation
    if len((final_explanation + decision_log).strip()) < 80:
        questions.append(
            "Your final explanation was very brief. "
            "Summarize the most important change you made and why you made it."
        )

    return questions


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


def build_report(
    attempt: AssessmentAttempt,
    snapshots: list[CodeSnapshot],
    test_runs: list[TestRun],
    ai_interactions: list[AIInteraction],
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
    scores = calculate_scores(
        test_runs=test_runs,
        hidden_summary=hidden_summary,
        candidate_tests=candidate_tests,
        ai_interactions=ai_interactions,
        final_explanation=final_submission.final_explanation,
        decision_log=final_submission.decision_log,
        snapshots=snapshots,
        initially_failing_tests=initially_failing_tests,
    )
    recommendation = recommendation_for_score(scores["total"])

    public_runs = [run for run in test_runs if run.run_type == "public"]
    pub_summary = parse_pytest_output(public_runs[-1] if public_runs else None)
    disallowed_count = sum(
        1 for i in ai_interactions
        if i.role == "assistant" and i.policy_tags and any(
            tag in {"enumerate_defects", "full_solution", "final_explanation"} for tag in i.policy_tags
        )
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
        "rubric_weights": RUBRIC,
        "public_test_results": {
            "last_run_summary": pub_summary,
            "run_count": len(public_runs),
            "initially_failing_tests": initially_failing_tests,
        },
        "hidden_test_results": {
            "seeded_issue_areas": SEEDED_ISSUE_AREAS,
            "summary": hidden_summary,
        },
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
                and any(tag in {"enumerate_defects", "full_solution", "final_explanation"} for tag in interaction.policy_tags)
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
        "process_evidence": {
            "snapshot_count": len(snapshots),
            "test_run_count": len(test_runs),
            "test_runs": [
                {"id": run.id, "type": run.run_type, "status": run.status, "duration_ms": run.duration_ms}
                for run in test_runs
            ],
        },
        "explanation_submitted": {
            "final_explanation": final_submission.final_explanation,
            "decision_log": final_submission.decision_log,
        },
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


def load_report_inputs(session: Session, attempt_id: int) -> tuple[AssessmentAttempt, list[CodeSnapshot], list[TestRun], list[AIInteraction]]:
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
    return attempt, snapshots, test_runs, ai_interactions


@router.post(
    "/assessment-attempts/{attempt_id}/evidence-report",
    response_model=EvidenceReportResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_evidence_report(attempt_id: int, session: Session = Depends(get_session)) -> EvidenceReportResponse:
    attempt, snapshots, test_runs, ai_interactions = load_report_inputs(session, attempt_id)
    try:
        report = build_report(attempt, snapshots, test_runs, ai_interactions)
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
def get_evidence_report(attempt_id: int, session: Session = Depends(get_session)) -> EvidenceReportResponse:
    evidence_report = session.scalar(select(EvidenceReport).where(EvidenceReport.attempt_id == attempt_id))
    if evidence_report is None:
        raise HTTPException(status_code=404, detail="Evidence report not found")
    return evidence_response(evidence_report)

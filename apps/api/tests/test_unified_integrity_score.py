"""Tests for compute_integrity_score() — the unified integrity function.

Tests use overridden thresholds so the exact numeric defaults in
integrity_config.py can change without breaking coverage logic.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from signalloop_api.models import AIInteraction, ProctoringEvent
from signalloop_api.reports import compute_integrity_score


# ── Fixtures / helpers ────────────────────────────────────────────────────────

BASE_T: dict = {
    "focus_loss_low_max": 2,
    "focus_loss_medium_max": 4,
    "focus_loss_duration_medium_secs": 120,
    "focus_loss_duration_high_secs": 300,
    "fullscreen_exit_low_max": 1,
    "fullscreen_exit_medium_max": 3,
    "large_paste_low_max": 1,
    "large_paste_medium_max": 2,
    "ai_violation_medium_min": 1,
    "ai_violation_high_min": 3,
    "prompt_injection_high_min": 1,
    "label_medium_min": 1,
    "label_high_min": 3,
    "label_critical_min": 6,
}

NOW = datetime(2026, 6, 22, 12, 0, 0, tzinfo=timezone.utc)
EMPTY_REVIEW = {"required_answer_count": 1, "required_question_count": 1}
EMPTY_PASTE = {"pasted_ai_code_count": 0}
EMPTY_PASTE_EVENTS = {"large_paste_count": 0}


def _focus_event(duration_seconds: int) -> ProctoringEvent:
    e = MagicMock(spec=ProctoringEvent)
    e.event_type = "focus_returned"
    e.event_metadata = {"duration_seconds": duration_seconds}
    return e


def _fullscreen_exit() -> ProctoringEvent:
    e = MagicMock(spec=ProctoringEvent)
    e.event_type = "fullscreen_exit"
    e.event_metadata = None
    return e


def _ai_interaction(policy_tags: list[str]) -> AIInteraction:
    i = MagicMock(spec=AIInteraction)
    i.role = "assistant"
    i.policy_tags = policy_tags
    return i


def score(
    proctoring: list[ProctoringEvent] | None = None,
    ai: list[AIInteraction] | None = None,
    large_pastes: int = 0,
    thresholds: dict | None = None,
) -> dict:
    return compute_integrity_score(
        ai_interactions=ai or [],
        pasted_code=EMPTY_PASTE,
        paste_events={"large_paste_count": large_pastes},
        submission_review=EMPTY_REVIEW,
        proctoring_events=proctoring or [],
        thresholds=thresholds or BASE_T,
    )


# ── All-zero signals → low ────────────────────────────────────────────────────

def test_no_signals_returns_low() -> None:
    result = score()
    assert result["label"] == "low"
    assert result["total_weight_points"] == 0


def test_result_has_required_keys() -> None:
    result = score()
    assert "label" in result
    assert "contributing_factors" in result
    assert "total_weight_points" in result


def test_contributing_factors_present_for_all_signals() -> None:
    result = score()
    signal_names = {f["signal"] for f in result["contributing_factors"]}
    expected = {
        "focus_loss_count", "focus_loss_duration_seconds",
        "fullscreen_exits", "large_paste_count",
        "ai_violation_count", "prompt_injection_count",
    }
    assert signal_names == expected


# ── Focus loss ────────────────────────────────────────────────────────────────

def test_one_focus_event_short_duration_medium() -> None:
    result = score(proctoring=[_focus_event(30)])
    assert result["label"] == "medium"
    focus_factor = next(f for f in result["contributing_factors"] if f["signal"] == "focus_loss_count")
    assert focus_factor["weight"] == "low"


def test_two_focus_events_still_low_count() -> None:
    result = score(proctoring=[_focus_event(20), _focus_event(20)])
    # 2 events = at low_max → low weight (1 pt)
    assert result["total_weight_points"] >= 1


def test_five_focus_events_high_count() -> None:
    result = score(proctoring=[_focus_event(10)] * 5)
    focus_factor = next(f for f in result["contributing_factors"] if f["signal"] == "focus_loss_count")
    assert focus_factor["weight"] == "high"


def test_long_duration_increases_label() -> None:
    # 350s total > high_secs threshold → duration gets high weight
    result = score(proctoring=[_focus_event(350)])
    dur_factor = next(f for f in result["contributing_factors"] if f["signal"] == "focus_loss_duration_seconds")
    assert dur_factor["weight"] == "high"


def test_short_duration_low_weight() -> None:
    result = score(proctoring=[_focus_event(60)])
    dur_factor = next(f for f in result["contributing_factors"] if f["signal"] == "focus_loss_duration_seconds")
    assert dur_factor["weight"] == "low"


# ── Fullscreen exits ──────────────────────────────────────────────────────────

def test_one_fullscreen_exit_medium() -> None:
    result = score(proctoring=[_fullscreen_exit()])
    assert result["label"] == "medium"
    factor = next(f for f in result["contributing_factors"] if f["signal"] == "fullscreen_exits")
    assert factor["weight"] == "low"


def test_four_fullscreen_exits_high_weight() -> None:
    result = score(proctoring=[_fullscreen_exit()] * 4)
    factor = next(f for f in result["contributing_factors"] if f["signal"] == "fullscreen_exits")
    assert factor["weight"] == "high"


# ── Large pastes ──────────────────────────────────────────────────────────────

def test_one_large_paste_medium() -> None:
    result = score(large_pastes=1)
    assert result["label"] == "medium"


def test_three_large_pastes_high() -> None:
    result = score(large_pastes=3)
    factor = next(f for f in result["contributing_factors"] if f["signal"] == "large_paste_count")
    assert factor["weight"] == "high"


# ── AI violations ─────────────────────────────────────────────────────────────

def test_one_severe_ai_violation_medium() -> None:
    result = score(ai=[_ai_interaction(["full_solution"])])
    assert result["label"] == "medium"


def test_three_severe_violations_high_weight() -> None:
    ai = [_ai_interaction(["full_solution"])] * 3
    result = score(ai=ai)
    factor = next(f for f in result["contributing_factors"] if f["signal"] == "ai_violation_count")
    assert factor["weight"] == "high"


def test_non_severe_tags_not_counted() -> None:
    result = score(ai=[_ai_interaction(["no_issue_identified"])])
    factor = next(f for f in result["contributing_factors"] if f["signal"] == "ai_violation_count")
    assert factor["value"] == 0


# ── Promotion rules ───────────────────────────────────────────────────────────

def test_prompt_injection_promotes_to_at_least_high() -> None:
    result = score(ai=[_ai_interaction(["prompt_injection"])])
    assert result["label"] in {"high", "critical"}


def test_prompt_injection_factor_marked_high() -> None:
    result = score(ai=[_ai_interaction(["prompt_injection"])])
    factor = next(f for f in result["contributing_factors"] if f["signal"] == "prompt_injection_count")
    assert factor["weight"] == "high"


def test_five_plus_severe_violations_promoted_high() -> None:
    ai = [_ai_interaction(["full_solution"])] * 5
    result = score(ai=ai)
    assert result["label"] in {"high", "critical"}


def test_fullscreen_exit_plus_focus_loss_promotion() -> None:
    # 2 fullscreen exits + 4 focus losses triggers promotion to at least high
    proctoring = [_fullscreen_exit(), _fullscreen_exit(), _focus_event(10), _focus_event(10), _focus_event(10), _focus_event(10)]
    result = score(proctoring=proctoring, thresholds={**BASE_T, "focus_loss_medium_max": 4})
    assert result["label"] in {"high", "critical"}


# ── Label thresholds ──────────────────────────────────────────────────────────

def test_medium_threshold_boundary() -> None:
    t = {**BASE_T, "label_medium_min": 2, "label_high_min": 5, "label_critical_min": 9}
    # duration=0 → focus_dur_pts=0; count=1 → focus_count_pts=1; total=1 < medium_min(2) → low
    result = score(proctoring=[_focus_event(0)], thresholds=t)
    assert result["label"] == "low"


def test_high_threshold_boundary() -> None:
    t = {**BASE_T, "label_medium_min": 1, "label_high_min": 3, "label_critical_min": 9}
    # 3 pts (two high signals) → high
    result = score(
        proctoring=[_focus_event(400)],  # duration → high (3 pts) alone
        thresholds=t,
    )
    assert result["label"] == "high"


def test_critical_threshold_boundary() -> None:
    t = {**BASE_T, "label_critical_min": 4}
    # 4+ pts → critical
    result = score(
        proctoring=[_focus_event(400), _fullscreen_exit(), _fullscreen_exit(), _fullscreen_exit(), _fullscreen_exit()],
        large_pastes=3,
        thresholds=t,
    )
    assert result["label"] == "critical"


# ── Threshold override ────────────────────────────────────────────────────────

def test_custom_thresholds_change_label() -> None:
    """Relaxing focus-loss threshold should make the same data score lower."""
    strict_t = {**BASE_T, "focus_loss_low_max": 0, "focus_loss_medium_max": 1}
    relaxed_t = {**BASE_T, "focus_loss_low_max": 5, "focus_loss_medium_max": 10}

    proctoring = [_focus_event(30), _focus_event(30)]
    strict_result = score(proctoring=proctoring, thresholds=strict_t)
    relaxed_result = score(proctoring=proctoring, thresholds=relaxed_t)

    # Strict thresholds → higher label
    strict_pts = strict_result["total_weight_points"]
    relaxed_pts = relaxed_result["total_weight_points"]
    assert strict_pts >= relaxed_pts


# ── Snapshot events don't count toward focus signals ─────────────────────────

def test_snapshot_events_not_counted_as_focus_loss() -> None:
    snapshot_event = MagicMock(spec=ProctoringEvent)
    snapshot_event.event_type = "snapshot"
    snapshot_event.event_metadata = {"s3_key": "snapshots/1/abc.jpg", "trigger": "periodic"}

    result = score(proctoring=[snapshot_event])
    factor = next(f for f in result["contributing_factors"] if f["signal"] == "focus_loss_count")
    assert factor["value"] == 0

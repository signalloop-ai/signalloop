"""Configurable thresholds for the unified integrity score.

All values are in one place so they can be tuned from pilot data without
touching scoring logic. Import INTEGRITY_THRESHOLDS directly; the compute
function in reports.py reads from this dict.

Threshold semantics
-------------------
*_low_max    : signal value at or below this → "low" weight (1 pt)
*_medium_max : signal value at or below this (and above low_max) → "medium" weight (2 pts)
above medium_max                             → "high" weight (3 pts)

Duration thresholds use total cumulative seconds across all focus-loss events.
"""

INTEGRITY_THRESHOLDS: dict[str, int] = {
    # Focus-loss event count
    "focus_loss_low_max": 2,
    "focus_loss_medium_max": 4,

    # Cumulative seconds away from the assessment window
    "focus_loss_duration_medium_secs": 120,
    "focus_loss_duration_high_secs": 300,

    # Full-screen exits
    "fullscreen_exit_low_max": 1,
    "fullscreen_exit_medium_max": 3,

    # Large paste events (snapshot-diff based)
    "large_paste_low_max": 1,
    "large_paste_medium_max": 2,

    # AI policy violations (severe tags only)
    "ai_violation_medium_min": 1,
    "ai_violation_high_min": 3,

    # Prompt injection — any occurrence triggers promotion
    "prompt_injection_high_min": 1,

    # Cumulative weight totals for label boundaries
    "label_medium_min": 1,
    "label_high_min": 3,
    "label_critical_min": 6,
}

# 03 - Unified Integrity Score

Status: not started.

## Goal

Replace the separate `ai_integrity_risk` field with a single `integrity_score`
that combines AI collaboration signals (Phase 2) and browser proctoring signals
(Phase 3) into one honest, configurable assessment.

## Motivation

The Phase 2 report has an `ai_integrity_risk` label. Phase 3 adds separate
proctoring signals. Two parallel integrity labels in the same report are
confusing — employers should see one clear answer with contributing factors
itemised below it.

## Output shape

```json
{
  "integrity_score": {
    "label": "low | medium | high | critical",
    "contributing_factors": [
      { "signal": "focus_loss_count",   "value": 3,     "weight": "medium" },
      { "signal": "fullscreen_exits",   "value": 1,     "weight": "low"    },
      { "signal": "large_paste_count",  "value": 2,     "weight": "medium" },
      { "signal": "ai_violation_count", "value": 0,     "weight": "none"   },
      { "signal": "webcam_consented",   "value": true,  "weight": "none"   }
    ]
  }
}
```

The old `ai_integrity_risk` field is kept in the report JSON for backwards
compatibility but deprecated — its value is derived from `integrity_score.label`.

## Rubric

All thresholds are named constants in a `INTEGRITY_THRESHOLDS` config dict in
`apps/api/signalloop_api/reports.py`. No values are hardcoded in logic.

### Signal definitions

| Signal | Source | Unit |
|---|---|---|
| `focus_loss_count` | `proctoring_events` where `event_type = "focus_returned"` | count |
| `focus_loss_duration_seconds` | sum of `metadata.duration_seconds` for focus events | seconds |
| `fullscreen_exits` | `proctoring_events` where `event_type = "fullscreen_exit"` | count |
| `large_paste_count` | existing snapshot diff logic (`PASTE_LINE_THRESHOLD`) | count |
| `ai_violation_count` | existing AI policy violation log | count |
| `prompt_injection_count` | existing policy tags filtered for `prompt_injection` | count |
| `webcam_consented` | `attempt.webcam_consent` | bool |

### Default thresholds (configurable)

```python
INTEGRITY_THRESHOLDS = {
    # Focus loss
    "focus_loss_low_max":               2,      # ≤ this many focus losses → low contribution
    "focus_loss_medium_max":            4,      # ≤ this many → medium contribution
    "focus_loss_duration_medium_secs":  120,    # total seconds away before medium
    "focus_loss_duration_high_secs":    300,    # total seconds away before high

    # Fullscreen
    "fullscreen_exit_low_max":          1,      # 1 exit → low
    "fullscreen_exit_medium_max":       3,      # 2–3 exits → medium

    # Paste
    "large_paste_low_max":              1,      # 1 large paste → low
    "large_paste_medium_max":           2,      # 2 → medium (matches existing Phase 2 logic)

    # AI signals
    "ai_violation_medium_min":          1,      # ≥ 1 violation → medium
    "ai_violation_high_min":            3,      # ≥ 3 violations → high
    "prompt_injection_high_min":        1,      # any prompt injection → immediately high
}
```

### Label computation

Compute a weighted point total across all signals. Each signal contributes
0 (none), 1 (low), 2 (medium), or 3 (high) weight points.

```
total_weight_points = sum of per-signal weight points

0     → label: "low"
1–2   → label: "medium"
3–5   → label: "high"
6+    → label: "critical"
```

Promotion rules (override the point total):
- Any `prompt_injection` event → minimum "high"
- `ai_violation_count ≥ 5` → minimum "high"
- Both `fullscreen_exits ≥ 2` AND `focus_loss_count ≥ 4` together → minimum "high"

### Example

Candidate with: 3 focus losses (90s total), 1 fullscreen exit, 1 large paste,
0 AI violations, webcam consented.

| Signal | Raw value | Threshold hit | Weight points |
|---|---|---|---|
| focus_loss_count | 3 | ≤ 4 (medium_max) | 2 |
| focus_loss_duration | 90s | ≤ 120s (medium) | 1 |
| fullscreen_exits | 1 | ≤ 1 (low_max) | 1 |
| large_paste_count | 1 | ≤ 1 (low_max) | 1 |
| ai_violation_count | 0 | below medium_min | 0 |

Total: 5 → label: "high"

Employer sees: "High integrity risk — 3 focus-loss events, 1 fullscreen exit,
1 large paste."

## Implementation

- `compute_integrity_score(report_data, proctoring_events, attempt) -> IntegrityScore`
  function in `reports.py`.
- Called at report generation time, same as existing `compute_ai_integrity_risk()`.
- `compute_ai_integrity_risk()` becomes a thin wrapper returning
  `integrity_score.label` for backwards compatibility.
- `INTEGRITY_THRESHOLDS` dict exported to a new
  `apps/api/signalloop_api/integrity_config.py` module so it can be overridden
  in tests without touching the report generator.

## Acceptance criteria

- Report JSON contains `integrity_score` with `label` and `contributing_factors`.
- `ai_integrity_risk.label` still present in JSON, equals `integrity_score.label`.
- All thresholds live in `INTEGRITY_THRESHOLDS`; no magic numbers in scoring logic.
- Unit tests cover: all-zero signals → "low", promotion rules, boundary conditions.
- Changing a threshold value changes the label without code changes.

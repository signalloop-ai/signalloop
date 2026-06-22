# 04 - Employer Report: Proctoring Section

Status: not started.

## Goal

Add a "Proctoring Signals" section to the employer evidence report, and replace the
existing AI integrity risk banner with a unified integrity banner that draws from the
combined score introduced in task 03.

## Report section: Proctoring Signals

Position: after "Process evidence" (snapshots, test runs), before "Submission Review".

### Contents

**Webcam consent chip** — one of:
- `Webcam enabled` (green pill)
- `Webcam declined` (neutral pill)
- `Webcam not requested` (neutral pill — pre-Phase-3 attempts)

**Event summary table:**

| Signal | Value |
|---|---|
| Focus-loss events | 3 |
| Total time away | 1m 32s |
| Fullscreen exits | 1 |
| Large pastes | 1 |

**Snapshot thumbnail strip** (if webcam consented):
- Horizontal scrollable row of JPEG thumbnails, ~80px tall
- Each thumbnail labelled with HH:MM elapsed time and trigger type
  ("periodic", "focus return", "submission")
- Clicking a thumbnail opens the full image in a new tab (presigned GET URL)

If webcam was not consented: replace thumbnail strip with
"Candidate did not enable webcam for this assessment."

**Focus-loss timeline** (collapsed by default, `<details>`):
Each focus event as a row: `HH:MM elapsed — away for Xs`.

## Unified integrity banner

The existing amber/red banner at the top of the report that shows `ai_integrity_risk`
is replaced with a banner driven by `integrity_score`.

**Low:** no banner shown (same as current behavior).

**Medium:**
```
⚠ Moderate integrity signals — see Proctoring Signals and AI collaboration sections.
```
Amber background.

**High / Critical:**
```
⚠ High integrity risk — [contributing factor summary]. Review proctoring signals and
AI collaboration evidence carefully before advancing this candidate.
```
Red background.

Contributing factor summary is a short plain-English sentence generated from
`integrity_score.contributing_factors`:
- "3 focus-loss events, 1 fullscreen exit"
- "2 large pastes, 1 AI policy violation"

## Frontend changes

File: `apps/web/src/app/employer/reports/[attemptId]/page.tsx`

- Fetch `proctoring_signals` from report JSON (new field from task 03/04 backend).
- Render `ProctoringSignalsSection` component.
- Replace `IntegrityRiskBanner` to use `integrity_score` instead of `ai_integrity_risk`.
- Fetch snapshot presigned URLs from the report API (backend returns them inline in the
  `proctoring_signals.snapshots` array as `{ timestamp, trigger, url }` objects).

## Backend changes

Report generation (`reports.py`):
- Collect `proctoring_events` for the attempt from the database.
- Compute `proctoring_signals` summary dict:
  ```python
  {
      "webcam_consented": bool | None,
      "focus_loss_count": int,
      "focus_loss_duration_seconds": int,
      "fullscreen_exit_count": int,
      "large_paste_count": int,
      "focus_events": [{ "occurred_at": str, "duration_seconds": int }],
      "snapshots": [{ "timestamp": str, "trigger": str, "url": str }]
  }
  ```
- For each snapshot S3 key in `proctoring_events`, generate a presigned GET URL
  (60-minute expiry) and include it in `snapshots`.
- Store `proctoring_signals` in the report JSON.

Report fetch endpoint: return `proctoring_signals` as part of the existing report JSON.
No new endpoint needed.

## Acceptance criteria

- Proctoring Signals section appears in the employer report.
- Focus-loss count, duration, and fullscreen exits correctly reflect logged events.
- Thumbnail strip renders for consented attempts; "not enabled" message for others.
- Integrity banner shows correct label and contributing factor summary.
- Clicking a thumbnail opens the full-size image.
- Pre-Phase-3 attempts (no `proctoring_signals`) render gracefully — section shows
  "No proctoring data available for this attempt."

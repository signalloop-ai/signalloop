# 01 - Browser Event Logging

Status: not started.

## Goal

Persist a structured log of candidate browser behavior events (fullscreen exits,
focus loss, focus return) so the employer report can surface an accurate picture
of the assessment environment.

## Backend changes

### New table: `proctoring_events`

```sql
CREATE TABLE proctoring_events (
    id          SERIAL PRIMARY KEY,
    attempt_id  INTEGER NOT NULL REFERENCES assessment_attempts(id),
    event_type  VARCHAR(50) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    metadata    JSONB
);
```

`event_type` values: `fullscreen_exit`, `fullscreen_enter`, `focus_lost`,
`focus_returned`.

`metadata` carries context: `{ "duration_seconds": 45 }` for a returned-focus
event, `{ "paste_size_lines": 30 }` for a large paste event (large paste events
already tracked via snapshots — link them here as a derived event type so the
proctoring section has a single source).

### Alembic migration

`0005_add_proctoring_events.py`

### New API endpoint

```
POST /candidate/invites/{invite_token}/proctoring-events
Body: { event_type: string, occurred_at: string, metadata?: object }
Response: 201
```

Requires a valid (non-submitted, non-expired) attempt. Accepts events in batches
to reduce round trips:

```
POST /candidate/invites/{invite_token}/proctoring-events/batch
Body: { events: [{ event_type, occurred_at, metadata? }, ...] }
```

Rate-limited: max 60 events per minute per attempt (existing rate limiter covers this).

## Frontend changes

### Event listeners (candidate workspace)

Add to `apps/web/src/app/invite/[inviteToken]/page.tsx`:

```
document.addEventListener("fullscreenchange", onFullscreenChange)
document.addEventListener("visibilitychange", onVisibilityChange)
window.addEventListener("blur", onWindowBlur)
window.addEventListener("focus", onWindowFocus)
```

Track `blurredAt` timestamp in component state. On focus return, compute duration
and emit a `focus_returned` event with `{ duration_seconds }` in metadata.

### Fullscreen request

On workspace load (after invite accepted), call `document.documentElement.requestFullscreen()`.
If the browser or user declines, log that in component state — do not block the assessment.
Show a non-intrusive banner ("For the best experience, please stay fullscreen") if not
in fullscreen, but never gate the assessment on it.

### Batched upload

Buffer events in a local queue (`useRef<ProctoringEvent[]>`). Flush the queue to the
batch endpoint:
- Every 30 seconds (same interval as the existing auto-poll)
- On page unload (`beforeunload`) — best-effort, no await
- On final submission (before the submission API call)

This avoids a round trip per event and survives brief network blips.

## What this does NOT do

- Block fullscreen exit
- Block tab switching
- Show any visible penalty message to the candidate
- Log mouse movements or keystrokes

## Acceptance criteria

- `proctoring_events` rows written for: fullscreen exit, focus loss > 5 seconds,
  focus return (with duration), on a real candidate workspace session.
- Batch endpoint accepts up to 20 events per call.
- Events attached to the correct `attempt_id`.
- No event logging for submitted or expired attempts (409 returned, ignored by frontend).

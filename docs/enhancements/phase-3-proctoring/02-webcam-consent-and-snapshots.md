# 02 - Webcam Consent and Snapshots

Status: not started.

## Goal

Optionally capture periodic JPEG snapshots from the candidate's webcam during the
assessment and store them in S3. Gives employers visual spot-check evidence without
the storage and complexity of continuous video recording.

## Consent model

Webcam is always optional. The assessment proceeds in full whether or not the
candidate consents.

Consent UI appears once, immediately after the candidate accepts the invite and
before the workspace loads. Two choices:
- **Allow camera** — starts snapshot capture
- **Skip** — proceeds without any camera involvement

If the candidate grants camera access but later revokes it at the OS/browser level,
capture silently stops — no error shown to the candidate.

Consent choice is stored on the attempt: `webcam_consent: boolean | null`.
`null` means the consent screen was not shown (older attempts without Phase 3).

## Snapshot schedule

| Trigger | Frequency / condition |
|---|---|
| Periodic | Every 5 minutes (configurable: `SNAPSHOT_INTERVAL_SECONDS`, default 300) |
| Focus-loss return | If away for > 30 seconds, capture on return |
| Final submission | One snapshot immediately before the submission API call |

Maximum snapshots: `ceil(duration_minutes / 5) + focus_loss_count + 1`.
For a 90-min assessment: ~19 + focus events + 1 at submission ≈ 25 max.

## Technical design

### Capture (frontend)

```ts
const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
const track = stream.getVideoTracks()[0];
const imageCapture = new ImageCapture(track);
const blob = await imageCapture.takePhoto({ imageWidth: 640 });
```

`ImageCapture` API is supported in all modern browsers. Fallback: draw a video
frame to an off-screen canvas and call `canvas.toBlob("image/jpeg", 0.7)`.

Canvas fallback for browsers without `ImageCapture`:
```ts
const video = document.createElement("video");
video.srcObject = stream;
await video.play();
const canvas = document.createElement("canvas");
canvas.width = 640; canvas.height = 480;
canvas.getContext("2d")!.drawImage(video, 0, 0);
const blob = await new Promise<Blob>(resolve => canvas.toBlob(resolve!, "image/jpeg", 0.7));
```

### Upload (frontend → S3 via presigned URL)

1. Frontend calls `POST /candidate/invites/{token}/snapshot-upload-url`
   with `{ filename: "{unix_timestamp}.jpg" }`.
2. API returns `{ upload_url: string, s3_key: string }` (presigned PUT URL,
   5-minute expiry).
3. Frontend does `fetch(upload_url, { method: "PUT", body: blob, headers: { "Content-Type": "image/jpeg" } })`.
4. Frontend calls `POST /candidate/invites/{token}/proctoring-events` with
   `event_type: "snapshot"` and `metadata: { s3_key, trigger: "periodic" | "focus_return" | "submission" }`.

### Backend: presigned URL endpoint

```
POST /candidate/invites/{invite_token}/snapshot-upload-url
Body: { filename: string }
Response: { upload_url: string, s3_key: string }
```

S3 key format: `snapshots/{attempt_id}/{filename}`

Uses `boto3.client("s3").generate_presigned_url("put_object", ...)`.
Requires `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET`
— already present in Render environment.

### Backend: store consent

Add `webcam_consent: bool | None` column to `assessment_attempts` (Alembic migration
`0006_add_webcam_consent`).

```
PATCH /candidate/invites/{invite_token}/webcam-consent
Body: { consented: boolean }
Response: 204
```

Called once when the candidate makes their choice on the consent screen.

## Employer report: snapshot thumbnails

The report fetches the list of snapshot S3 keys from `proctoring_events` where
`event_type = "snapshot"`. For each key, the report API returns a presigned GET URL
(60-minute expiry). The report UI renders these as a horizontal thumbnail strip
with timestamps.

If `webcam_consent = false` or `null`, the thumbnail strip is replaced with
"Candidate did not enable webcam."

## Security and privacy

- S3 keys are never exposed to the candidate — presigned PUT URLs are write-only
  for the specific key and expire after 5 minutes.
- Employer presigned GET URLs expire after 60 minutes (report viewing session).
- No face recognition, emotion detection, or biometric processing.
- Candidate-facing copy on the consent screen must state: "These images are stored
  securely and shared only with the employer who created this assessment."

## Acceptance criteria

- Consent screen shows before workspace loads; choice is persisted.
- Snapshots upload to `s3://SIGNALLOOP_RUN_BUCKET/snapshots/{attempt_id}/`.
- At least one periodic snapshot per 5-minute window appears in S3.
- Submission snapshot captured immediately before submit call.
- Employer report shows thumbnail strip for consented attempts.
- Non-consented attempts show "Candidate did not enable webcam" in the report.
- No camera activity occurs for non-consented attempts after page load.

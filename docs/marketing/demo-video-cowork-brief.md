# SignalLoop demo video — handoff brief for a computer-use agent (Claude cowork)

You (the agent) will record and assemble a slick, **under-3-minute** general-audience demo of
SignalLoop. Voiceover is already generated; you do the screen capture + editing. `[HUMAN]`
marks the few steps the user must do (logins, installs, final approval).

## 0. Mission / output spec
- One polished MP4, **16:9, 1080p, < 3:00**, embeddable anywhere (website, LinkedIn, link).
- Style: polished screen recording with **smooth auto-zoom** + **on-screen captions** + a
  **music bed** + the provided **AI voiceover**. No animation needed.
- Tone: confident, modern, "hiring/engineering in the AI era."

## 1. What's already prepared (in this repo)
- **Script + shot list + captions:** `docs/marketing/demo-video-plan.md` (§3 script, §4 shots,
  §6 the exact prompts to type). Read this first — it's the source of truth for content.
- **Voiceover MP3s (already generated):** `docs/marketing/voiceover/` — seven files, in order:
  `01_hook`, `02_what`, `03_task`, `04_collaborator`, `05_report`, `05b_platform`, `06_close`.
  Use these as the master audio timeline. (Voice "Adam"; ask the human if they want another
  voice.)
- **Captions:** the CAP lines in plan §3. Easiest path: auto-caption from the VO in your editor,
  then spot-fix against §3.

## 2. Environment (running locally on this machine)
- Web app: **http://localhost:3000** · API: http://127.0.0.1:8015 · Worker: 127.0.0.1:9000
  (all running; if a page is blank, ask `[HUMAN]` to confirm the dev servers are up).
- Browser prep before recording: a clean Chrome window, **no bookmarks bar, no extensions
  visible**, window sized to 1920×1080, OS in Do-Not-Disturb, dock hidden.
- Candidate workspace is **token-based (no login)**. Employer/admin pages need a **Clerk login**
  → `[HUMAN]` step.

## 3. Tools to install `[HUMAN]` (or confirm installed)
- **Screen Studio** (capture with auto-zoom + smooth cursor) — free trial is fine.
- **CapCut** (free) or **Descript** for assembly + auto-captions. Descript is easiest for VO sync.
- A licensed music track (Epidemic Sound / Artlist / YouTube Audio Library).

## 4. Coordination points `[HUMAN]`

**Two different accounts** (they can't be signed in at once — Clerk is single-session). Easiest:
use **two browser profiles/windows**, one per account, so no mid-recording sign-out dance.
- **Employer (regular):** `employer@example.com` → used for the employer portal + the evidence
  report (Blocks B–D). *Must own the invite to view its report.*
- **Admin:** `admin@example.com` → used ONLY for the `/admin` roster shot (Block F). Note an
  admin is auto-redirected away from `/employer`, so do not use it for the report.

1. Install the tools above (and grant Screen Studio screen-recording permission).
2. **Create a fresh invite you own:** signed in as **`employer@example.com`**, go to
   http://localhost:3000/employer, create an invite (any email, Standard FastAPI v2, untimed),
   and copy the invite link → hand it to the agent. *(Owning it lets you open its report in
   Block D.)*
3. Stay signed in as **`employer@example.com`** for Blocks B–D; switch to (or use the second
   profile for) **`admin@example.com`** for the Block F admin shot.
4. Final review of the cut before publishing.

## 5. Recording runbook — ONE candidate session produces both the workspace footage and a real,
strong report. Record each block as its own clip; you'll sequence them in the editor.

Pre-made fallback invite (untimed, Standard v2):
`http://localhost:3000/invite/<invite-token>`

**Block A — open + the task** (maps to VO 03_task)
1. Open the invite link → **Accept**. (Webcam prompt: click **Skip** unless a camera is
   available; if available, **Allow** so the report's proctoring section has a snapshot.)
2. Open `task_api/main.py` in the file tree; scroll slowly so the code is readable.
3. Click **Run** (public tests). Let the bottom drawer show failures. Click a failing test name
   → it jumps to the line. Pause ~1s. *(Auto-zoom this.)*

**Block B — the AI collaborator (the centerpiece; maps to VO 04_collaborator)**
4. In the AI Collaborator panel, type and send:
   `I want to add an endpoint that lists all tasks for a given owner — can you write it for me?`
   → wait for the assistant's **guiding question**. Zoom on it.
5. Type and send:
   `A GET route like /users/{user_id}/tasks, returning tasks where owner_id matches`
   → the assistant now returns the **focused code**. Zoom on the code block.
6. (Optional extra beat) type:
   `I think delete_task never checks the task owner — how do I fix that?`
   → it returns only the **minimal lines**, not the whole function. (Shows "guides, doesn't dump.")
7. Slowly scroll the chat so the guide→code arc is visible.

**Block C — complete + submit** (for a strong report)
8. To make the submitted solution strong, paste the reference solution into `task_api/main.py`
   (replace the file contents): copy from
   `assessment_packs/fastapi_task_api_standard_v2/evaluator/reference_solution/task_api/main.py`.
   *(Do this quickly — it's not a hero shot.)*
9. Click **Run** again → tests pass. (Nice "green" beat.)
10. Click **Submit** → the confirmation modal appears (good beat) → confirm.

**Block D — the evidence report** `[HUMAN] signed in as employer@example.com` (maps to VO 05_report)
11. As the **employer who owns the invite** (`employer@example.com`), open the attempt's
    **Evidence Report** in the employer portal → the report auto-generates on first open. (Use
    the invite you created in §4 step 2 so this account owns it. The §5 fallback invite may be
    owned by another account — only use it if `employer@example.com` owns it.)
12. Record, slowly, with zooms: the **recommendation banner + score ring** → the **score
    breakdown bars** → the **AI collaboration** section → the **FAVO** section → the **follow-up
    interview questions**. (If a proctoring snapshot exists, show the Proctoring Signals strip.)

**Block E — platform / extensibility** `[HUMAN] logged in` (maps to VO 05b_platform)
13. In the employer portal, open the **Create invite** controls and show the **assessment
    selector** (Standard FastAPI v2 / Advanced FastAPI v1), then click **Details** to reveal the
    assessment detail modal. This visually backs "standard & advanced modes / more skills."

**Block F — breadth + close** `[HUMAN] signed in as admin@example.com (admin)` (maps to VO 06_close)
14. Switch to the **admin** account (`admin@example.com`) — or its browser profile — and go
    to **http://localhost:3000/admin**: a 3-second establishing pan over the employer roster.
15. End on a clean **SignalLoop logo** frame (use the app header, or a title card in the editor).

## 6. Assembly runbook (editor)
1. Import the seven VO MP3s in order onto the audio track — this is your **master timeline**.
2. Lay each recorded block under its matching VO section (see the maps above), trimming so the
   key action lands under the matching sentence.
3. Add **auto-captions** from the VO; spot-fix against plan §3; keep them short + high-contrast.
4. Apply Screen Studio auto-zoom (or manual zoom keyframes) on: the failing test line, the AI
   reply, the AI code block, the score ring, FAVO.
5. Add a **title card** at the start ("SignalLoop") and an **outro card** ("SignalLoop ·
   <yourdomain>") held ~2s.
6. Add a **music bed**, ducked ~-18 dB under the VO; small lift at the report reveal.
7. Trim to **< 3:00**. Export **MP4, H.264, 1080p**.

## 7. Deliverables
- `signalloop-demo-1080p.mp4` (primary).
- Optional later: a 9:16 or 1:1 social cut, and a burned-in-captions version for autoplay.

## 8. Notes / gotchas
- The AI responses are generated live, so wording varies slightly — the §6 prompts reliably
  produce the guide-then-code behavior; if a take is off, just re-send.
- Generator model is `gpt-4o` (fast, predictable). Don't change it.
- If the employer report looks weak, it means the submission wasn't complete — re-do Block C
  (paste the full reference solution) before submitting.
- Keep the candidate identity/email consistent across shots for coherence.

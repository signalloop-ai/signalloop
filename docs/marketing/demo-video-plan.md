# SignalLoop demo video — production plan

A slick, <3-minute, general-audience intro (works for hiring teams, investors, candidates, or
"try this out" links). AI voiceover + on-screen captions + music over polished screen
recording. 16:9, 1080p.

## 1. Tool stack (Mac)

| Job | Recommended | Free alternative |
|---|---|---|
| Screen capture (auto-zoom, smooth cursor) | **Screen Studio** (~$89 one-time) | QuickTime (no auto-zoom) |
| AI voiceover | **ElevenLabs** (natural, consistent) | macOS/Descript built-in voices |
| Edit + captions + assembly | **Descript** (edit by text, auto-captions) | **CapCut** (free, great captions/effects) |
| Music (licensed) | Epidemic Sound / Artlist | YouTube Audio Library |

Recommended combo: **Screen Studio** (capture) + **ElevenLabs** (VO) + **Descript or CapCut**
(assemble + captions + music). No animation software needed — "slick" = auto-zoom + clean
overlays.

## 2. End-to-end process

1. **Stage demo data** (see §5) so every screen looks real and impressive.
2. **Prep the environment**: clean Chrome profile (no bookmarks bar, no extensions), 1920×1080
   display scaling, hide the dock, close notifications (Do Not Disturb), one API instance
   running, log in as the demo employer/candidate ahead of time.
3. **Lock the script** (§3) and generate the **AI voiceover** in ElevenLabs (one clip per
   section; keep the takes so you can re-time). Note each section's duration.
4. **Record screen segments** per the shot list (§4) in Screen Studio — follow the script
   beats, move the cursor deliberately and slowly, pause on key UI. Record 1–2 extra seconds at
   each end for trimming.
5. **Assemble** in the editor: drop the VO on the audio track, lay screen clips under it, add
   zooms/callouts where noted, then intro/outro cards, captions, and a music bed ducked ~-18dB
   under the VO.
6. **Tighten to <3:00**, export MP4 (H.264, 1080p). Optionally export a 1:1 or 9:16 cut for
   social later.
7. **Captions**: burn-in for social autoplay; keep an .srt sidecar for the website player.

## 3. Script (AI voiceover) — timed to ~2:55

> VO = voiceover line. CAP = on-screen caption/callout. SHOT = what's on screen.

**[0:00–0:12] Hook**
- VO: "Hiring engineers just got harder. Hand out a take-home test, and an AI solves it in
  minutes — so it tells you nothing about how someone actually builds."
- CAP: "Take-home tests? Solved by AI in minutes."
- SHOT: Title card "SignalLoop" → cut to the candidate workspace blurred/zoomed.

**[0:12–0:26] What it is**
- VO: "SignalLoop is a coding assessment built for the AI era. Candidates fix real bugs and
  ship features in a real IDE — with an AI collaborator built in, exactly like the job."
- CAP: "A real IDE. A real AI collaborator."
- SHOT: Candidate workspace resolves into focus — file tree, Monaco editor, AI panel, Run/Submit.

**[0:26–0:46] The task**
- VO: "They start with a working-but-flawed FastAPI service: read the code, run the public
  tests, and see exactly what's failing — just like a real ticket."
- CAP: "Find the bug. Fix it. Prove it with tests."
- SHOT: open `task_api/main.py`; click **Run**; test drawer shows pass/fail; click a failing
  test name → jumps to the line. (Zoom on the failing assertion.)

**[0:46–1:34] The differentiator — the AI collaborator (the money shot)**
- VO: "Here's what makes SignalLoop different. The AI collaborator won't hand over the answer —
  it coaches. Ask it to build a feature, and it asks how *you'd* approach it first."
- CAP: "It guides — it doesn't give it away."
- SHOT: type prompt #1 (§6); AI replies with a guiding question. Zoom on the reply.
- VO: "Once the candidate shows they understand the approach, it gives just the code they need —
  not the whole solution."
- CAP: "Show you understand → earn the code."
- SHOT: type prompt #2 (the approach); AI replies with the focused code. Zoom on the code block.
- VO: "Every prompt is captured — so you don't just see the final code, you see how they think,
  how they use AI, and whether they truly understand what they shipped."
- CAP: "You see *how* they work with AI."
- SHOT: scroll the chat showing the back-and-forth.

**[1:34–2:18] The evidence report (employer value)**
- VO: "When they submit, SignalLoop generates an Engineering Evidence Report."
- CAP: "Evidence — not a pass/fail."
- SHOT: employer report page loads — recommendation banner + score ring. Zoom on the ring.
- VO: "A clear recommendation, backed by a six-part rubric: public fixes, hidden-test
  generalization, the feature they built, the tests they wrote, how they collaborated with AI,
  and code quality."
- SHOT: scroll the score-breakdown bars.
- VO: "It even interprets how they framed, asked, verified, and owned the work — and drafts
  follow-up questions for your interview."
- CAP: "Frame · Ask · Verify · Own + interview questions."
- SHOT: pause on the FAVO section, then the follow-up questions list.

**[2:18–2:36] Platform / extensibility** (VO clip `05b_platform`)
- VO: "You just saw our FastAPI track, in standard and advanced modes. We started there
  because it's common — but SignalLoop isn't tied to one stack: new skills slot in easily, each
  assessment can be tailored to the employer and the role, and we're expanding across
  engineering — and beyond."
- CAP: "Any stack · standard & advanced · tailored to the role"
- SHOT: employer invite screen showing the assessment selector (**Standard FastAPI v2** /
  **Advanced FastAPI v1**) and the assessment **Details** modal. (Conveys "standard & advanced"
  + "more skills/packs.")

**[2:36–2:58] Integrity + breadth**
- VO: "Integrity is built in — AI-policy signals, paste detection, and optional proctoring roll
  into one integrity score. And a super-admin view gives operators the full picture across every
  hiring team."
- CAP: "Integrity, built in."
- SHOT: integrity banner + a webcam-snapshot thumbnail strip; quick cut to the `/admin` roster.

**[2:58–3:10] Close**

> Timing note: the platform beat adds ~16s, nudging the raw cut just over 3:00. Trim silences
> between VO clips (and tighten the report scroll) to land at/under 3:00 — or keep ~3:05, which
> is fine for web/LinkedIn.

- VO: "SignalLoop — see how engineers actually build, in the age of AI."
- CAP: "SignalLoop · <yourdomain>"
- SHOT: clean logo card + URL / "Request a demo".

## 4. Shot list (record in this order; re-sequence in edit)

1. Candidate workspace idle (hero) — for the intro resolve.
2. Open main.py → Run tests → failing output → click failing test → jump to line.
3. AI collaborator conversation (prompts in §6) — the full guide→code exchange.
4. (Optional) candidate writes a quick test / adds the enhancement code.
5. Submit flow (the confirm modal is a nice beat).
6. Employer report: recommendation + ring; score bars; AI collaboration; FAVO; follow-up
   questions; (proctoring snapshots if present).
7. Admin roster (`/admin`) — 3-second establishing shot.
8. Logo/outro card.

## 5. Demo data to stage (so screens look impressive)

We seed a **strong, realistic candidate attempt** that exercises every differentiator, then
generate its evidence report:

- A candidate who fixed the public bugs, generalized to most hidden tests, built one
  enhancement, and wrote a couple of their own tests (so the rubric bars look strong but
  honest — not a perfect 100).
- An **AI-collaboration transcript** that demonstrates progressive disclosure: a vague ask →
  Socratic guidance → the candidate articulating the approach → the focused code. This is the
  centerpiece the report's "AI collaboration" section reads from.
- A few proctoring signals (a focus-loss event or two + a webcam snapshot via the local
  data-URL fallback) so the integrity section renders with content.
- A generated Engineering Evidence Report with a solid recommendation, FAVO, and follow-up
  questions.

For the **live AI exchange on camera**, type the validated prompts in §6 — they reliably
produce the guide-then-code behavior, so the recording isn't a gamble on a model's mood.

## 6. Exact prompts to type during the AI-collaborator shot

These are validated to trigger the progressive-disclosure behavior. Type them as the candidate;
the real model responds.

Enhancement flow (recommended for the demo):
1. `I want to add an endpoint that lists all tasks for a given owner — can you write it for me?`
   → AI asks a guiding question (which route shape, what to filter on).
2. `A GET route like /users/{user_id}/tasks, returning tasks where owner_id matches`
   → AI confirms and gives the focused endpoint code.

Bug-fix beat (optional, shows minimal-lines help):
- `I think delete_task never checks the task owner, so anyone can delete any task — how do I fix that?`
  → AI gives only the minimal ownership-check lines (not the whole function).

Avoid on camera (these are coached/blocked by design — only show if illustrating the guardrail):
- "give me the full solution", "find all the bugs", "write all the tests".

## 8. Fast track — a good first cut in ~1–2 hours

Don't do the full plan for v1. Minimum path that still looks good:

1. **Tools:** Screen Studio (free trial) + ElevenLabs (free tier) + CapCut (free).
2. **Demo data:** let me seed one strong attempt + report (below) — this is the biggest
   "looks good for zero effort" lever.
3. **VO:** paste the §3 script into ElevenLabs → one MP3 (pick one voice, one take).
4. **Record** only the core scenes (§4 items 1–3 and 6) in one or two passes. Don't chase
   perfection — Screen Studio's auto-zoom does the polishing.
5. **Assemble in CapCut:** drop the VO, lay the clips under it, hit auto-captions, add one
   music track + an intro and outro title card. Export 1080p.
6. Skip for v1: the 9:16/1:1 social cuts, the test-writing shot, custom callouts (captions are
   enough).

The three levers that make it look professional with the least effort: **(a) clean demo data,
(b) Screen Studio auto-zoom, (c) the tight script.** Everything else is polish you can add later.

## 7. Recording tips for "slick"

- Move the cursor slowly and intentionally; let each screen breathe ~1s before acting.
- One idea per shot; cut between shots rather than scrolling around hunting.
- Use Screen Studio auto-zoom on: the failing test line, the AI reply, the score ring, FAVO.
- Keep captions short (3–6 words) and high-contrast; sync the keyword to the VO beat.
- Music: subtle, builds slightly at the report reveal; duck under VO.
- End on the logo card held for ~2s so the last frame is brandable (good for LinkedIn thumbnail).

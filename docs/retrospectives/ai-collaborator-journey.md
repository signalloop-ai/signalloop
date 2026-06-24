# Designing the AI Collaborator: a design journey

A retrospective on how SignalLoop's in-assessment AI collaborator went from a brittle keyword
filter to a two-component, progressive-disclosure coach — what we tried, why each version
failed, and the principles that finally worked. Written as a durable record and as raw
material for a blog post.

## The problem

SignalLoop is a coding assessment. Candidates work in a real IDE with an embedded AI
assistant — because that's how engineers actually work now. But that creates a tension:

> The assistant has to be **genuinely helpful** (or candidates give up and the signal is
> noise), while never **handing over the answer** (or it stops measuring the candidate).

Concretely, the assistant must help a candidate reason through a bug they found, explain
framework mechanics, and discuss tradeoffs — but it must not enumerate every defect, write the
whole solution, write the candidate's tests, reveal hidden tests, or make their design
decisions. And it must do this robustly against paraphrase, multi-turn conversations, and
candidates actively trying to extract answers.

That "helpful but not a cheat code" line turned out to be much harder to hold than expected.

## The journey

### V0 — Keyword/pattern matching
The MVP classified requests by string matching ("find all bugs", "full solution", …).

**Why it failed:** trivially bypassed by rephrasing. "What are all the issues" vs "walk me
through everything that could be improved" — the policy is semantic, but keywords are
syntactic. It was a UI nicety pretending to be a guardrail.

### V1 — Single LLM call (classify + generate together) + keyword fallback
We moved the decision into the model: one call returned JSON `{allowed, policy_tags, message}`,
with the keyword classifier kept as a fallback for parse/availability failures (ADR 0007).

**Why it fell short:** bundling "is this allowed?" with "what's the response?" made both jobs
fuzzier, and the model would sometimes produce a helpful answer while tagging it as a
violation (or vice versa). The classification and the pedagogy wanted to be separate concerns.

### V2 — Two-step (LLM classifier → generator) + a keyword output guard
We split it: an LLM **classifier** decided allow/block, an LLM **generator** produced the
reply, and — to be safe — a keyword **output guard** re-inspected the generator's text and
swapped in a Socratic redirect if it "looked like" a solution.

**Why it failed — and this is the central lesson:** we now had **three independent components
each making the same decision with different logic**: the LLM classifier, the Python keyword
classifier (which we also ran *during normal operation* to "validate" some tags), and the
keyword output guard. They constantly disagreed and overrode one another.

This produced a **whack-a-mole** dynamic. Every fix to one layer created a new false positive
somewhere else. A sampling of real bugs from this era:
- "make the change so only the owner can read the task" → blocked as `anti_decomposition`.
- A candidate stating a correct diagnosis ("I think the issue is my handler never compares
  owner_id") → blocked because it co-occurred with a test-failure paste.
- "in create_user I don't see duplicate-email handling, can you help with code for this?" →
  blocked as `full_solution`.
- Follow-up messages losing the topic, because history was fed in the wrong order.

We kept adding keywords and examples; the prompt grew to ~135 lines of bug-reaction examples;
the false-positive rate didn't converge. The candidate experience was: *the assistant refuses
reasonable questions*, which is exactly what makes people give up.

### V3 — Collapse to two components, one responsibility each (the structural fix)
The breakthrough was realizing the bugs were **architectural**, not prompt-tuning. We
collapsed the system to:

- **Classifier = the single source of truth for blocking.** Short, principle-based prompt. It
  decides only *abuse vs allowed*. It leans allow.
- **Generator = the single owner of the response.** It decides how to help.
- **Deleted the output guard entirely.** No second pass re-judging the generator.
- **Demoted the keyword classifier to availability-only** — it runs *only* when the LLM call
  or parse genuinely fails, and it can never override a working LLM.

Two follow-on fixes came from the same "one decision in one place" principle:
- **Context-bleed:** feeding the classifier the conversation history made it *block* legitimate
  follow-ups (a concept question + "help with this" read as building a full solution). Fix:
  **the classifier judges the current message alone**; conversation context belongs to the
  generator (an allowed-only path that can't cause a false block).
- **Generator context done right:** give the generator the real transcript (both roles, in
  chronological order) plus a "focus on the current message" rule — fixing both "lost topic"
  and "re-answered an earlier turn."
- **Workspace grounding:** give the generator the candidate's actual files so it answers about
  *their* code like a normal coding agent, not with textbook snippets.

This killed the structural false-positive engine. But it surfaced the real question we'd been
avoiding: *what should the assistant actually do when a request is allowed?*

### V4 — The pedagogy: Socratic guidance + progressive disclosure (the "proprietary" part)
Our first answer was "once the candidate identifies an issue, give them the code." Too
generous: ask for an enhancement and you got the whole endpoint; ask for a test and you got
the whole test; ask to explain a bug and you got the whole rewritten function. It was helpful
and it was a cheat code.

The owner's insight reframed it: **don't refuse — coach, and let the candidate earn the code by
showing they understand.** That became the design:

- For anything that asks to implement/fix/write, the generator decides from **what the
  candidate has demonstrated in the conversation**:
  - **Not yet shown the approach** (first ask, "just do it for me", named the goal but not the
    how) → ask one pointed Socratic question, or give a conceptual hint / point at a similar
    pattern. No code yet.
  - **Has articulated the approach** (the route + what to filter; what a test sends + asserts;
    the exact behavior to change and why) → give the code, kept tight. A **bug fix is only the
    minimal changed lines**, never the whole function.
- **Concept/syntax questions** are answered directly with a tiny snippet — that's general
  knowledge, not the assessment.

Two refinements mattered:
- **The gate is understanding, not a turn count.** An early version said "at most two
  questions" — which is a loophole (deflect twice, get the code). We replaced it with: the
  *moment* the candidate articulates the approach, give the code; if they keep deflecting
  ("just do it"), keep guiding indefinitely.
- **Allow at the classifier, gate at the generator.** Single-feature and single-test requests
  (even "write it for me") are *allowed* — the generator decides whether they've earned it.
  This keeps the classifier simple and puts the nuanced pedagogy in one place.

The result, in one real session: a candidate asks for a due-date enhancement → gets a guiding
question → describes adding a `due_date` field and rejecting past dates → and *that turn* gets
the code, before they even ask for it. Probe → understand → code. The Socratic method does the
teaching; the progressive-disclosure gate protects the signal.

## The final design

**Two LLM components + one deterministic gate + a lenient fallback:**

1. **Deterministic pre-gate** — pasted test *function code* is blocked structurally (it's the
   one gameable case that's reliably detectable without an LLM).
2. **Classifier (LLM, single source of truth for blocking)** — judges the current message
   alone; leans allow; blocks only the narrow abuse set (enumerate-all, full-solution,
   whole-test-suite, hidden-tests, choose-design, prompt-injection, anti-decomposition).
3. **Generator (LLM, owns the response)** — workspace-grounded, conversation-aware,
   progressive disclosure (guide → give code on demonstrated understanding; minimal lines for
   fixes). Output returned verbatim.
4. **Keyword fallback** — availability-only; runs solely when the LLM is unavailable; never
   overrides a working LLM.

Validated by a **live regression net** that runs the real model against scenarios grounded in
the actual seeded issues of the shipped assessment packs — because mocked tests prove the
plumbing, not the model's judgment.

## Lessons (the blog takeaways)

1. **Don't stack overlapping deciders.** If two components can each block a request, they will
   eventually disagree, and every fix to one re-breaks the other. One decision, one owner.
2. **Use the model for semantic policy; keep keywords as a degraded mode.** Pattern matching
   is a syntactic tool for a semantic problem. It belongs behind an availability fallback, not
   in the hot path overriding the model.
3. **Put context where it helps, not where it hurts.** History made the *generator* better and
   the *classifier* worse (context-bleed). Match the input to the job.
4. **Gate on demonstrated understanding, not on turns or keywords.** "Earn the code by showing
   the approach" is both better pedagogy and a tighter integrity boundary than any rule about
   counts or phrases.
5. **Lean allow; let the report catch gaming.** A guardrail that refuses real questions fails
   its actual job (candidates give up). The AI-collaboration scoring still captures patterns,
   so the live boundary can afford to be generous.
6. **Test against the real model, on real tasks.** Unit tests with a mocked LLM caught zero of
   the judgment bugs. A live regression net grounded in the real seeded issues caught several
   on the first run (including a reproducible context-bleed false positive).
7. **Mind model-specific operational quirks.** Reasoning-class models (e.g. GPT-5) need
   `max_completion_tokens` (not `max_tokens`) and a generous budget — a small budget is spent
   entirely on hidden reasoning and returns empty content. Fail loudly (log the API error),
   don't swallow it.

## Pointers
- Policy and behavior rules: `docs/prompts/ai-collaborator-policy.md`
- Decision record: `docs/decisions/0007-llm-based-ai-policy-evaluation.md`
- Implementation: `apps/api/signalloop_api/ai_policy.py`, `ai_provider.py`
- Live regression net: `apps/api/tests/test_live_ai_policy.py`
- Session-by-session detail: `docs/development/changes.md`

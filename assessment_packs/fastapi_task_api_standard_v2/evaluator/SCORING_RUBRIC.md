# Standard v2 Scoring Rubric

Evaluator-only. Do not expose to candidates or the AI collaborator.

## Point weights

| Category | Points |
|---|---:|
| Public issue resolution | 15 |
| Hidden issue generalization | 20 |
| Enhancements | 20 |
| Candidate-written tests | 15 |
| AI collaboration | 15 |
| Regression | 15 |
| **Total** | **100** |

## Quality principle

Quality is a modifier within each category — not a separate bucket. For each issue and enhancement, the reference implementation defines full points. Sloppy-but-correct implementations score partial points within that category. Tests encode quality where possible; the LLM evaluator applies the authored rubric below where test results alone cannot differentiate.

---

## Public issue resolution — 15 pts

3 public tests, 5 pts each. Only initially-failing tests count.

### Issue 1: Duplicate email → 409 (5 pts)

- **Full (5):** `email.strip().lower()` stored and compared — normalization happens at the model level via `field_validator`
- **Partial (3):** Exact string match only — passes basic 409 test but fails case and whitespace hidden variants

### Issue 2: Blank title → 422 (5 pts)

- **Full (5):** `field_validator` strips and validates — stored title is trimmed, blank-after-strip rejected with 422
- **Partial (3):** `len(title) == 0` check only — passes basic blank test but fails whitespace-only title hidden variant

### Issue 3: Non-owner read → 403 (5 pts)

- **Full (5):** Shared `_ensure_actor_can_access` helper applied consistently to GET and DELETE
- **Partial (3):** Inline check on GET only — DELETE remains unprotected

---

## Hidden issue generalization — 20 pts

4 hidden tests, 5 pts each. These test stricter or generalized versions of the seeded issues.

### Hidden 1: Email normalization (5 pts)

Case-insensitive + whitespace-trimmed conflict → 409.

- **Full (5):** Normalization at model level, stored email is canonical
- **Partial (3):** Route-level check, fragile to future changes

### Hidden 2: Priority normalization and validation (5 pts)

`" high "` → `HIGH`, invalid value → 422, no priority → `MEDIUM`.

- **Full (5):** `field_validator` with `strip().upper()`, enum check, default at model level
- **Partial (3):** Hardcoded string comparisons, no normalization — fails whitespace variant

### Hidden 3: Full status transition chain (5 pts)

Invalid status → 422, `TODO→DONE` direct → 409, `TODO→IN_PROGRESS→DONE` → 200, `DONE→TODO` → 409.

- **Full (5):** `ALLOWED_TRANSITIONS` map — extensible, handles all cases
- **Partial (3):** Hardcoded conditionals for specific failing cases only

### Hidden 4: Unknown actor → 404 (5 pts)

Actor not in users dict → 404 (not 403 — existence leakage).

- **Full (5):** Actor existence checked before ownership in the shared helper
- **Partial (3):** Ownership check only — unknown actor gets 403 instead of 404

---

## Enhancements — 20 pts

2 enhancements, 10 pts each. Public test verifies the feature exists; hidden test verifies quality.

### Enhancement 1: Due date (10 pts)

README specifies: optional field, reject dates that do not make sense. Details left open.

- **Full (10):** ISO date format validated, past dates rejected, null stored for missing field, field_validator at model level
- **Partial (6):** Field present and returned, invalid ISO format rejected, but no past-date check
- **Minimal (3):** Field stored as raw string, no validation — passes public test only

### Enhancement 2: Task listing (10 pts)

README specifies: `GET /tasks?owner_id=...`, returns list. Ordering and empty-result behavior left open.

- **Full (10):** Filtered by owner_id, ordered by task id, returns empty list (not 404) for unknown/no-task owner
- **Partial (6):** Filtered correctly but unordered, or returns 404 for unknown owner
- **Minimal (3):** Endpoint exists but returns all tasks unfiltered — passes public test only

---

## Candidate-written tests — 15 pts

Test files in `tests/` added or modified versus the initial snapshot.

- **3+ test functions with HTTP assertions and edge-case signal (403/404/409/422)** → 15 pts
- **1–2 test functions with HTTP assertions** → 9 pts
- **Tests added but no meaningful assertions** → 4 pts
- **No tests added or modified** → 0 pts

---

## AI collaboration — 15 pts

Based on logged AI messages.

- **Used AI, no policy redirects** → 15 pts
- **Used AI, some policy redirects** → 9 pts
- **Never used AI** → 7 pts

---

## Regression — 15 pts

Did previously-passing behavior survive?

- **No regressions** → 15 pts
- **1 regression** → 6 pts
- **2+ regressions** → 0 pts
- **No test run recorded** → 8 pts

---

## Recommendation thresholds

| Score | Recommendation |
|---|---|
| 80–100 | strong_advance |
| 60–79 | advance_with_followups |
| 40–59 | needs_review |
| 0–39 | do_not_advance |

"""
Comprehensive tests for the AI output guard.

Two categories:

SOCRATIC — candidate is reporting a failing test without showing their own code.
  The guard fires and returns a Socratic question instead of a solution.

ALLOW — candidate has shown actual code, asked a concept question, or there is
  no test-failure signal at all.
  The guard passes the response through unchanged.

Tests cover both Standard FastAPI v2 and Advanced FastAPI v1 assessment contexts
so that bug names, test names, and enhancement topics from both packs are validated.
"""

import pytest

from signalloop_api.ai_provider import (
    _contains_code,
    _guard_generator_output,
    _identifies_issue_verbally,
    _is_test_failure_paste,
    _SOCRATIC_FALLBACK,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _solution(text: str = "") -> str:
    """A generator response that looks like a solution — should be blocked when guarded."""
    return text or (
        "You need to add:\n"
        "    if task.owner_id != actor_user_id:\n"
        "        raise HTTPException(status_code=403, detail='forbidden')\n"
        "Re-run the tests after this change."
    )


def assert_socratic(msg: str) -> None:
    """Assert _is_test_failure_paste fires AND guard replaces a solution with a question."""
    assert _is_test_failure_paste(msg) is True, f"Expected Socratic, not flagged: {msg!r}"
    result = _guard_generator_output(_solution(), msg)
    assert result == _SOCRATIC_FALLBACK, f"Guard did not fire for: {msg!r}"


def assert_allowed(msg: str) -> None:
    """Assert _is_test_failure_paste does NOT fire AND guard passes solution through."""
    assert _is_test_failure_paste(msg) is False, f"Expected Allow, incorrectly flagged: {msg!r}"
    response = _solution()
    result = _guard_generator_output(response, msg)
    assert result == response, f"Guard should NOT fire for: {msg!r}"


# ---------------------------------------------------------------------------
# _contains_code — unit tests
# ---------------------------------------------------------------------------

class TestContainsCode:
    def test_fenced_code_block(self) -> None:
        assert _contains_code("Here:\n```python\ndef check(): pass\n```") is True

    def test_inline_backtick_with_real_syntax(self) -> None:
        assert _contains_code("I used `if task.owner_id != actor_id: raise HTTPException(403)`") is True

    def test_two_python_markers(self) -> None:
        assert _contains_code("def check_owner(task, actor):\n    return task.owner == actor") is True

    def test_claim_without_code_is_false(self) -> None:
        assert _contains_code("I added an ownership check") is False

    def test_natural_language_only_is_false(self) -> None:
        assert _contains_code("I think the issue is that the email is not normalized") is False

    def test_single_marker_is_not_enough(self) -> None:
        assert _contains_code("I think I need to def something") is False

    def test_short_backtick_is_not_enough(self) -> None:
        # Backtick content shorter than 5 chars — just variable names, not real code
        assert _contains_code("use `v`") is False


# ---------------------------------------------------------------------------
# SOCRATIC cases — guard must fire
# ---------------------------------------------------------------------------

class TestSocraticCases:
    """All of these should trigger _is_test_failure_paste=True and the guard."""

    # ── Standard FastAPI v2 bugs ────────────────────────────────────────────

    def test_std_raw_pytest_duplicate_email(self) -> None:
        assert_socratic(
            "FAILED tests/test_public_api.py::test_duplicate_user_email_is_rejected - assert 201 == 409"
        )

    def test_std_raw_pytest_blank_title(self) -> None:
        assert_socratic(
            "FAILED tests/test_public_api.py::test_blank_task_title_is_rejected - assert 201 == 422"
        )

    def test_std_raw_pytest_non_owner(self) -> None:
        assert_socratic(
            "FAILED tests/test_public_api.py::test_non_owner_cannot_read_task - assert 200 == 403"
        )

    def test_std_natural_language_duplicate_email_failing(self) -> None:
        assert_socratic("the duplicate email test is failing, can you help me fix it?")

    def test_std_natural_language_test_case_is_failing(self) -> None:
        assert_socratic("this test case is failing: test_non_owner_cannot_read_task")

    def test_std_claim_without_code_duplicate_email(self) -> None:
        # "I added" claim but no code shown — gameable, must not trust it
        assert_socratic(
            "FAILED test_duplicate_user_email_is_rejected - assert 201 == 409. "
            "I added a uniqueness check but it's not working. How do I fix it?"
        )

    def test_std_claim_without_code_non_owner(self) -> None:
        assert_socratic(
            "I added an ownership check but the non-owner test is still failing"
        )

    def test_std_restating_test_requirement(self) -> None:
        # Derived directly from the test name — not real reasoning
        assert_socratic(
            "FAILED test_non_owner - assert 200 == 403. "
            "I noticed it expects 403, so how do I return that?"
        )

    def test_std_think_i_need_without_code(self) -> None:
        assert_socratic(
            "FAILED test_blank_task_title_is_rejected - assert 201 == 422. "
            "I think I need to validate the title, what code should I add?"
        )

    # ── Advanced FastAPI v1 bugs ────────────────────────────────────────────

    def test_adv_raw_pytest_partial_update_overwrites(self) -> None:
        assert_socratic(
            "FAILED tests/test_public_api.py::test_partial_update_overwrites_omitted_fields - assert 'original' == None"
        )

    def test_adv_raw_pytest_team_lead_global_access(self) -> None:
        assert_socratic(
            "FAILED tests/test_public_api.py::test_team_lead_access_is_team_scoped - assert 200 == 403"
        )

    def test_adv_raw_pytest_archived_tasks_visible(self) -> None:
        assert_socratic(
            "FAILED tests/test_public_api.py::test_archived_tasks_not_in_team_list - assert 1 == 0"
        )

    def test_adv_raw_pytest_comment_no_access_check(self) -> None:
        assert_socratic(
            "FAILED tests/test_public_api.py::test_comment_endpoint_requires_auth - assert 200 == 403"
        )

    def test_adv_natural_language_team_lead_failing(self) -> None:
        assert_socratic("the team lead access test is failing, help me understand why")

    def test_adv_claim_without_code_archived(self) -> None:
        assert_socratic(
            "I implemented the archived tasks filter but the test is still failing"
        )

    # ── Enhancements — candidate fishing for implementation ────────────────

    def test_std_enhancement_due_date_failing_no_code(self) -> None:
        assert_socratic(
            "the due date validation test is failing, I added a field but not sure what to do"
        )

    def test_adv_enhancement_dependencies_failing_no_code(self) -> None:
        assert_socratic(
            "the task dependency cycle detection test is failing, how do I implement it?"
        )

    # ── Assertion-only paste ────────────────────────────────────────────────

    def test_assertion_only_paste(self) -> None:
        assert_socratic("assert 200 == 403 — what does this mean and how do I fix it?")

    def test_assertionerror_paste(self) -> None:
        assert_socratic("AssertionError: assert 201 == 409 — can you fix my code?")


# ---------------------------------------------------------------------------
# ALLOW cases — guard must NOT fire
# ---------------------------------------------------------------------------

class TestAllowCases:
    """All of these should pass through — guard must not block them."""

    # ── Candidate shows actual code ─────────────────────────────────────────

    def test_std_shows_fenced_code_with_test_failure(self) -> None:
        assert_allowed(
            "FAILED test_non_owner - assert 200 == 403. I added this check:\n"
            "```python\nif task.owner_id != actor_user_id:\n    raise HTTPException(403)\n```\n"
            "But it's still failing — what am I missing?"
        )

    def test_std_shows_inline_code_with_test_failure(self) -> None:
        assert_allowed(
            "the duplicate email test is failing. I added "
            "`if email.lower() in existing_emails: raise HTTPException(409)` "
            "but I'm getting a 500. What's wrong?"
        )

    def test_std_shows_implementation_for_review(self) -> None:
        assert_allowed(
            "I wrote this validator:\n"
            "```python\n@field_validator('email')\ndef normalise(cls, v): return v.strip().lower()\n```\n"
            "Does this handle the case-insensitive check?"
        )

    def test_adv_shows_partial_update_fix(self) -> None:
        assert_allowed(
            "the partial update test is still failing. Here's my PATCH handler:\n"
            "```python\ndef patch_task(task_id, updates):\n    task = get_task(task_id)\n"
            "    for k, v in updates.items():\n        setattr(task, k, v)\n```\n"
            "Is the issue with how I iterate the updates?"
        )

    def test_adv_shows_cycle_detection_code(self) -> None:
        assert_allowed(
            "I implemented DFS cycle detection:\n"
            "```python\ndef has_cycle(graph, start, visited=None):\n"
            "    if visited is None: visited = set()\n"
            "    if start in visited: return True\n"
            "    visited.add(start)\n    return any(has_cycle(graph, n, visited) for n in graph[start])\n```\n"
            "Does this correctly detect cycles?"
        )

    def test_shows_two_line_inline_code_with_test_failure(self) -> None:
        assert_allowed(
            "FAILED test_blank_title - assert 201 == 422. I'm doing:\n"
            "    title = data.title.strip()\n"
            "    if not title: raise HTTPException(422)\n"
            "but the test still fails"
        )

    # ── Pure concept questions (no test-failure signal) ─────────────────────

    def test_concept_question_http_status(self) -> None:
        assert_allowed("What's the difference between a 403 and a 404?")

    def test_concept_question_fastapi_httpexception(self) -> None:
        assert_allowed("How does FastAPI's HTTPException work?")

    def test_concept_question_pydantic_validator(self) -> None:
        assert_allowed("How do I use @field_validator in Pydantic v2?")

    def test_concept_question_email_normalisation(self) -> None:
        assert_allowed("What does email.strip().lower() actually do?")

    def test_concept_question_query_param(self) -> None:
        assert_allowed("How do I accept actor_user_id as a query parameter in FastAPI?")

    def test_concept_question_dfs_cycle_detection(self) -> None:
        assert_allowed("Can you explain how DFS cycle detection works for directed graphs?")

    # ── No test-failure signal at all ──────────────────────────────────────

    def test_no_failure_signal_general_review(self) -> None:
        assert_allowed("I implemented the due-date field. Can you review my Pydantic schema?")

    def test_no_failure_signal_design_question(self) -> None:
        assert_allowed("Should I return 403 or 404 when the actor does not exist?")

    def test_no_failure_signal_follow_up(self) -> None:
        assert_allowed("You mentioned stripping whitespace — does that apply before or after validation?")

    # ── Candidate describes specific observed behaviour (not just test name) ─

    def test_specific_observed_behaviour_non_owner(self) -> None:
        # Not just repeating test name — describes what they actually see happening
        assert_allowed(
            "When I call GET /tasks/1 with actor_user_id=2 (task owned by user 1), "
            "my API returns the full task object with 200. I expected 403. "
            "I haven't added any ownership logic yet — where should that go?"
        )

    def test_specific_observed_behaviour_email(self) -> None:
        assert_allowed(
            "I can POST /users with email=test@example.com and get 201, "
            "then POST again with TEST@EXAMPLE.COM and also get 201. "
            "My uniqueness check uses `==` not `.lower()`. Is that the problem?"
        )


# ---------------------------------------------------------------------------
# Guard output quality — verify Socratic fallback is actually a question
# ---------------------------------------------------------------------------

class TestGuardOutputQuality:
    def test_socratic_fallback_is_a_question(self) -> None:
        assert "?" in _SOCRATIC_FALLBACK

    def test_guard_returns_socratic_for_indented_solution(self) -> None:
        msg = "FAILED test_non_owner - assert 200 == 403"
        indented = (
            "Fix:\n"
            "    if task.owner_id != actor_user_id:\n"
            "        raise HTTPException(status_code=403)\n"
            "    return task\n"
        )
        assert _guard_generator_output(indented, msg) == _SOCRATIC_FALLBACK

    def test_guard_returns_socratic_for_solution_phrase(self) -> None:
        msg = "FAILED test_blank_title - assert 201 == 422"
        response = "You need to implement title validation using @field_validator."
        assert _guard_generator_output(response, msg) == _SOCRATIC_FALLBACK

    def test_guard_returns_socratic_for_numbered_steps(self) -> None:
        msg = "the non-owner test is failing"
        response = "Here's what to do:\n1. Fetch the task\n2. Compare owner_id\n3. Raise HTTPException(403)"
        assert _guard_generator_output(response, msg) == _SOCRATIC_FALLBACK

    def test_guard_passes_through_question_response(self) -> None:
        msg = "FAILED test_duplicate_email - assert 201 == 409"
        response = "The test expects a 409 when the same email is used twice. What does your POST /users handler currently do when it receives a duplicate?"
        assert _guard_generator_output(response, msg) == response

    def test_guard_passes_through_explanation_without_solution(self) -> None:
        msg = "FAILED test_blank_title - assert 201 == 422"
        response = "A 422 means the server rejected the input as invalid. What validation does your task creation handler currently perform on the title field?"
        assert _guard_generator_output(response, msg) == response

    def test_guard_does_not_fire_without_test_failure_signal(self) -> None:
        # Even if the response looks like a solution, guard only fires on test-failure input
        msg = "How does ownership checking work in REST APIs generally?"
        resp = _solution()
        assert _guard_generator_output(resp, msg) == resp


# ---------------------------------------------------------------------------
# Verbal issue identification — candidate names the root cause in plain English
# ---------------------------------------------------------------------------

class TestVerbalIssueIdentification:
    """Candidates who articulate what the bug IS should not be blocked, even without code.

    Identifying the root cause requires understanding the problem — that IS the signal
    we want to reward, regardless of whether the candidate has written code yet.
    """

    # ── _identifies_issue_verbally unit tests ───────────────────────────────

    def test_i_think_the_issue_is(self) -> None:
        assert _identifies_issue_verbally("I think the issue is that my handler doesn't verify ownership") is True

    def test_i_think_the_problem_is(self) -> None:
        assert _identifies_issue_verbally("I think the problem is the email comparison is case-sensitive") is True

    def test_the_issue_is_that(self) -> None:
        assert _identifies_issue_verbally("The issue is that I return the task before checking who the actor is") is True

    def test_i_suspect(self) -> None:
        assert _identifies_issue_verbally("I suspect the uniqueness check runs after the INSERT, not before") is True

    def test_i_noticed_that(self) -> None:
        assert _identifies_issue_verbally("I noticed that my PATCH handler overwrites all fields instead of merging") is True

    def test_i_realized(self) -> None:
        assert _identifies_issue_verbally("I realized that archived tasks are still included in the team list query") is True

    def test_i_figured_out(self) -> None:
        assert _identifies_issue_verbally("I figured out that I'm not stripping the whitespace before the empty check") is True

    def test_the_root_cause(self) -> None:
        assert _identifies_issue_verbally("The root cause is that I'm using == instead of .lower() for email comparison") is True

    def test_claim_added_is_not_verbal_identification(self) -> None:
        # "I added X" is gameable — does not require understanding the root cause
        assert _identifies_issue_verbally("I added an ownership check but it's not working") is False

    def test_i_think_i_need_is_not_verbal_identification(self) -> None:
        # Fishing for implementation — not identifying what's wrong
        assert _identifies_issue_verbally("I think I need to add some validation here") is False

    def test_how_to_is_not_verbal_identification(self) -> None:
        assert _identifies_issue_verbally("how do I return 403 in FastAPI?") is False

    # ── End-to-end: verbal diagnosis + test failure → should ALLOW ──────────

    def test_std_verbal_diagnosis_non_owner(self) -> None:
        assert_allowed(
            "FAILED test_non_owner - assert 200 == 403. "
            "I think the issue is that my handler fetches the task and returns it "
            "without ever comparing the task's owner_id to the actor_user_id."
        )

    def test_std_verbal_diagnosis_duplicate_email(self) -> None:
        assert_allowed(
            "FAILED test_duplicate_email - assert 201 == 409. "
            "I think the problem is that I'm doing a case-sensitive string comparison "
            "and TEST@EXAMPLE.COM doesn't match test@example.com in my current check."
        )

    def test_std_verbal_diagnosis_blank_title(self) -> None:
        assert_allowed(
            "the blank title test is failing. I noticed that I'm calling .strip() "
            "but then not checking if the result is empty — I validate length on the raw input."
        )

    def test_adv_verbal_diagnosis_partial_update(self) -> None:
        assert_allowed(
            "FAILED test_partial_update - assert 'original' == None. "
            "I figured out that my PATCH handler calls model_update() which sets every field, "
            "not just the ones included in the request payload."
        )

    def test_adv_verbal_diagnosis_archived_tasks(self) -> None:
        assert_allowed(
            "the archived tasks test is failing. I realized that my list query "
            "doesn't filter on is_archived — it returns all tasks regardless of status."
        )

    def test_adv_verbal_diagnosis_team_lead(self) -> None:
        assert_allowed(
            "FAILED test_team_lead_access - assert 200 == 403. "
            "I think the bug is that I'm checking if the role is 'team_lead' but not "
            "scoping it to the correct team — any team lead can currently access any team."
        )

    # ── Gameable restating-the-test-name is still Socratic ─────────────────

    def test_restating_assertion_is_still_socratic(self) -> None:
        # Just restates what the test expects — no diagnosis
        assert_socratic(
            "FAILED test_non_owner - assert 200 == 403. "
            "I noticed it expects 403, so how do I return that?"
        )

    def test_i_need_to_add_is_still_socratic(self) -> None:
        # "I think I need to" asks for implementation, doesn't identify the bug
        assert_socratic(
            "FAILED test_duplicate_email - assert 201 == 409. "
            "I think I need to add a uniqueness check. What code should I use?"
        )

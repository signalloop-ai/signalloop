import json
from typing import Protocol

import httpx

from signalloop_api.ai_policy import (
    AIDecision,
    ClassifierDecision,
    CLASSIFIER_PROMPT,
    DESIGN_CHOICE_REDIRECT_MESSAGE,
    DISALLOWED_TAGS,
    GENERATOR_PROMPT,
    REDIRECT_MESSAGE,
    SOCRATIC_REDIRECT_MESSAGE,
    TEST_PASTE_REDIRECT_MESSAGE,
    fallback_classify,
    parse_classifier_response,
)
from signalloop_api.config import settings


class AIProvider(Protocol):
    def evaluate(self, message: str, context: dict | None, recent_messages: list[str]) -> AIDecision:
        ...


class LocalGuidanceProvider:
    def evaluate(self, message: str, context: dict | None, recent_messages: list[str]) -> AIDecision:
        decision = fallback_classify(message, recent_messages)
        if not decision.allowed:
            return AIDecision(allowed=False, policy_tags=decision.tags, message=decision.redirect_message or REDIRECT_MESSAGE)
        context_note = ""
        if context and context.get("path"):
            context_note = f" For `{context['path']}`, focus on the specific behavior you selected."
        return AIDecision(
            allowed=True,
            policy_tags=[],
            message=(
                "I can help with one candidate-identified issue or one failing public behavior at a time."
                f"{context_note} Describe the observed behavior, expected behavior, and the smallest public test or code path that demonstrates the gap."
            ),
        )


class OpenAIProvider:
    def __init__(self, api_key: str, model: str, classifier_model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.generator_model = model
        self.classifier_model = classifier_model

    def _call_openai(self, system: str, user: str, model: str, max_tokens: int, json_mode: bool = False) -> str:
        """Single OpenAI Chat Completions call. Returns the response text."""
        payload: dict = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return str(resp.json()["choices"][0]["message"]["content"]).strip()

    def evaluate(self, message: str, context: dict | None, recent_messages: list[str]) -> AIDecision:
        # Build classifier user content — include recent messages for anti_decomposition detection
        history_lines = "\n".join(f"[candidate] {m}" for m in recent_messages[-4:]) if recent_messages else ""
        if history_lines:
            classifier_user = "Recent messages:\n" + history_lines + "\n\nCurrent message: " + message
        else:
            classifier_user = "Current message: " + message

        # Step 1: Classify
        try:
            raw_classification = self._call_openai(
                CLASSIFIER_PROMPT, classifier_user, self.classifier_model, max_tokens=80, json_mode=True
            )
            clf = parse_classifier_response(raw_classification, message, recent_messages)
        except Exception:
            # Network/API failure → fall back to pattern classifier
            decision = fallback_classify(message, recent_messages)
            clf = ClassifierDecision(
                allowed=decision.allowed,
                tag=decision.tags[0] if decision.tags and decision.tags != ["general_allowed"] else None,
            )

        if not clf.allowed:
            tag = clf.tag or ""
            if tag == "no_issue_identified":
                redirect = SOCRATIC_REDIRECT_MESSAGE
            elif tag == "choose_design":
                redirect = DESIGN_CHOICE_REDIRECT_MESSAGE
            elif tag == "test_paste_derivation":
                redirect = TEST_PASTE_REDIRECT_MESSAGE
            else:
                redirect = REDIRECT_MESSAGE
            return AIDecision(allowed=False, policy_tags=[tag] if tag else [], message=redirect)

        # Step 2: Generate — include recent candidate messages so the generator
        # can maintain topic coherence across follow-up messages.
        if recent_messages:
            history = "\n".join(f"Candidate: {m}" for m in recent_messages[-3:])
            user_content = f"Recent conversation:\n{history}\n\nCurrent message: {message}"
        else:
            user_content = message

        if context:
            path = context.get("path", "")
            content = context.get("content", "")
            user_content = f"Selected file: {path}\n```\n{content}\n```\n\n{user_content}"

        try:
            response_text = self._call_openai(
                GENERATOR_PROMPT, user_content, self.generator_model, max_tokens=200
            )
        except Exception:
            response_text = "I could not generate a response right now."

        return AIDecision(allowed=True, policy_tags=[], message=_guard_generator_output(response_text, message))


_SOLUTION_PATTERNS = [
    "raise HTTPException",
    "raise ValueError",
    "if actor_user_id",
    "if task.owner",
    "email.strip().lower()",
    "email_norm",
    "status_code=403",
    "status_code=409",
    "status_code=422",
    "@field_validator",
    "@validator",
    "You need to add",
    "You need to implement",
    "You need to enforce",
    "You need to check",
    "- Before:",
    "- After:",
]

# Signals that the candidate is reporting a failing test rather than showing their own work.
# Covers raw pytest output AND natural-language references to a failing test.
_TEST_FAILURE_SIGNALS = [
    # Raw pytest output
    "FAILED tests/",
    "FAILED test_",
    "AssertionError: assert ",
    "E       assert ",
    "assert 200 == ",
    "assert 201 == ",
    "assert 400 == ",
    "assert 404 == ",
    "assert 422 == ",
    "assert 403 == ",
    "assert 409 == ",
    # Natural-language test references
    "test is failing",
    "test case is failing",
    "test is still failing",
    "test case fails",
    "this test fails",
    "test failing",
    "failing test",
]

_SOCRATIC_FALLBACK = (
    "What does your current handler do in that scenario? "
    "Walk me through what happens in your code when this request comes in."
)


def _contains_code(message: str) -> bool:
    """True if the message contains actual code the candidate has written.

    Requires either an explicit code fence or multiple Python-syntax markers —
    just claiming 'I added X' without showing code does not qualify.
    """
    if "```" in message:
        return True
    # Inline backtick with real syntax: `if ...:` or `def ...` etc.
    import re
    if re.search(r"`[^`]{5,}`", message):
        return True
    # At least two distinct Python-syntax markers in the same message
    code_markers = ["def ", "class ", "return ", "raise ", "    if ", "    return ", "    raise "]
    found = sum(1 for m in code_markers if m in message)
    return found >= 2


# Signals that the candidate has identified the root cause of the issue in plain English.
# Articulating a specific diagnosis (without code) is also genuine insight and should not
# be blocked — it requires understanding the problem, not just reading the test name.
_VERBAL_ISSUE_IDENTIFICATION = [
    "i think the issue is",
    "i think the problem is",
    "i think the bug is",
    "i think it's because",
    "i think it is because",
    "the issue is that",
    "the problem is that",
    "the bug is that",
    "i believe the issue",
    "i believe the problem",
    "i suspect",
    "i noticed that",
    "i realized that",
    "i figured out",
    "i identified",
    "the root cause",
    "i think my handler",
    "i think my code is",
    "i think my code doesn",
]


def _identifies_issue_verbally(message: str) -> bool:
    """True if the candidate articulates a specific diagnosis in plain English.

    Distinguishes genuine reasoning ("I think the issue is that my handler doesn't check
    ownership") from gameable claims ("I added X") or mere test restatement ("the test
    expects 403, how do I return that?").
    """
    lower = message.lower()
    return any(sig in lower for sig in _VERBAL_ISSUE_IDENTIFICATION)


def _is_test_failure_paste(message: str) -> bool:
    """True when the message references a failing test AND the candidate has shown no real work.

    Real work = actual code in the message OR a verbal diagnosis of the root cause.
    Mere claims like "I added X" are not sufficient — they are trivially derived from
    reading the test name and do not demonstrate understanding.
    """
    lower = message.lower()
    has_failure_signal = any(sig.lower() in lower for sig in _TEST_FAILURE_SIGNALS)
    if not has_failure_signal:
        return False
    if _contains_code(message):
        return False
    if _identifies_issue_verbally(message):
        return False
    return True


def _guard_generator_output(response: str, original_message: str) -> str:
    """Post-generation check: only enforce Socratic constraint when candidate pasted raw test output."""
    if not _is_test_failure_paste(original_message):
        # Candidate identified the problem themselves — allow code responses freely.
        return response

    lower = response.lower()

    # Count indented code lines (solution code is usually indented)
    indented_lines = sum(1 for line in response.splitlines() if line.startswith("    ") or line.startswith("\t"))
    if indented_lines >= 3:
        return _SOCRATIC_FALLBACK

    # Detect solution-shaped phrases
    if any(pat.lower() in lower for pat in _SOLUTION_PATTERNS):
        return _SOCRATIC_FALLBACK

    # Detect multi-step instructions (numbered lists 1. 2. 3.)
    numbered_steps = sum(1 for line in response.splitlines() if line.strip()[:2] in {"1.", "2.", "3.", "4."})
    if numbered_steps >= 2:
        return _SOCRATIC_FALLBACK

    return response


def extract_response_text(payload: dict) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"])
    output = payload.get("output", [])
    text_parts: list[str] = []
    for item in output:
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                text_parts.append(str(content["text"]))
    return "\n".join(text_parts).strip() or "{}"


def parse_ai_decision(raw: str, original_message: str, recent_messages: list[str]) -> AIDecision:
    """Parse the LLM JSON response. Falls back to pattern classification on parse failure."""
    try:
        data = json.loads(raw)
        allowed = bool(data.get("allowed", True))
        policy_tags = [t for t in data.get("policy_tags", []) if isinstance(t, str)]
        message = str(data.get("message", "")).strip()

        # If the LLM said allowed but included a disallowed tag, trust the tag.
        if policy_tags and any(t in DISALLOWED_TAGS for t in policy_tags):
            allowed = False
        if not allowed and not message:
            message = SOCRATIC_REDIRECT_MESSAGE if "no_issue_identified" in policy_tags else REDIRECT_MESSAGE
        if allowed and not message:
            message = "I could not generate a response."

        return AIDecision(allowed=allowed, policy_tags=policy_tags, message=message)
    except (json.JSONDecodeError, KeyError, TypeError):
        decision = fallback_classify(original_message, recent_messages)
        if not decision.allowed:
            msg = decision.redirect_message or REDIRECT_MESSAGE
        else:
            msg = "I could not generate a response."
        return AIDecision(allowed=decision.allowed, policy_tags=decision.tags, message=msg)


def get_ai_provider() -> AIProvider:
    if settings.openai_api_key:
        return OpenAIProvider(settings.openai_api_key, settings.openai_model, classifier_model=settings.openai_classifier_model)
    return LocalGuidanceProvider()

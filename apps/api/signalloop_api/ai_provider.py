import json
from typing import Protocol

import httpx

from signalloop_api.ai_policy import (
    AIDecision,
    ClassifierDecision,
    CLASSIFIER_PROMPT,
    DISALLOWED_TAGS,
    GENERATOR_PROMPT,
    REDIRECT_MESSAGE,
    SOCRATIC_REDIRECT_MESSAGE,
    TEST_PASTE_REDIRECT_MESSAGE,
    fallback_classify,
    is_pasted_test_code,
    parse_classifier_response,
    redirect_message_for_tag,
)
from signalloop_api.config import settings


class AIProvider(Protocol):
    def evaluate(
        self,
        message: str,
        context: dict | None,
        recent_messages: list[str],
        recent_turns: list[tuple[str, str]] | None = None,
        workspace_files: dict[str, str] | None = None,
    ) -> AIDecision:
        ...


class LocalGuidanceProvider:
    def evaluate(
        self,
        message: str,
        context: dict | None,
        recent_messages: list[str],
        recent_turns: list[tuple[str, str]] | None = None,
        workspace_files: dict[str, str] | None = None,
    ) -> AIDecision:
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


def _format_history(recent_turns: list[tuple[str, str]] | None, recent_messages: list[str]) -> str:
    """Build the generator's conversation context.

    Prefers the real (role, message) transcript so the generator sees its OWN prior answers
    (needed to resolve "make that change for me") and can tell that earlier candidate asks
    were already handled. Falls back to the candidate-only list when no transcript is supplied.
    Each line is truncated so a long pasted message can't blow up the prompt.
    """
    if recent_turns:
        lines = []
        for role, text in recent_turns[-6:]:
            label = "Candidate" if role == "candidate" else "You (assistant)"
            lines.append(f"{label}: {text[:400]}")
        return "\n".join(lines)
    if recent_messages:
        return "\n".join(f"Candidate: {m[:400]}" for m in recent_messages[-3:])
    return ""


def _build_generator_user_content(
    message: str,
    context: dict | None,
    history: str,
    workspace_files: dict[str, str] | None,
) -> str:
    """Assemble the generator's user message the way a coding agent sees a request: the
    candidate's current code, what they're focused on, the conversation so far, then the
    actual question."""
    blocks: list[str] = []

    if workspace_files:
        files_block = "\n\n".join(f"--- {path} ---\n{content}" for path, content in workspace_files.items())
        blocks.append(
            "The candidate's current workspace files (their code as it stands right now):\n"
            f"{files_block}"
        )

    if context and context.get("path"):
        path = context["path"]
        content = context.get("content")
        if content and not workspace_files:
            # No workspace available — fall back to the selected snippet as the only code.
            blocks.append(f"Selected file: {path}\n```\n{content}\n```")
        else:
            # Workspace already carries the code; the selection is just a focus hint.
            blocks.append(f"The candidate is currently looking at: {path}")

    if history:
        blocks.append(
            "Conversation so far, for REFERENCE ONLY — these turns are already handled. Use them "
            "only to resolve references like 'that' or 'it'. Do NOT re-answer them or volunteer "
            "changes the candidate did not just ask for:\n"
            f"{history}"
        )

    blocks.append("Now answer ONLY the candidate's current message:\n" + message)
    return "\n\n".join(blocks)


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

    def evaluate(
        self,
        message: str,
        context: dict | None,
        recent_messages: list[str],
        recent_turns: list[tuple[str, str]] | None = None,
        workspace_files: dict[str, str] | None = None,
    ) -> AIDecision:
        # recent_messages: candidate-only, chronological (oldest -> newest), NOT including the
        # current message. Used only by the degraded keyword fallback.
        # recent_turns: the real (role, message) transcript of recent turns, chronological,
        # for the generator so it can resolve references and not re-answer handled requests.
        # workspace_files: the candidate's current code ({path: content}), candidate-visible
        # only, so the generator can ground answers in their actual implementation.

        # Deterministic gate: pasting actual test function code lets the candidate reverse the
        # fix out of the test, which skips the reasoning being assessed. This is structural,
        # not phrase-matching, so it is reliable and does not need the LLM.
        if is_pasted_test_code(message):
            return AIDecision(
                allowed=False,
                policy_tags=["test_paste_derivation"],
                message=TEST_PASTE_REDIRECT_MESSAGE,
            )

        # Step 1 — Classify (the single source of truth for blocking).
        # The classifier judges the CURRENT message on its own merits. Feeding it prior turns
        # caused context-bleed false positives (e.g. a concept question followed by "help me
        # with code for this" was mis-read as full_solution). Conversation context belongs to
        # the generator — an allowed-only path that cannot cause a false block — and it still
        # receives recent_messages below.
        classifier_user = "Current message: " + message

        try:
            raw_classification = self._call_openai(
                CLASSIFIER_PROMPT, classifier_user, self.classifier_model, max_tokens=80, json_mode=True
            )
            clf = parse_classifier_response(raw_classification, message, recent_messages)
        except Exception:
            # Network/API failure -> degraded, lenient pattern fallback.
            decision = fallback_classify(message, recent_messages)
            clf = ClassifierDecision(
                allowed=decision.allowed,
                tag=decision.tags[0] if decision.tags and decision.tags != ["general_allowed"] else None,
            )

        if not clf.allowed:
            return AIDecision(
                allowed=False,
                policy_tags=[clf.tag] if clf.tag else [],
                message=redirect_message_for_tag(clf.tag),
            )

        # Step 2 — Generate. The generator owns the give-code-vs-coach decision (and only it
        # does). Whatever it returns is returned to the candidate verbatim — there is no
        # second keyword pass re-judging its output.
        history = _format_history(recent_turns, recent_messages)
        user_content = _build_generator_user_content(message, context, history, workspace_files)

        try:
            response_text = self._call_openai(
                GENERATOR_PROMPT, user_content, self.generator_model, max_tokens=350
            )
        except Exception:
            response_text = "I could not generate a response right now."

        return AIDecision(allowed=True, policy_tags=[], message=response_text)


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
    """Parse a single-call LLM JSON response. Falls back to pattern classification on failure."""
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

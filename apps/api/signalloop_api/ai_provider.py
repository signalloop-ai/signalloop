import json
from typing import Protocol

import httpx

from signalloop_api.ai_policy import AIDecision, DISALLOWED_TAGS, REDIRECT_MESSAGE, SYSTEM_PROMPT, fallback_classify
from signalloop_api.config import settings


class AIProvider(Protocol):
    def evaluate(self, message: str, context: dict | None, recent_messages: list[str]) -> AIDecision:
        ...


class LocalGuidanceProvider:
    def evaluate(self, message: str, context: dict | None, recent_messages: list[str]) -> AIDecision:
        decision = fallback_classify(message, recent_messages)
        if not decision.allowed:
            return AIDecision(allowed=False, policy_tags=decision.tags, message=REDIRECT_MESSAGE)
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
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def evaluate(self, message: str, context: dict | None, recent_messages: list[str]) -> AIDecision:
        user_content = message
        if context:
            user_content = f"Candidate-selected context:\n{context}\n\nCandidate question:\n{message}"

        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "input": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "max_output_tokens": 700,
                "reasoning": {"effort": "minimal"},
                "text": {"format": {"type": "json_object"}},
            },
            timeout=30,
        )
        response.raise_for_status()
        raw = extract_response_text(response.json())
        return parse_ai_decision(raw, message, recent_messages)


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
        message = str(data.get("message", "")).strip() or "I could not generate a response."

        # If the LLM said allowed but included a disallowed tag, trust the tag.
        if policy_tags and any(t in DISALLOWED_TAGS for t in policy_tags):
            allowed = False
        if not allowed and not message:
            message = REDIRECT_MESSAGE

        return AIDecision(allowed=allowed, policy_tags=policy_tags, message=message)
    except (json.JSONDecodeError, KeyError, TypeError):
        decision = fallback_classify(original_message, recent_messages)
        msg = REDIRECT_MESSAGE if not decision.allowed else "I could not generate a response."
        return AIDecision(allowed=decision.allowed, policy_tags=decision.tags, message=msg)


def get_ai_provider() -> AIProvider:
    if settings.openai_api_key:
        return OpenAIProvider(settings.openai_api_key, settings.openai_model)
    return LocalGuidanceProvider()

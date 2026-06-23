from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from signalloop_api.ai_provider import AIProvider, get_ai_provider
from signalloop_api.audit import record_audit_event
from signalloop_api.database import get_session
from signalloop_api.models import AIInteraction, AssessmentAttempt
from signalloop_api.schemas import AIMessageRequest, AIMessageResponse
from signalloop_api.timebox import enforce_not_expired


router = APIRouter()

DISALLOWED_CONTEXT_PARTS = {"evaluator", "hidden_tests", "REFERENCE_SOLUTION_NOTES.md", "SCORING_RUBRIC.md"}


def validate_selected_context(selected_context: dict | None) -> dict | None:
    if selected_context is None:
        return None
    path = str(selected_context.get("path", ""))
    if any(part in path for part in DISALLOWED_CONTEXT_PARTS):
        raise HTTPException(status_code=400, detail="Evaluator-only context is not allowed")
    content = selected_context.get("content")
    if isinstance(content, str) and len(content) > 6000:
        selected_context = {**selected_context, "content": content[:6000]}
    return selected_context


@router.post("/candidate/invites/{invite_token}/ai/messages", response_model=AIMessageResponse)
def send_ai_message(
    invite_token: str,
    payload: AIMessageRequest,
    session: Session = Depends(get_session),
    provider: AIProvider = Depends(get_ai_provider),
) -> AIMessageResponse:
    attempt = session.scalar(
        select(AssessmentAttempt).where(AssessmentAttempt.invite_token == invite_token)
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    if attempt.status == "submitted":
        raise HTTPException(status_code=409, detail="Attempt is already submitted")
    enforce_not_expired(session, attempt)

    selected_context = validate_selected_context(payload.selected_context)
    # Fetch the 6 most recent candidate messages, then reverse to chronological order
    # (oldest -> newest) so the classifier and generator read the conversation in the order
    # it happened. The current message is passed separately and is not yet persisted.
    recent_messages = [
        interaction.message
        for interaction in reversed(
            session.scalars(
                select(AIInteraction)
                .where(AIInteraction.attempt_id == attempt.id)
                .where(AIInteraction.role == "candidate")
                .order_by(AIInteraction.id.desc())
                .limit(6)
            ).all()
        )
    ]

    decision = provider.evaluate(payload.message, selected_context, recent_messages)

    session.add(
        AIInteraction(
            attempt_id=attempt.id,
            role="candidate",
            message=payload.message,
            selected_context=selected_context,
            policy_tags=decision.policy_tags,
        )
    )
    session.add(
        AIInteraction(
            attempt_id=attempt.id,
            role="assistant",
            message=decision.message,
            selected_context=None,
            policy_tags=decision.policy_tags,
        )
    )
    record_audit_event(
        session,
        "ai.message",
        actor_type="candidate",
        attempt_id=attempt.id,
        event_metadata={"allowed": decision.allowed, "policy_tags": decision.policy_tags},
    )
    session.commit()

    return AIMessageResponse(
        message=decision.message,
        allowed=decision.allowed,
        policy_tags=decision.policy_tags,
    )

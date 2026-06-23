from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from signalloop_api.ai_provider import AIProvider, get_ai_provider
from signalloop_api.audit import record_audit_event
from signalloop_api.database import get_session
from signalloop_api.models import AIInteraction, AssessmentAttempt
from signalloop_api.schemas import AIMessageRequest, AIMessageResponse
from signalloop_api.timebox import enforce_not_expired, latest_snapshot


router = APIRouter()

DISALLOWED_CONTEXT_PARTS = {"evaluator", "hidden_tests", "REFERENCE_SOLUTION_NOTES.md", "SCORING_RUBRIC.md"}

# Candidate source the collaborator may read as workspace context (like a normal coding agent).
WORKSPACE_INCLUDE_DIRS = ("task_api/", "tests/")
WORKSPACE_MAX_CHARS = 16000


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


def candidate_workspace_files(snapshot_files: dict | None) -> dict[str, str]:
    """The candidate's current source files to hand the collaborator as workspace context.

    Snapshots only ever contain candidate-visible files, but we still filter defensively:
    evaluator/hidden paths are excluded, and only candidate source under task_api/ and tests/
    is included (skip lockfiles/config/readme noise), bounded by a total size cap.
    """
    if not snapshot_files:
        return {}
    workspace: dict[str, str] = {}
    total = 0
    for path, content in snapshot_files.items():
        if any(part in path for part in DISALLOWED_CONTEXT_PARTS):
            continue
        if not path.endswith(".py") or not path.startswith(WORKSPACE_INCLUDE_DIRS):
            continue
        if not isinstance(content, str):
            continue
        if total + len(content) > WORKSPACE_MAX_CHARS:
            continue
        workspace[path] = content
        total += len(content)
    return workspace


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
    # Fetch the most recent interactions, newest-first, then reverse to chronological order
    # (oldest -> newest). The current message is passed separately and is not yet persisted.
    recent_interactions = list(
        reversed(
            session.scalars(
                select(AIInteraction)
                .where(AIInteraction.attempt_id == attempt.id)
                .order_by(AIInteraction.id.desc())
                .limit(8)
            ).all()
        )
    )
    # Candidate-only list for the degraded keyword fallback (assistant redirect text would
    # false-trigger its abuse patterns). The full transcript goes to the generator so it can
    # resolve references and avoid re-answering already-handled requests.
    recent_messages = [i.message for i in recent_interactions if i.role == "candidate"][-6:]
    recent_turns = [(i.role, i.message) for i in recent_interactions]

    # Give the collaborator the candidate's current code so it answers about their actual
    # implementation, the way a regular coding agent would.
    workspace_files = candidate_workspace_files(getattr(latest_snapshot(session, attempt), "files", None))

    decision = provider.evaluate(
        payload.message,
        selected_context,
        recent_messages,
        recent_turns=recent_turns,
        workspace_files=workspace_files,
    )

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

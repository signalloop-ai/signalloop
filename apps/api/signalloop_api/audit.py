from sqlalchemy.orm import Session

from signalloop_api.models import AuditEvent


def record_audit_event(
    session: Session,
    event_type: str,
    *,
    actor_type: str = "system",
    attempt_id: int | None = None,
    event_metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type,
        actor_type=actor_type,
        attempt_id=attempt_id,
        event_metadata=event_metadata or {},
    )
    session.add(event)
    return event

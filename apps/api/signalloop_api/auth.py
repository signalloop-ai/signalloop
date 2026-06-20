from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from signalloop_api.config import settings
from signalloop_api.database import get_session
from signalloop_api.models import Employer


@dataclass(frozen=True)
class EmployerIdentity:
    clerk_user_id: str
    email: str


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _make_jwks_client() -> PyJWKClient | None:
    if not settings.clerk_jwks_url:
        return None
    # Module-level singleton so the JWKS key cache persists across requests.
    # Re-creating PyJWKClient per request throws away the cache and forces a
    # fresh HTTPS fetch every time, which can stall for 15s on TCP timeout.
    return PyJWKClient(settings.clerk_jwks_url, cache_keys=True)


_jwks_client: PyJWKClient | None = _make_jwks_client()


def verify_clerk_token(token: str) -> EmployerIdentity:
    if not _jwks_client or not settings.clerk_jwt_issuer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Clerk JWT verification is not configured",
        )

    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_jwt_issuer,
            options={"verify_aud": False},
        )
    except (InvalidTokenError, PyJWKClientError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid employer token") from exc

    clerk_user_id = claims.get("sub")
    if not isinstance(clerk_user_id, str) or not clerk_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid employer token")

    email = claims.get("email") or claims.get("email_address") or f"{clerk_user_id}@clerk.local"
    return EmployerIdentity(clerk_user_id=clerk_user_id, email=str(email))


def get_or_create_employer(session: Session, identity: EmployerIdentity) -> Employer:
    employer = session.scalar(select(Employer).where(Employer.clerk_user_id == identity.clerk_user_id))
    if employer is not None:
        if employer.email != identity.email:
            email_in_use = session.scalar(select(Employer.id).where(Employer.email == identity.email))
            if email_in_use in {None, employer.id}:
                employer.email = identity.email
        return employer

    email = identity.email
    email_in_use = session.scalar(select(Employer.id).where(Employer.email == email))
    if email_in_use is not None:
        email = f"{identity.clerk_user_id}@clerk.local"

    employer = Employer(
        clerk_user_id=identity.clerk_user_id,
        email=email,
        company_name=None,
    )
    session.add(employer)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        employer = session.scalar(select(Employer).where(Employer.clerk_user_id == identity.clerk_user_id))
        if employer is not None:
            return employer
        employer = Employer(
            clerk_user_id=identity.clerk_user_id,
            email=f"{identity.clerk_user_id}@clerk.local",
            company_name=None,
        )
        session.add(employer)
        session.flush()
    return employer


def get_current_employer(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> Employer:
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Employer authentication required")
    identity = verify_clerk_token(token)
    return get_or_create_employer(session, identity)

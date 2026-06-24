from dataclasses import dataclass

import httpx
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

    # Clerk's default session token does NOT include an email claim, so we resolve the user's
    # primary email from the Clerk Backend API. This is required for the (email-based)
    # super-admin role assignment to work at all — without it every login falls back to a
    # synthetic @clerk.local address that can never match SUPER_ADMIN_EMAILS.
    email = claims.get("email") or claims.get("email_address")
    if not email:
        email = _resolve_email_from_clerk(clerk_user_id)
    email = email or f"{clerk_user_id}@clerk.local"
    return EmployerIdentity(clerk_user_id=clerk_user_id, email=str(email))


_email_cache: dict[str, str] = {}


def _resolve_email_from_clerk(clerk_user_id: str) -> str | None:
    """Look up a Clerk user's primary email via the Backend API (cached per user_id).

    Returns None if no secret key is configured or the lookup fails; callers fall back to a
    synthetic address so authentication still succeeds (the user just won't be matched as an
    admin).
    """
    if not settings.clerk_secret_key:
        return None
    cached = _email_cache.get(clerk_user_id)
    if cached:
        return cached
    try:
        resp = httpx.get(
            f"https://api.clerk.com/v1/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        primary_id = data.get("primary_email_address_id")
        emails = {
            e.get("id"): e.get("email_address")
            for e in data.get("email_addresses", [])
            if e.get("email_address")
        }
        email = emails.get(primary_id) or next(iter(emails.values()), None)
    except Exception:
        return None
    if email:
        _email_cache[clerk_user_id] = email
    return email


def get_or_create_employer(session: Session, identity: EmployerIdentity) -> Employer:
    employer = session.scalar(select(Employer).where(Employer.clerk_user_id == identity.clerk_user_id))
    if employer is not None:
        if employer.email != identity.email:
            email_in_use = session.scalar(select(Employer.id).where(Employer.email == identity.email))
            if email_in_use in {None, employer.id}:
                employer.email = identity.email
        _assign_role(employer, identity.email)
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
    _assign_role(employer, identity.email)
    session.add(employer)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        employer = session.scalar(select(Employer).where(Employer.clerk_user_id == identity.clerk_user_id))
        if employer is not None:
            _assign_role(employer, identity.email)
            return employer
        employer = Employer(
            clerk_user_id=identity.clerk_user_id,
            email=f"{identity.clerk_user_id}@clerk.local",
            company_name=None,
        )
        _assign_role(employer, identity.email)
        session.add(employer)
        session.flush()
    return employer


def _assign_role(employer: Employer, email: str) -> None:
    is_admin = email.lower() in settings.super_admin_emails
    desired_role = "super_admin" if is_admin else None
    if employer.role != desired_role:
        employer.role = desired_role


def get_current_employer(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> Employer:
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Employer authentication required")
    identity = verify_clerk_token(token)
    return get_or_create_employer(session, identity)


def get_current_super_admin(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> Employer:
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Super admin authentication required")
    identity = verify_clerk_token(token)
    employer = get_or_create_employer(session, identity)
    if employer.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return employer

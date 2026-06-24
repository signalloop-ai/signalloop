"""Tests for resolving a Clerk user's email from the Backend API.

Clerk's default session token has no email claim, so super-admin assignment (which is
email-based) depends on this resolver. These cover the selection logic and caching with a
mocked Clerk API.
"""

from unittest.mock import MagicMock, patch

import signalloop_api.auth as auth
from signalloop_api.config import settings


def _clerk_user_payload(primary: str, others: list[str] | None = None) -> dict:
    emails = [{"id": "idp", "email_address": primary}]
    for i, e in enumerate(others or []):
        emails.append({"id": f"id{i}", "email_address": e})
    return {"primary_email_address_id": "idp", "email_addresses": emails}


def _mock_resp(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


def test_resolves_primary_email(monkeypatch):
    auth._email_cache.clear()
    monkeypatch.setattr(settings, "clerk_secret_key", "sk_test")
    with patch("httpx.get", return_value=_mock_resp(_clerk_user_payload("admin@example.com", ["alt@example.com"]))):
        assert auth._resolve_email_from_clerk("user_1") == "admin@example.com"


def test_caches_after_first_lookup(monkeypatch):
    auth._email_cache.clear()
    monkeypatch.setattr(settings, "clerk_secret_key", "sk_test")
    mock_get = MagicMock(return_value=_mock_resp(_clerk_user_payload("a@b.com")))
    with patch("httpx.get", mock_get):
        auth._resolve_email_from_clerk("user_cache")
        auth._resolve_email_from_clerk("user_cache")
    assert mock_get.call_count == 1  # second call served from cache


def test_returns_none_without_secret(monkeypatch):
    auth._email_cache.clear()
    monkeypatch.setattr(settings, "clerk_secret_key", None)
    assert auth._resolve_email_from_clerk("user_x") is None


def test_returns_none_on_api_failure(monkeypatch):
    auth._email_cache.clear()
    monkeypatch.setattr(settings, "clerk_secret_key", "sk_test")
    with patch("httpx.get", side_effect=Exception("boom")):
        assert auth._resolve_email_from_clerk("user_err") is None

"""Tests for webcam consent and snapshot-upload-url endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker, Session

from signalloop_api.models import AssessmentAttempt, AssessmentPack


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_attempt(
    session_factory: sessionmaker[Session],
    *,
    status: str = "in_progress",
    webcam_consent: bool | None = None,
    token: str = "tok-webcam-test",
) -> tuple[str, int]:
    with session_factory() as session:
        pack = AssessmentPack(
            slug=f"test-pack-{token}",
            title="Test Pack",
            version="v1",
            candidate_path="assessment_packs/test",
            evaluator_path="assessment_packs/test/evaluator",
        )
        session.add(pack)
        session.flush()
        attempt = AssessmentAttempt(
            assessment_pack_id=pack.id,
            invite_token=token,
            status=status,
            assessment_level="standard",
            timing_mode="untimed",
            duration_minutes=90,
            evaluator_feedback_mode="strict",
            webcam_consent=webcam_consent,
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        return attempt.invite_token, attempt.id


def _consent_url(token: str) -> str:
    return f"/candidate/invites/{token}/webcam-consent"


def _upload_url(token: str) -> str:
    return f"/candidate/invites/{token}/snapshot-upload-url"


FAKE_PRESIGNED_URL = "https://s3.amazonaws.com/bucket/key?X-Amz-Signature=abc"


# ── Webcam consent endpoint ───────────────────────────────────────────────────

class TestWebcamConsent:
    def test_consent_granted_returns_204(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory)
        resp = client.patch(_consent_url(token), json={"consented": True})
        assert resp.status_code == 204

    def test_consent_declined_returns_204(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory)
        resp = client.patch(_consent_url(token), json={"consented": False})
        assert resp.status_code == 204

    def test_consent_persisted_true(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, attempt_id = _create_attempt(session_factory)
        client.patch(_consent_url(token), json={"consented": True})
        with session_factory() as session:
            attempt = session.get(AssessmentAttempt, attempt_id)
        assert attempt is not None
        assert attempt.webcam_consent is True

    def test_consent_persisted_false(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, attempt_id = _create_attempt(session_factory)
        client.patch(_consent_url(token), json={"consented": False})
        with session_factory() as session:
            attempt = session.get(AssessmentAttempt, attempt_id)
        assert attempt is not None
        assert attempt.webcam_consent is False

    def test_consent_can_be_changed(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, attempt_id = _create_attempt(session_factory, webcam_consent=True)
        client.patch(_consent_url(token), json={"consented": False})
        with session_factory() as session:
            attempt = session.get(AssessmentAttempt, attempt_id)
        assert attempt is not None
        assert attempt.webcam_consent is False

    def test_consent_unknown_token_returns_404(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        resp = client.patch("/candidate/invites/no-such/webcam-consent", json={"consented": True})
        assert resp.status_code == 404

    def test_consent_submitted_attempt_returns_409(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory, status="submitted", token="tok-consent-sub")
        resp = client.patch(_consent_url(token), json={"consented": True})
        assert resp.status_code == 409

    def test_consent_missing_field_returns_422(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory)
        resp = client.patch(_consent_url(token), json={})
        assert resp.status_code == 422

    def test_consent_non_string_type_returns_422(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        """A non-coercible value like a dict should fail validation."""
        token, _ = _create_attempt(session_factory)
        resp = client.patch(_consent_url(token), json={"consented": {"nested": "object"}})
        assert resp.status_code == 422

    def test_consent_allowed_for_opened_status(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory, status="opened", token="tok-consent-opened")
        resp = client.patch(_consent_url(token), json={"consented": True})
        assert resp.status_code == 204


# ── Snapshot upload URL endpoint ──────────────────────────────────────────────

class TestSnapshotUploadUrl:
    def _patched_s3(self) -> MagicMock:
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = FAKE_PRESIGNED_URL
        return mock_client

    def test_returns_presigned_url_and_key(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, attempt_id = _create_attempt(session_factory, webcam_consent=True, token="tok-snap-1")
        with patch("signalloop_api.proctoring.boto3.client", return_value=self._patched_s3()):
            with patch("signalloop_api.proctoring.settings") as mock_settings:
                mock_settings.s3_bucket = "test-bucket"
                mock_settings.aws_region = "us-east-1"
                resp = client.post(_upload_url(token), json={"filename": "1234567890.jpg"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["upload_url"] == FAKE_PRESIGNED_URL
        assert body["s3_key"] == f"snapshots/{attempt_id}/1234567890.jpg"

    def test_s3_key_format(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, attempt_id = _create_attempt(session_factory, webcam_consent=True, token="tok-snap-2")
        with patch("signalloop_api.proctoring.boto3.client", return_value=self._patched_s3()):
            with patch("signalloop_api.proctoring.settings") as mock_settings:
                mock_settings.s3_bucket = "bucket"
                mock_settings.aws_region = "us-east-1"
                resp = client.post(_upload_url(token), json={"filename": "ts-12345.jpeg"})
        assert resp.status_code == 200
        assert resp.json()["s3_key"].startswith(f"snapshots/{attempt_id}/")

    def test_no_consent_returns_403(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory, webcam_consent=None, token="tok-snap-3")
        resp = client.post(_upload_url(token), json={"filename": "shot.jpg"})
        assert resp.status_code == 403

    def test_declined_consent_returns_403(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory, webcam_consent=False, token="tok-snap-4")
        resp = client.post(_upload_url(token), json={"filename": "shot.jpg"})
        assert resp.status_code == 403

    def test_unknown_token_returns_404(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        resp = client.post("/candidate/invites/no-such/snapshot-upload-url", json={"filename": "shot.jpg"})
        assert resp.status_code == 404

    def test_submitted_attempt_returns_409(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(
            session_factory, status="submitted", webcam_consent=True, token="tok-snap-sub"
        )
        resp = client.post(_upload_url(token), json={"filename": "shot.jpg"})
        assert resp.status_code == 409

    def test_expired_attempt_returns_409(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(
            session_factory, status="expired", webcam_consent=True, token="tok-snap-exp"
        )
        resp = client.post(_upload_url(token), json={"filename": "shot.jpg"})
        assert resp.status_code == 409

    def test_unsafe_filename_path_traversal_rejected(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory, webcam_consent=True, token="tok-snap-5")
        resp = client.post(_upload_url(token), json={"filename": "../../etc/passwd.jpg"})
        assert resp.status_code == 422

    def test_filename_without_jpg_extension_rejected(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory, webcam_consent=True, token="tok-snap-6")
        resp = client.post(_upload_url(token), json={"filename": "shot.png"})
        assert resp.status_code == 422

    def test_filename_with_spaces_rejected(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory, webcam_consent=True, token="tok-snap-7")
        resp = client.post(_upload_url(token), json={"filename": "my shot.jpg"})
        assert resp.status_code == 422

    def test_missing_s3_bucket_returns_503(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory, webcam_consent=True, token="tok-snap-8")
        with patch("signalloop_api.proctoring.settings") as mock_settings:
            mock_settings.s3_bucket = None
            mock_settings.aws_region = "us-east-1"
            resp = client.post(_upload_url(token), json={"filename": "shot.jpg"})
        assert resp.status_code == 503

    def test_s3_client_error_returns_503(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        from botocore.exceptions import ClientError
        token, _ = _create_attempt(session_factory, webcam_consent=True, token="tok-snap-9")
        broken_client = MagicMock()
        broken_client.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "put_object"
        )
        with patch("signalloop_api.proctoring.boto3.client", return_value=broken_client):
            with patch("signalloop_api.proctoring.settings") as mock_settings:
                mock_settings.s3_bucket = "bucket"
                mock_settings.aws_region = "us-east-1"
                resp = client.post(_upload_url(token), json={"filename": "shot.jpg"})
        assert resp.status_code == 503

    def test_jpeg_extension_accepted(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, _ = _create_attempt(session_factory, webcam_consent=True, token="tok-snap-10")
        with patch("signalloop_api.proctoring.boto3.client", return_value=self._patched_s3()):
            with patch("signalloop_api.proctoring.settings") as mock_settings:
                mock_settings.s3_bucket = "bucket"
                mock_settings.aws_region = "us-east-1"
                resp = client.post(_upload_url(token), json={"filename": "shot.jpeg"})
        assert resp.status_code == 200

    def test_presigned_url_called_with_correct_params(
        self, client: TestClient, session_factory: sessionmaker[Session]
    ) -> None:
        token, attempt_id = _create_attempt(session_factory, webcam_consent=True, token="tok-snap-11")
        mock_s3 = self._patched_s3()
        with patch("signalloop_api.proctoring.boto3.client", return_value=mock_s3):
            with patch("signalloop_api.proctoring.settings") as mock_settings:
                mock_settings.s3_bucket = "my-bucket"
                mock_settings.aws_region = "us-west-2"
                client.post(_upload_url(token), json={"filename": "1234.jpg"})
        mock_s3.generate_presigned_url.assert_called_once_with(
            "put_object",
            Params={
                "Bucket": "my-bucket",
                "Key": f"snapshots/{attempt_id}/1234.jpg",
                "ContentType": "image/jpeg",
            },
            ExpiresIn=300,
        )

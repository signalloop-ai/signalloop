from fastapi.testclient import TestClient

from task_api.main import app, reset_state


client = TestClient(app)


def setup_function() -> None:
    reset_state()


def create_user(email: str = "owner@example.com") -> dict:
    response = client.post("/users", json={"email": email, "name": "Owner"})
    assert response.status_code == 201
    return response.json()


def test_can_create_user_and_task() -> None:
    user = create_user()

    response = client.post(
        "/tasks",
        json={"title": "Prepare beta checklist", "owner_id": user["id"]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Prepare beta checklist"
    assert body["owner_id"] == user["id"]
    assert body["status"] == "TODO"


def test_duplicate_user_email_is_rejected() -> None:
    create_user("same@example.com")

    response = client.post(
        "/users",
        json={"email": "same@example.com", "name": "Second"},
    )

    assert response.status_code == 409


def test_blank_task_title_is_rejected() -> None:
    user = create_user()

    response = client.post(
        "/tasks",
        json={"title": "   ", "owner_id": user["id"]},
    )

    assert response.status_code == 422


def test_non_owner_cannot_read_task() -> None:
    owner = create_user("owner@example.com")
    other = create_user("other@example.com")
    task = client.post(
        "/tasks",
        json={"title": "Owner-only task", "owner_id": owner["id"]},
    ).json()

    response = client.get(
        f"/tasks/{task['id']}",
        params={"actor_user_id": other["id"]},
    )

    assert response.status_code == 403



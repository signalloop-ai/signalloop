from fastapi.testclient import TestClient

from task_api.main import app, reset_state


client = TestClient(app)


def setup_function() -> None:
    reset_state()


def create_user(email: str) -> dict:
    response = client.post("/users", json={"email": email, "name": email.split("@")[0]})
    assert response.status_code == 201
    return response.json()


def create_task(owner_id: int, title: str = "Investigate beta issue") -> dict:
    response = client.post("/tasks", json={"title": title, "owner_id": owner_id})
    assert response.status_code == 201
    return response.json()


def test_duplicate_email_is_case_insensitive_and_conflicts() -> None:
    create_user("Lead@example.com")

    response = client.post("/users", json={"email": " lead@example.com ", "name": "Duplicate"})

    assert response.status_code == 409


def test_task_title_is_trimmed_and_blank_titles_are_rejected() -> None:
    owner = create_user("owner@example.com")

    created = client.post(
        "/tasks",
        json={"title": "  Ship checklist  ", "owner_id": owner["id"]},
    )
    blank = client.post(
        "/tasks",
        json={"title": "\t  ", "owner_id": owner["id"]},
    )

    assert created.status_code == 201
    assert created.json()["title"] == "Ship checklist"
    assert blank.status_code == 422


def test_task_priority_is_defaulted_normalized_and_validated() -> None:
    owner = create_user("owner@example.com")

    default_response = client.post(
        "/tasks",
        json={"title": "Default priority task", "owner_id": owner["id"]},
    )
    high_response = client.post(
        "/tasks",
        json={"title": "Escalated task", "owner_id": owner["id"], "priority": " high "},
    )
    invalid_response = client.post(
        "/tasks",
        json={"title": "Unknown priority task", "owner_id": owner["id"], "priority": "CRITICAL"},
    )

    assert default_response.status_code == 201
    assert default_response.json()["priority"] == "MEDIUM"
    assert high_response.status_code == 201
    assert high_response.json()["priority"] == "HIGH"
    assert invalid_response.status_code == 422


def test_only_owner_can_read_or_delete_task() -> None:
    owner = create_user("owner@example.com")
    other = create_user("other@example.com")
    task = create_task(owner["id"])

    read_response = client.get(
        f"/tasks/{task['id']}",
        params={"actor_user_id": other["id"]},
    )
    delete_response = client.delete(
        f"/tasks/{task['id']}",
        params={"actor_user_id": other["id"]},
    )
    owner_read_response = client.get(
        f"/tasks/{task['id']}",
        params={"actor_user_id": owner["id"]},
    )

    assert read_response.status_code == 403
    assert delete_response.status_code == 403
    assert owner_read_response.status_code == 200


def test_unknown_actor_cannot_access_task() -> None:
    owner = create_user("owner@example.com")
    task = create_task(owner["id"])

    response = client.get(
        f"/tasks/{task['id']}",
        params={"actor_user_id": 999},
    )

    assert response.status_code == 404


def test_status_values_and_transitions_are_enforced() -> None:
    owner = create_user("owner@example.com")
    task = create_task(owner["id"])

    invalid_status = client.patch(
        f"/tasks/{task['id']}/status",
        json={"status": "ARCHIVED"},
    )
    direct_done = client.patch(
        f"/tasks/{task['id']}/status",
        json={"status": "DONE"},
    )
    in_progress = client.patch(
        f"/tasks/{task['id']}/status",
        json={"status": "IN_PROGRESS"},
    )
    done = client.patch(
        f"/tasks/{task['id']}/status",
        json={"status": "DONE"},
    )
    reopen = client.patch(
        f"/tasks/{task['id']}/status",
        json={"status": "TODO"},
    )

    assert invalid_status.status_code == 422
    assert direct_done.status_code == 409
    assert in_progress.status_code == 200
    assert in_progress.json()["status"] == "IN_PROGRESS"
    assert done.status_code == 200
    assert done.json()["status"] == "DONE"
    assert reopen.status_code == 409


def test_owner_delete_removes_task_and_is_idempotently_not_found_afterward() -> None:
    owner = create_user("owner@example.com")
    task = create_task(owner["id"])

    delete_response = client.delete(
        f"/tasks/{task['id']}",
        params={"actor_user_id": owner["id"]},
    )
    read_response = client.get(
        f"/tasks/{task['id']}",
        params={"actor_user_id": owner["id"]},
    )
    second_delete = client.delete(
        f"/tasks/{task['id']}",
        params={"actor_user_id": owner["id"]},
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True, "task_id": task["id"]}
    assert read_response.status_code == 404
    assert second_delete.status_code == 404

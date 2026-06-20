from fastapi.testclient import TestClient

from task_api.main import app, reset_state


client = TestClient(app)


def setup_function() -> None:
    reset_state()


def create_user(email: str = "owner@example.com") -> dict:
    response = client.post("/users", json={"email": email, "name": email.split("@")[0]})
    assert response.status_code == 201
    return response.json()


def create_team(name: str = "Platform") -> dict:
    response = client.post("/teams", json={"name": name})
    assert response.status_code == 201
    return response.json()


def add_member(team_id: int, user_id: int, role: str = "member") -> dict:
    response = client.post(f"/teams/{team_id}/members", json={"user_id": user_id, "role": role})
    assert response.status_code == 201
    return response.json()


def create_task(team_id: int, owner_id: int, title: str = "Prepare beta launch") -> dict:
    response = client.post(
        "/tasks",
        json={"title": title, "team_id": team_id, "owner_id": owner_id, "description": "Initial description"},
    )
    assert response.status_code == 201
    return response.json()


def test_can_create_team_member_task_comment_and_events() -> None:
    owner = create_user("owner@example.com")
    team = create_team()
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    comment = client.post(
        f"/tasks/{task['id']}/comments",
        json={"actor_user_id": owner["id"], "body": "Looks good"},
    )
    events = client.get(f"/tasks/{task['id']}/events")

    assert comment.status_code == 201
    assert events.status_code == 200
    assert [event["action"] for event in events.json()] == ["created", "commented"]


def test_duplicate_user_email_is_normalized_and_rejected() -> None:
    create_user("Lead@example.com")

    response = client.post("/users", json={"email": " lead@example.com ", "name": "Duplicate"})

    assert response.status_code == 409


def test_patch_task_preserves_omitted_fields() -> None:
    owner = create_user()
    team = create_team()
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    response = client.patch(
        f"/tasks/{task['id']}",
        params={"actor_user_id": owner["id"]},
        json={"title": "Updated launch task"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated launch task"
    assert body["description"] == "Initial description"
    assert body["assignee_id"] is None


def test_archived_tasks_are_excluded_from_team_lists() -> None:
    owner = create_user()
    team = create_team()
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    delete_response = client.delete(f"/tasks/{task['id']}", params={"actor_user_id": owner["id"]})
    list_response = client.get(f"/teams/{team['id']}/tasks", params={"actor_user_id": owner["id"]})

    assert delete_response.status_code == 200
    assert list_response.status_code == 200
    assert all(item["id"] != task["id"] for item in list_response.json())


def test_status_transition_requires_in_progress_before_done() -> None:
    owner = create_user()
    team = create_team()
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    direct_done = client.patch(
        f"/tasks/{task['id']}/status",
        params={"actor_user_id": owner["id"]},
        json={"status": "DONE"},
    )
    in_progress = client.patch(
        f"/tasks/{task['id']}/status",
        params={"actor_user_id": owner["id"]},
        json={"status": "IN_PROGRESS"},
    )

    assert direct_done.status_code == 409
    assert in_progress.status_code == 200


def test_team_lead_cannot_access_unrelated_team_task() -> None:
    lead = create_user("lead@example.com")
    owner = create_user("owner@example.com")
    lead_team = create_team("Lead Team")
    other_team = create_team("Other Team")
    add_member(lead_team["id"], lead["id"], "lead")
    add_member(other_team["id"], owner["id"], "member")
    task = create_task(other_team["id"], owner["id"])

    response = client.get(f"/tasks/{task['id']}", params={"actor_user_id": lead["id"]})

    assert response.status_code == 403

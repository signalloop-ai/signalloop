from fastapi.testclient import TestClient

from task_api.main import app, reset_state


client = TestClient(app)


def setup_function() -> None:
    reset_state()


def create_user(email: str) -> dict:
    response = client.post("/users", json={"email": email, "name": email.split("@")[0]})
    assert response.status_code == 201
    return response.json()


def create_team(name: str) -> dict:
    response = client.post("/teams", json={"name": name})
    assert response.status_code == 201
    return response.json()


def add_member(team_id: int, user_id: int, role: str = "member") -> dict:
    response = client.post(f"/teams/{team_id}/members", json={"user_id": user_id, "role": role})
    assert response.status_code == 201
    return response.json()


def create_task(team_id: int, owner_id: int, assignee_id: int | None = None, title: str = "Task") -> dict:
    payload = {
        "title": title,
        "team_id": team_id,
        "owner_id": owner_id,
        "assignee_id": assignee_id,
        "description": "Original description",
    }
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    return response.json()


def test_membership_role_is_validated_and_duplicates_conflict() -> None:
    user = create_user("member@example.com")
    team = create_team("Platform")
    add_member(team["id"], user["id"], "member")

    duplicate = client.post(f"/teams/{team['id']}/members", json={"user_id": user["id"], "role": "member"})
    invalid = client.post(f"/teams/{team['id']}/members", json={"user_id": user["id"], "role": "admin"})

    assert duplicate.status_code == 409
    assert invalid.status_code == 422


def test_team_lead_access_is_limited_to_own_team() -> None:
    lead = create_user("lead@example.com")
    owner = create_user("owner@example.com")
    lead_team = create_team("Lead Team")
    other_team = create_team("Other Team")
    add_member(lead_team["id"], lead["id"], "lead")
    add_member(other_team["id"], owner["id"])
    task = create_task(other_team["id"], owner["id"])

    response = client.get(f"/tasks/{task['id']}", params={"actor_user_id": lead["id"]})

    assert response.status_code == 403


def test_partial_update_preserves_description_and_assignee() -> None:
    owner = create_user("owner@example.com")
    assignee = create_user("assignee@example.com")
    team = create_team("Platform")
    add_member(team["id"], owner["id"])
    add_member(team["id"], assignee["id"])
    task = create_task(team["id"], owner["id"], assignee_id=assignee["id"])

    response = client.patch(
        f"/tasks/{task['id']}",
        params={"actor_user_id": owner["id"]},
        json={"title": "Retitled task"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Retitled task"
    assert response.json()["description"] == "Original description"
    assert response.json()["assignee_id"] == assignee["id"]


def test_status_transition_and_audit_events_are_complete() -> None:
    owner = create_user("owner@example.com")
    team = create_team("Platform")
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
    done = client.patch(
        f"/tasks/{task['id']}/status",
        params={"actor_user_id": owner["id"]},
        json={"status": "DONE"},
    )
    events = client.get(f"/tasks/{task['id']}/events")

    assert direct_done.status_code == 409
    assert in_progress.status_code == 200
    assert done.status_code == 200
    assert [event["action"] for event in events.json()] == ["created", "status_changed", "status_changed"]


def test_archived_task_is_hidden_and_second_delete_is_not_found() -> None:
    owner = create_user("owner@example.com")
    team = create_team("Platform")
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    first_delete = client.delete(f"/tasks/{task['id']}", params={"actor_user_id": owner["id"]})
    read_after_delete = client.get(f"/tasks/{task['id']}", params={"actor_user_id": owner["id"]})
    second_delete = client.delete(f"/tasks/{task['id']}", params={"actor_user_id": owner["id"]})
    listed = client.get(f"/teams/{team['id']}/tasks", params={"actor_user_id": owner["id"]})

    assert first_delete.status_code == 200
    assert read_after_delete.status_code == 404
    assert second_delete.status_code == 404
    assert listed.json() == []


def test_comment_actor_must_have_task_access() -> None:
    owner = create_user("owner@example.com")
    outsider = create_user("outsider@example.com")
    team = create_team("Platform")
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    response = client.post(
        f"/tasks/{task['id']}/comments",
        json={"actor_user_id": outsider["id"], "body": "I should not comment"},
    )

    assert response.status_code == 403


def test_team_task_list_is_deterministically_sorted_and_paginated() -> None:
    owner = create_user("owner@example.com")
    team = create_team("Platform")
    add_member(team["id"], owner["id"])
    first = create_task(team["id"], owner["id"], title="First")
    second = create_task(team["id"], owner["id"], title="Second")
    third = create_task(team["id"], owner["id"], title="Third")

    page = client.get(
        f"/teams/{team['id']}/tasks",
        params={"actor_user_id": owner["id"], "limit": 2, "offset": 1},
    )

    assert page.status_code == 200
    assert [task["id"] for task in page.json()] == [second["id"], third["id"]]
    assert first["id"] < second["id"] < third["id"]

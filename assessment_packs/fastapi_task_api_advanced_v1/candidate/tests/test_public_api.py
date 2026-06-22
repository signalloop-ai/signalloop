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


def create_task(team_id: int, owner_id: int, title: str = "Beta launch task") -> dict:
    response = client.post(
        "/tasks",
        json={"title": title, "team_id": team_id, "owner_id": owner_id, "description": "Initial description"},
    )
    assert response.status_code == 201
    return response.json()


def test_can_create_team_member_task_and_events() -> None:
    owner = create_user("owner@example.com")
    team = create_team()
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    response = client.get(f"/tasks/{task['id']}/events")

    assert response.status_code == 200
    assert response.json()[0]["action"] == "created"


def test_patch_task_preserves_omitted_fields() -> None:
    owner = create_user()
    team = create_team()
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    response = client.patch(
        f"/tasks/{task['id']}",
        params={"actor_user_id": owner["id"]},
        json={"title": "Updated title"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated title"
    assert body["description"] == "Initial description"
    assert body["assignee_id"] is None


def test_team_lead_cannot_access_unrelated_team_task() -> None:
    lead = create_user("lead@example.com")
    owner = create_user("owner@example.com")
    lead_team = create_team("Lead Team")
    other_team = create_team("Other Team")
    add_member(lead_team["id"], lead["id"], "lead")
    add_member(other_team["id"], owner["id"])
    task = create_task(other_team["id"], owner["id"])

    response = client.get(f"/tasks/{task['id']}", params={"actor_user_id": lead["id"]})

    assert response.status_code == 403


def test_archived_tasks_are_excluded_from_team_lists() -> None:
    owner = create_user()
    team = create_team()
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    client.delete(f"/tasks/{task['id']}", params={"actor_user_id": owner["id"]})
    response = client.get(f"/teams/{team['id']}/tasks", params={"actor_user_id": owner["id"]})

    assert response.status_code == 200
    assert all(t["id"] != task["id"] for t in response.json())


def test_comment_requires_task_access() -> None:
    owner = create_user("owner@example.com")
    outsider = create_user("outsider@example.com")
    team = create_team()
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    response = client.post(
        f"/tasks/{task['id']}/comments",
        json={"actor_user_id": outsider["id"], "body": "I should not be able to comment"},
    )

    assert response.status_code == 403



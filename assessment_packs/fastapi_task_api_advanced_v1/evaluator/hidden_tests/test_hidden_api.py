from fastapi.testclient import TestClient

from task_api.main import app, reset_state


client = TestClient(app)


def setup_function() -> None:
    reset_state()


def create_user(email: str) -> dict:
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


def create_task(team_id: int, owner_id: int, title: str = "Task", assignee_id: int | None = None) -> dict:
    payload: dict = {"title": title, "team_id": team_id, "owner_id": owner_id, "description": "Original description"}
    if assignee_id is not None:
        payload["assignee_id"] = assignee_id
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    return response.json()


def add_dependency(task_id: int, blocker_id: int, actor_id: int) -> None:
    client.post(
        f"/tasks/{task_id}/dependencies",
        params={"actor_user_id": actor_id},
        json={"blocker_task_id": blocker_id},
    )


# --- Hidden issue 1: partial update authorization ---

def test_non_owner_non_assignee_cannot_patch_task() -> None:
    owner = create_user("owner@example.com")
    outsider = create_user("outsider@example.com")
    team = create_team()
    add_member(team["id"], owner["id"])
    add_member(team["id"], outsider["id"])
    task = create_task(team["id"], owner["id"])

    response = client.patch(
        f"/tasks/{task['id']}",
        params={"actor_user_id": outsider["id"]},
        json={"title": "Unauthorized change"},
    )

    assert response.status_code == 403


# --- Hidden issue 2: role validation ---

def test_membership_role_is_validated() -> None:
    user = create_user("member@example.com")
    team = create_team()

    invalid = client.post(f"/teams/{team['id']}/members", json={"user_id": user["id"], "role": "admin"})
    valid = client.post(f"/teams/{team['id']}/members", json={"user_id": user["id"], "role": "member"})

    assert invalid.status_code == 422
    assert valid.status_code == 201


# --- Hidden issue 3: status transition enforcement ---

def test_status_transition_chain_is_enforced() -> None:
    owner = create_user("owner@example.com")
    team = create_team()
    add_member(team["id"], owner["id"])
    task = create_task(team["id"], owner["id"])

    invalid_status = client.patch(f"/tasks/{task['id']}/status", params={"actor_user_id": owner["id"]}, json={"status": "SHIPPED"})
    direct_done = client.patch(f"/tasks/{task['id']}/status", params={"actor_user_id": owner["id"]}, json={"status": "DONE"})
    to_in_progress = client.patch(f"/tasks/{task['id']}/status", params={"actor_user_id": owner["id"]}, json={"status": "IN_PROGRESS"})
    to_done = client.patch(f"/tasks/{task['id']}/status", params={"actor_user_id": owner["id"]}, json={"status": "DONE"})

    assert invalid_status.status_code == 422
    assert direct_done.status_code == 409
    assert to_in_progress.status_code == 200
    assert to_done.status_code == 200


# --- Enhancement 1 basic: task dependency creation ---

def test_task_can_block_another_task() -> None:
    owner = create_user("owner@example.com")
    team = create_team()
    add_member(team["id"], owner["id"])
    blocker = create_task(team["id"], owner["id"], title="Blocker")
    blocked = create_task(team["id"], owner["id"], title="Blocked")

    response = client.post(
        f"/tasks/{blocked['id']}/dependencies",
        params={"actor_user_id": owner["id"]},
        json={"blocker_task_id": blocker["id"]},
    )

    assert response.status_code == 201
    assert response.json()["blocker_task_id"] == blocker["id"]


# --- Enhancement 2 basic: team activity feed exists ---

def test_team_activity_feed_returns_events() -> None:
    owner = create_user("owner@example.com")
    team = create_team()
    add_member(team["id"], owner["id"])
    create_task(team["id"], owner["id"])

    response = client.get(f"/teams/{team['id']}/activity", params={"actor_user_id": owner["id"]})

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1
    assert response.json()[0]["action"] == "created"


# --- Enhancement 1 quality: blocker enforced on status transition ---

def test_blocker_prevents_in_progress_transition() -> None:
    owner = create_user("owner@example.com")
    team = create_team()
    add_member(team["id"], owner["id"])
    blocker = create_task(team["id"], owner["id"], title="Blocker")
    blocked = create_task(team["id"], owner["id"], title="Blocked")

    add_dependency(blocked["id"], blocker["id"], owner["id"])

    start_while_blocked = client.patch(
        f"/tasks/{blocked['id']}/status",
        params={"actor_user_id": owner["id"]},
        json={"status": "IN_PROGRESS"},
    )

    client.patch(f"/tasks/{blocker['id']}/status", params={"actor_user_id": owner["id"]}, json={"status": "IN_PROGRESS"})
    client.patch(f"/tasks/{blocker['id']}/status", params={"actor_user_id": owner["id"]}, json={"status": "DONE"})

    start_after_blocker_done = client.patch(
        f"/tasks/{blocked['id']}/status",
        params={"actor_user_id": owner["id"]},
        json={"status": "IN_PROGRESS"},
    )

    assert start_while_blocked.status_code == 409
    assert start_after_blocker_done.status_code == 200


# --- Enhancement 1 quality: cycle detection ---

def test_dependency_cycle_is_rejected() -> None:
    owner = create_user("owner@example.com")
    team = create_team()
    add_member(team["id"], owner["id"])
    t1 = create_task(team["id"], owner["id"], title="Task 1")
    t2 = create_task(team["id"], owner["id"], title="Task 2")
    t3 = create_task(team["id"], owner["id"], title="Task 3")

    client.post(f"/tasks/{t2['id']}/dependencies", params={"actor_user_id": owner["id"]}, json={"blocker_task_id": t1["id"]})
    client.post(f"/tasks/{t3['id']}/dependencies", params={"actor_user_id": owner["id"]}, json={"blocker_task_id": t2["id"]})

    cycle = client.post(f"/tasks/{t1['id']}/dependencies", params={"actor_user_id": owner["id"]}, json={"blocker_task_id": t3["id"]})
    self_dep = client.post(f"/tasks/{t1['id']}/dependencies", params={"actor_user_id": owner["id"]}, json={"blocker_task_id": t1["id"]})

    assert cycle.status_code == 409
    assert self_dep.status_code == 409


# --- Enhancement 2 quality: activity feed pagination and access control ---

def test_activity_feed_is_paginated_and_team_scoped() -> None:
    owner = create_user("owner@example.com")
    outsider = create_user("outsider@example.com")
    team = create_team("Platform")
    other_team = create_team("Other")
    add_member(team["id"], owner["id"])
    add_member(other_team["id"], outsider["id"])

    create_task(team["id"], owner["id"], title="Task 1")
    create_task(team["id"], owner["id"], title="Task 2")

    all_events = client.get(f"/teams/{team['id']}/activity", params={"actor_user_id": owner["id"]})
    first_page = client.get(f"/teams/{team['id']}/activity", params={"actor_user_id": owner["id"], "limit": 1, "offset": 0})
    second_page = client.get(f"/teams/{team['id']}/activity", params={"actor_user_id": owner["id"], "limit": 1, "offset": 1})
    outsider_access = client.get(f"/teams/{team['id']}/activity", params={"actor_user_id": outsider["id"]})

    assert all_events.status_code == 200
    assert len(all_events.json()) >= 2
    assert first_page.status_code == 200
    assert len(first_page.json()) == 1
    assert second_page.status_code == 200
    assert len(second_page.json()) == 1
    assert first_page.json()[0] != second_page.json()[0]
    assert outsider_access.status_code == 403

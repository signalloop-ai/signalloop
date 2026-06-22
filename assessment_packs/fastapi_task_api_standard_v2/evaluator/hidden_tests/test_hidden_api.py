from fastapi.testclient import TestClient

from task_api.main import app, reset_state


client = TestClient(app)


def setup_function() -> None:
    reset_state()


def create_user(email: str) -> dict:
    response = client.post("/users", json={"email": email, "name": email.split("@")[0]})
    assert response.status_code == 201
    return response.json()


def create_task(owner_id: int, title: str = "Beta task", **kwargs: object) -> dict:
    response = client.post("/tasks", json={"title": title, "owner_id": owner_id, **kwargs})
    assert response.status_code == 201
    return response.json()


# --- Enhancement 1 basic: due date field ---

def test_due_date_is_optional_and_returned() -> None:
    owner = create_user("owner@example.com")

    with_date = client.post("/tasks", json={"title": "Task with deadline", "owner_id": owner["id"], "due_date": "2099-12-31"})
    without_date = client.post("/tasks", json={"title": "Task without deadline", "owner_id": owner["id"]})

    assert with_date.status_code == 201
    assert with_date.json()["due_date"] == "2099-12-31"
    assert without_date.status_code == 201
    assert without_date.json().get("due_date") is None


# --- Enhancement 2 basic: task listing by owner ---

def test_tasks_can_be_listed_by_owner() -> None:
    owner = create_user("owner@example.com")
    other = create_user("other@example.com")
    client.post("/tasks", json={"title": "Owner task 1", "owner_id": owner["id"]})
    client.post("/tasks", json={"title": "Owner task 2", "owner_id": owner["id"]})
    client.post("/tasks", json={"title": "Other task", "owner_id": other["id"]})

    response = client.get("/tasks", params={"owner_id": owner["id"]})

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "Owner task 1" in titles
    assert "Owner task 2" in titles
    assert "Other task" not in titles


# --- Hidden issue 1: email normalization ---

def test_duplicate_email_is_case_insensitive_and_trimmed() -> None:
    create_user("Lead@example.com")

    case_variant = client.post("/users", json={"email": "lead@example.com", "name": "Dup1"})
    whitespace_variant = client.post("/users", json={"email": " Lead@example.com ", "name": "Dup2"})

    assert case_variant.status_code == 409
    assert whitespace_variant.status_code == 409


# --- Hidden issue 2: full status transition chain ---

def test_status_transition_chain_is_enforced() -> None:
    owner = create_user("owner@example.com")
    task = create_task(owner["id"])

    invalid_status = client.patch(f"/tasks/{task['id']}/status", json={"status": "SHIPPED"})
    direct_done = client.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"})
    to_in_progress = client.patch(f"/tasks/{task['id']}/status", json={"status": "IN_PROGRESS"})
    to_done = client.patch(f"/tasks/{task['id']}/status", json={"status": "DONE"})
    reopen = client.patch(f"/tasks/{task['id']}/status", json={"status": "TODO"})

    assert invalid_status.status_code == 422
    assert direct_done.status_code == 409
    assert to_in_progress.status_code == 200
    assert to_done.status_code == 200
    assert reopen.status_code == 409


# --- Hidden issue 3: unknown actor returns 404 ---

def test_unknown_actor_returns_404_not_403() -> None:
    owner = create_user("owner@example.com")
    task = create_task(owner["id"])

    read_response = client.get(f"/tasks/{task['id']}", params={"actor_user_id": 999})
    delete_response = client.delete(f"/tasks/{task['id']}", params={"actor_user_id": 999})

    assert read_response.status_code == 404
    assert delete_response.status_code == 404


# --- Enhancement 1 quality: due date validation ---

def test_due_date_rejects_invalid_format() -> None:
    owner = create_user("owner@example.com")

    bad_format = client.post(
        "/tasks",
        json={"title": "Bad date", "owner_id": owner["id"], "due_date": "31-12-2099"},
    )
    not_a_date = client.post(
        "/tasks",
        json={"title": "Not a date", "owner_id": owner["id"], "due_date": "next-friday"},
    )
    valid = client.post(
        "/tasks",
        json={"title": "Valid date", "owner_id": owner["id"], "due_date": "2099-06-01"},
    )

    assert bad_format.status_code == 422
    assert not_a_date.status_code == 422
    assert valid.status_code == 201
    assert valid.json()["due_date"] == "2099-06-01"


# --- Enhancement 2 quality: task listing filter and order ---

def test_task_listing_is_filtered_and_ordered_by_id() -> None:
    owner = create_user("owner@example.com")
    other = create_user("other@example.com")
    t1 = create_task(owner["id"], "First")
    t2 = create_task(owner["id"], "Second")
    create_task(other["id"], "Other owner task")

    owner_tasks = client.get("/tasks", params={"owner_id": owner["id"]})
    no_tasks = client.get("/tasks", params={"owner_id": 999})

    assert owner_tasks.status_code == 200
    ids = [t["id"] for t in owner_tasks.json()]
    assert ids == sorted(ids)
    assert t1["id"] in ids
    assert t2["id"] in ids
    assert all(t["owner_id"] == owner["id"] for t in owner_tasks.json())

    assert no_tasks.status_code == 200
    assert no_tasks.json() == []

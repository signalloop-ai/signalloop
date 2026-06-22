from datetime import date
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator


app = FastAPI(title="Internal Task API")


VALID_STATUSES = {"TODO", "IN_PROGRESS", "DONE"}
VALID_PRIORITIES = {"LOW", "MEDIUM", "HIGH"}
ALLOWED_TRANSITIONS = {
    "TODO": {"IN_PROGRESS"},
    "IN_PROGRESS": {"DONE"},
    "DONE": set(),
}


class UserCreate(BaseModel):
    email: str
    name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Email is required")
        return normalized


class TaskCreate(BaseModel):
    title: str
    owner_id: int
    priority: str = "MEDIUM"
    due_date: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Title is required")
        return normalized

    @field_validator("priority")
    @classmethod
    def priority_must_be_known(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in VALID_PRIORITIES:
            raise ValueError(f"Priority must be one of {sorted(VALID_PRIORITIES)}")
        return normalized

    @field_validator("due_date")
    @classmethod
    def due_date_must_be_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            raise ValueError("due_date must be a valid ISO date (YYYY-MM-DD)")
        if parsed < date.today():
            raise ValueError("due_date cannot be in the past")
        return value


class StatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_must_be_known(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in VALID_STATUSES:
            raise ValueError(f"Status must be one of {sorted(VALID_STATUSES)}")
        return normalized


users: Dict[int, dict] = {}
tasks: Dict[int, dict] = {}
next_user_id = 1
next_task_id = 1


def reset_state() -> None:
    global next_user_id, next_task_id
    users.clear()
    tasks.clear()
    next_user_id = 1
    next_task_id = 1


def _ensure_actor_can_access(task: dict, actor_user_id: int) -> None:
    if actor_user_id not in users:
        raise HTTPException(status_code=404, detail="Actor not found")
    if task["owner_id"] != actor_user_id:
        raise HTTPException(status_code=403, detail="Forbidden")


@app.post("/users", status_code=201)
def create_user(payload: UserCreate) -> dict:
    global next_user_id
    if any(user["email"] == payload.email for user in users.values()):
        raise HTTPException(status_code=409, detail="Email already exists")
    user = {"id": next_user_id, "email": payload.email, "name": payload.name}
    users[next_user_id] = user
    next_user_id += 1
    return user


@app.get("/users/{user_id}")
def get_user(user_id: int) -> dict:
    user = users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.post("/tasks", status_code=201)
def create_task(payload: TaskCreate) -> dict:
    global next_task_id
    if payload.owner_id not in users:
        raise HTTPException(status_code=404, detail="Owner not found")
    task = {
        "id": next_task_id,
        "title": payload.title,
        "owner_id": payload.owner_id,
        "status": "TODO",
        "priority": payload.priority,
        "due_date": payload.due_date,
    }
    tasks[next_task_id] = task
    next_task_id += 1
    return task


@app.get("/tasks")
def list_tasks(owner_id: int) -> list[dict]:
    return sorted(
        [task for task in tasks.values() if task["owner_id"] == owner_id],
        key=lambda t: t["id"],
    )


@app.get("/tasks/{task_id}")
def get_task(task_id: int, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_actor_can_access(task, actor_user_id)
    return task


@app.patch("/tasks/{task_id}/status")
def update_task_status(task_id: int, payload: StatusUpdate) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if payload.status not in ALLOWED_TRANSITIONS[task["status"]]:
        raise HTTPException(status_code=409, detail="Invalid status transition")
    task["status"] = payload.status
    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_actor_can_access(task, actor_user_id)
    del tasks[task_id]
    return {"deleted": True, "task_id": task_id}

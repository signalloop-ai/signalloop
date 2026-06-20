from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator


app = FastAPI(title="Team Task API")

VALID_ROLES = {"member", "lead"}
VALID_STATUSES = {"TODO", "IN_PROGRESS", "DONE"}
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


class TeamCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Team name is required")
        return normalized


class MemberCreate(BaseModel):
    user_id: int
    role: str = "member"

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_ROLES:
            raise ValueError("Unknown role")
        return normalized


class TaskCreate(BaseModel):
    title: str
    team_id: int
    owner_id: int
    assignee_id: Optional[int] = None
    description: Optional[str] = None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Title is required")
        return normalized


class TaskPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None

    @field_validator("title")
    @classmethod
    def normalize_optional_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Title is required")
        return normalized


class StatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in VALID_STATUSES:
            raise ValueError("Unknown status")
        return normalized


class CommentCreate(BaseModel):
    actor_user_id: int
    body: str

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Comment body is required")
        return normalized


users: Dict[int, dict] = {}
teams: Dict[int, dict] = {}
memberships: Dict[int, list[dict]] = {}
tasks: Dict[int, dict] = {}
comments: Dict[int, list[dict]] = {}
events: Dict[int, list[dict]] = {}
next_user_id = 1
next_team_id = 1
next_task_id = 1
next_comment_id = 1


def reset_state() -> None:
    global next_user_id, next_team_id, next_task_id, next_comment_id
    users.clear()
    teams.clear()
    memberships.clear()
    tasks.clear()
    comments.clear()
    events.clear()
    next_user_id = 1
    next_team_id = 1
    next_task_id = 1
    next_comment_id = 1


def add_event(task_id: int, actor_user_id: int, action: str) -> None:
    events.setdefault(task_id, []).append(
        {"task_id": task_id, "actor_user_id": actor_user_id, "action": action}
    )


def membership_for(team_id: int, user_id: int) -> dict | None:
    return next(
        (member for member in memberships.get(team_id, []) if member["user_id"] == user_id),
        None,
    )


def ensure_user_exists(user_id: int, *, label: str = "User") -> None:
    if user_id not in users:
        raise HTTPException(status_code=404, detail=f"{label} not found")


def ensure_task_access(task: dict, actor_user_id: int) -> None:
    ensure_user_exists(actor_user_id, label="Actor")
    member = membership_for(task["team_id"], actor_user_id)
    if member is None:
        raise HTTPException(status_code=403, detail="Actor is not a team member")
    if member["role"] == "lead":
        return
    if task["owner_id"] == actor_user_id or task.get("assignee_id") == actor_user_id:
        return
    raise HTTPException(status_code=403, detail="Actor cannot access this task")


@app.post("/users", status_code=201)
def create_user(payload: UserCreate) -> dict:
    global next_user_id
    if any(user["email"] == payload.email for user in users.values()):
        raise HTTPException(status_code=409, detail="Email already exists")
    user = {"id": next_user_id, "email": payload.email, "name": payload.name}
    users[next_user_id] = user
    next_user_id += 1
    return user


@app.post("/teams", status_code=201)
def create_team(payload: TeamCreate) -> dict:
    global next_team_id
    team = {"id": next_team_id, "name": payload.name}
    teams[next_team_id] = team
    memberships[next_team_id] = []
    next_team_id += 1
    return team


@app.post("/teams/{team_id}/members", status_code=201)
def add_team_member(team_id: int, payload: MemberCreate) -> dict:
    if team_id not in teams:
        raise HTTPException(status_code=404, detail="Team not found")
    ensure_user_exists(payload.user_id)
    if membership_for(team_id, payload.user_id) is not None:
        raise HTTPException(status_code=409, detail="Membership already exists")
    member = {"team_id": team_id, "user_id": payload.user_id, "role": payload.role}
    memberships.setdefault(team_id, []).append(member)
    return member


@app.post("/tasks", status_code=201)
def create_task(payload: TaskCreate) -> dict:
    global next_task_id
    if payload.team_id not in teams:
        raise HTTPException(status_code=404, detail="Team not found")
    ensure_user_exists(payload.owner_id, label="Owner")
    if membership_for(payload.team_id, payload.owner_id) is None:
        raise HTTPException(status_code=403, detail="Owner is not a team member")
    if payload.assignee_id is not None:
        ensure_user_exists(payload.assignee_id, label="Assignee")
        if membership_for(payload.team_id, payload.assignee_id) is None:
            raise HTTPException(status_code=403, detail="Assignee is not a team member")

    task = {
        "id": next_task_id,
        "title": payload.title,
        "description": payload.description,
        "team_id": payload.team_id,
        "owner_id": payload.owner_id,
        "assignee_id": payload.assignee_id,
        "status": "TODO",
        "archived": False,
    }
    tasks[next_task_id] = task
    add_event(next_task_id, payload.owner_id, "created")
    next_task_id += 1
    return task


@app.get("/tasks/{task_id}")
def get_task(task_id: int, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None or task["archived"]:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_task_access(task, actor_user_id)
    return task


@app.patch("/tasks/{task_id}")
def patch_task(task_id: int, payload: TaskPatch, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None or task["archived"]:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_task_access(task, actor_user_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "assignee_id" in update_data and update_data["assignee_id"] is not None:
        ensure_user_exists(update_data["assignee_id"], label="Assignee")
        if membership_for(task["team_id"], update_data["assignee_id"]) is None:
            raise HTTPException(status_code=403, detail="Assignee is not a team member")
    task.update(update_data)
    add_event(task_id, actor_user_id, "updated")
    return task


@app.patch("/tasks/{task_id}/status")
def update_status(task_id: int, payload: StatusUpdate, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None or task["archived"]:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_task_access(task, actor_user_id)
    if payload.status not in ALLOWED_TRANSITIONS[task["status"]]:
        raise HTTPException(status_code=409, detail="Invalid status transition")
    task["status"] = payload.status
    add_event(task_id, actor_user_id, "status_changed")
    return task


@app.post("/tasks/{task_id}/comments", status_code=201)
def add_comment(task_id: int, payload: CommentCreate) -> dict:
    global next_comment_id
    task = tasks.get(task_id)
    if task is None or task["archived"]:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_task_access(task, payload.actor_user_id)
    comment = {
        "id": next_comment_id,
        "task_id": task_id,
        "actor_user_id": payload.actor_user_id,
        "body": payload.body,
    }
    comments.setdefault(task_id, []).append(comment)
    add_event(task_id, payload.actor_user_id, "commented")
    next_comment_id += 1
    return comment


@app.get("/users/{user_id}/tasks")
def list_user_tasks(user_id: int) -> list[dict]:
    ensure_user_exists(user_id)
    return sorted(
        [
            task
            for task in tasks.values()
            if not task["archived"] and (task["owner_id"] == user_id or task.get("assignee_id") == user_id)
        ],
        key=lambda item: item["id"],
    )


@app.get("/teams/{team_id}/tasks")
def list_team_tasks(team_id: int, actor_user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    if team_id not in teams:
        raise HTTPException(status_code=404, detail="Team not found")
    ensure_user_exists(actor_user_id, label="Actor")
    if membership_for(team_id, actor_user_id) is None:
        raise HTTPException(status_code=403, detail="Actor is not a team member")
    visible = sorted(
        [task for task in tasks.values() if task["team_id"] == team_id and not task["archived"]],
        key=lambda item: item["id"],
    )
    return visible[offset: offset + limit]


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None or task["archived"]:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_task_access(task, actor_user_id)
    task["archived"] = True
    add_event(task_id, actor_user_id, "archived")
    return {"archived": True, "task_id": task_id}


@app.get("/tasks/{task_id}/events")
def list_task_events(task_id: int) -> list[dict]:
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return events.get(task_id, [])

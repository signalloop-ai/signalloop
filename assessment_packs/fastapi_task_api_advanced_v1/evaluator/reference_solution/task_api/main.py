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
    def validate_role(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_ROLES:
            raise ValueError(f"Role must be one of {sorted(VALID_ROLES)}")
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
            raise ValueError(f"Status must be one of {sorted(VALID_STATUSES)}")
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


class DependencyCreate(BaseModel):
    blocker_task_id: int


users: Dict[int, dict] = {}
teams: Dict[int, dict] = {}
memberships: Dict[int, list[dict]] = {}
tasks: Dict[int, dict] = {}
comments: Dict[int, list[dict]] = {}
events: Dict[int, list[dict]] = {}
dependencies: Dict[int, list[int]] = {}  # task_id -> [blocker_task_ids]
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
    dependencies.clear()
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
        (m for m in memberships.get(team_id, []) if m["user_id"] == user_id),
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


def _is_reachable(start_id: int, target_id: int) -> bool:
    """Return True if target_id is reachable from start_id via the dependency graph."""
    visited: set[int] = set()
    stack = [start_id]
    while stack:
        current = stack.pop()
        if current == target_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        stack.extend(dependencies.get(current, []))
    return False


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
    task.update(payload.model_dump(exclude_unset=True))
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
    if payload.status == "IN_PROGRESS":
        unresolved = [
            b for b in dependencies.get(task_id, [])
            if not tasks.get(b, {}).get("archived") and tasks.get(b, {}).get("status") != "DONE"
        ]
        if unresolved:
            raise HTTPException(status_code=409, detail="Task has unresolved blockers")
    task["status"] = payload.status
    add_event(task_id, actor_user_id, "status_changed")
    return task


@app.post("/tasks/{task_id}/dependencies", status_code=201)
def add_dependency(task_id: int, payload: DependencyCreate, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None or task["archived"]:
        raise HTTPException(status_code=404, detail="Task not found")
    blocker = tasks.get(payload.blocker_task_id)
    if blocker is None or blocker["archived"]:
        raise HTTPException(status_code=404, detail="Blocker task not found")
    if task_id == payload.blocker_task_id:
        raise HTTPException(status_code=409, detail="Task cannot depend on itself")
    if _is_reachable(payload.blocker_task_id, task_id):
        raise HTTPException(status_code=409, detail="Dependency would create a cycle")
    deps = dependencies.setdefault(task_id, [])
    if payload.blocker_task_id not in deps:
        deps.append(payload.blocker_task_id)
        add_event(task_id, actor_user_id, "dependency_added")
    return {"task_id": task_id, "blocker_task_id": payload.blocker_task_id}


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
            task for task in tasks.values()
            if not task["archived"] and (task["owner_id"] == user_id or task.get("assignee_id") == user_id)
        ],
        key=lambda t: t["id"],
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
        key=lambda t: t["id"],
    )
    return visible[offset: offset + limit]


@app.get("/teams/{team_id}/activity")
def team_activity_feed(team_id: int, actor_user_id: int, limit: int = 20, offset: int = 0) -> list[dict]:
    if team_id not in teams:
        raise HTTPException(status_code=404, detail="Team not found")
    if membership_for(team_id, actor_user_id) is None:
        raise HTTPException(status_code=403, detail="Actor is not a team member")
    all_events: list[dict] = []
    for task_id, task_events in events.items():
        task = tasks.get(task_id)
        if task and task["team_id"] == team_id and not task["archived"]:
            for idx, event in enumerate(task_events):
                all_events.append({**event, "_sort": (task_id, idx)})
    all_events.sort(key=lambda e: e["_sort"])
    page = all_events[offset: offset + limit]
    return [{k: v for k, v in e.items() if k != "_sort"} for e in page]


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

from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="Team Task API")


class UserCreate(BaseModel):
    email: str
    name: Optional[str] = None


class TeamCreate(BaseModel):
    name: str


class MemberCreate(BaseModel):
    user_id: int
    role: str = "member"


class TaskCreate(BaseModel):
    title: str
    team_id: int
    owner_id: int
    assignee_id: Optional[int] = None
    description: Optional[str] = None


class TaskPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[int] = None


class StatusUpdate(BaseModel):
    status: str


class CommentCreate(BaseModel):
    actor_user_id: int
    body: str


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


def is_team_member(team_id: int, user_id: int) -> bool:
    return any(member["user_id"] == user_id for member in memberships.get(team_id, []))


def is_team_lead(user_id: int) -> bool:
    return any(
        member["user_id"] == user_id and member["role"] == "lead"
        for members in memberships.values()
        for member in members
    )


@app.post("/users", status_code=201)
def create_user(payload: UserCreate) -> dict:
    global next_user_id
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
    if payload.user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")
    member = {"team_id": team_id, "user_id": payload.user_id, "role": payload.role}
    memberships.setdefault(team_id, []).append(member)
    return member


@app.post("/tasks", status_code=201)
def create_task(payload: TaskCreate) -> dict:
    global next_task_id
    if payload.team_id not in teams:
        raise HTTPException(status_code=404, detail="Team not found")
    if payload.owner_id not in users:
        raise HTTPException(status_code=404, detail="Owner not found")
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
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["owner_id"] != actor_user_id and task.get("assignee_id") != actor_user_id and not is_team_lead(actor_user_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return task


@app.patch("/tasks/{task_id}")
def patch_task(task_id: int, payload: TaskPatch, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task["title"] = payload.title
    task["description"] = payload.description
    task["assignee_id"] = payload.assignee_id
    add_event(task_id, actor_user_id, "updated")
    return task


@app.patch("/tasks/{task_id}/status")
def update_status(task_id: int, payload: StatusUpdate, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task["status"] = payload.status
    add_event(task_id, actor_user_id, "status_changed")
    return task


@app.post("/tasks/{task_id}/comments", status_code=201)
def add_comment(task_id: int, payload: CommentCreate) -> dict:
    global next_comment_id
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
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
    return [
        task
        for task in tasks.values()
        if task["owner_id"] == user_id or task.get("assignee_id") == user_id
    ]


@app.get("/teams/{team_id}/tasks")
def list_team_tasks(team_id: int, actor_user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    if team_id not in teams:
        raise HTTPException(status_code=404, detail="Team not found")
    visible = [task for task in tasks.values() if task["team_id"] == team_id]
    return visible[offset: offset + limit]


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task["archived"] = True
    add_event(task_id, actor_user_id, "archived")
    return {"archived": True, "task_id": task_id}


@app.get("/tasks/{task_id}/events")
def list_task_events(task_id: int) -> list[dict]:
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return events.get(task_id, [])

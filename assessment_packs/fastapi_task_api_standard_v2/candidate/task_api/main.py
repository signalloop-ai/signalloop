from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="Internal Task API")


class UserCreate(BaseModel):
    email: str
    name: Optional[str] = None


class TaskCreate(BaseModel):
    title: str
    owner_id: int


class StatusUpdate(BaseModel):
    status: str


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


@app.post("/users", status_code=201)
def create_user(payload: UserCreate) -> dict:
    global next_user_id
    user = {
        "id": next_user_id,
        "email": payload.email,
        "name": payload.name,
    }
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
    }
    tasks[next_task_id] = task
    next_task_id += 1
    return task


@app.get("/tasks/{task_id}")
def get_task(task_id: int, actor_user_id: int) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.patch("/tasks/{task_id}/status")
def update_task_status(task_id: int, payload: StatusUpdate) -> dict:
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task["status"] = payload.status
    return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, actor_user_id: int) -> dict:
    task = tasks.pop(task_id, None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True, "task_id": task_id}

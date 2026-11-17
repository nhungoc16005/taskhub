from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import (
    CurrentUser,
    EditableProject,
    EditableTask,
    TaskServiceDep,
    ViewableProject,
    ViewableTask,
)
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models.task import TaskPriority, TaskStatus
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(tags=["tasks"])

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    data: TaskCreate,
    project: EditableProject,
    current_user: CurrentUser,
    service: TaskServiceDep,
):
    return await service.create(current_user, project, data)


@router.get("/projects/{project_id}/tasks", response_model=Page[TaskRead])
async def list_tasks(
    project: ViewableProject,
    service: TaskServiceDep,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
    skip: Skip = 0,
    limit: Limit = DEFAULT_PAGE_SIZE,
):
    return await service.list_by_project(
        project, skip, limit, status, priority, assignee_id
    )


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(task: ViewableTask):
    return task


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(data: TaskUpdate, task: EditableTask, service: TaskServiceDep):
    return await service.update(task, data)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task: ViewableTask, current_user: CurrentUser, service: TaskServiceDep
):
    await service.delete(current_user, task)

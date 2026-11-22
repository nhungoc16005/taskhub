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
from app.api.pagination import PaginationDep
from app.models.task import TaskPriority, TaskStatus
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(tags=["tasks"])


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
    pagination: PaginationDep,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
):
    return await service.list_by_project(
        project, pagination, task_status, priority, assignee_id
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

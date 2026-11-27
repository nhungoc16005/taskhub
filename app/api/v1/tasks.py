from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.api.deps import (
    CurrentUser,
    EditableProject,
    EditableTask,
    TaskServiceDep,
    ViewableProject,
    ViewableTask,
)
from app.api.documentation import TASK_EXAMPLE
from app.api.pagination import PaginationDep
from app.api.responses import error_responses
from app.core.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(tags=["tasks"])


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create task",
    openapi_extra={
        "requestBody": {"content": {"application/json": {"example": TASK_EXAMPLE}}}
    },
    responses=error_responses(
        400,
        401,
        403,
        404,
        409,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def create_task(
    data: TaskCreate,
    background_tasks: BackgroundTasks,
    project: EditableProject,
    current_user: CurrentUser,
    service: TaskServiceDep,
) -> Task:
    return await service.create(current_user, project, data, background_tasks)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=Page[TaskRead],
    summary="List tasks",
    responses=error_responses(
        401,
        403,
        404,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def list_tasks(
    project: ViewableProject,
    service: TaskServiceDep,
    pagination: PaginationDep,
    task_status: Annotated[list[TaskStatus] | None, Query(alias="status")] = None,
    priority: Annotated[list[TaskPriority] | None, Query()] = None,
    assignee_id: Annotated[int | None, Query(ge=1)] = None,
) -> Page[TaskRead]:
    return await service.list_by_project(
        project, pagination, task_status, priority, assignee_id
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskRead,
    summary="Get task",
    responses=error_responses(
        401,
        403,
        404,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def get_task(task: ViewableTask) -> Task:
    return task.resource


@router.patch(
    "/tasks/{task_id}",
    response_model=TaskRead,
    summary="Update task",
    responses=error_responses(
        400,
        401,
        403,
        404,
        409,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def update_task(
    data: TaskUpdate,
    task: EditableTask,
    service: TaskServiceDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Task:
    return await service.update(task, data, current_user, background_tasks)


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    responses=error_responses(
        401,
        403,
        404,
        409,
        422,
        500,
        descriptions={403: "Inactive user or insufficient permissions"},
    ),
)
async def delete_task(
    task: EditableTask, current_user: CurrentUser, service: TaskServiceDep
) -> None:
    await service.delete(current_user, task)

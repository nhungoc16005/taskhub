from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import (
    CommentServiceDep,
    CurrentUser,
    EditableTask,
    ViewableTask,
)
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import Page

router = APIRouter(tags=["comments"])

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    data: CommentCreate,
    task: EditableTask,
    current_user: CurrentUser,
    service: CommentServiceDep,
):
    return await service.create(current_user, task, data)


@router.get("/tasks/{task_id}/comments", response_model=Page[CommentRead])
async def list_comments(
    task: ViewableTask,
    service: CommentServiceDep,
    skip: Skip = 0,
    limit: Limit = DEFAULT_PAGE_SIZE,
):
    return await service.list_by_task(task, skip, limit)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int, current_user: CurrentUser, service: CommentServiceDep
):
    await service.delete(current_user, comment_id)

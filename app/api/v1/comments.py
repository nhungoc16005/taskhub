from fastapi import APIRouter, status

from app.api.deps import (
    CommentServiceDep,
    CurrentUser,
    EditableTask,
    ViewableTask,
)
from app.api.pagination import PaginationDep
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import Page

router = APIRouter(tags=["comments"])


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
    pagination: PaginationDep,
):
    return await service.list_by_task(task, pagination)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int, current_user: CurrentUser, service: CommentServiceDep
):
    await service.delete(current_user, comment_id)

from fastapi import APIRouter, status

from app.api.deps import (
    CommentServiceDep,
    CurrentUser,
    DeletableComment,
    EditableTask,
    ViewableTask,
)
from app.api.pagination import PaginationDep
from app.api.responses import RESOURCE_RESPONSES
from app.models.comment import Comment
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import Page

router = APIRouter(tags=["comments"], responses=RESOURCE_RESPONSES)


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create comment",
)
async def create_comment(
    data: CommentCreate,
    task: EditableTask,
    current_user: CurrentUser,
    service: CommentServiceDep,
) -> Comment:
    return await service.create(current_user, task.resource, data)


@router.get(
    "/tasks/{task_id}/comments",
    response_model=Page[CommentRead], summary="List comments",
)
async def list_comments(
    task: ViewableTask,
    service: CommentServiceDep,
    pagination: PaginationDep,
) -> Page[Comment]:
    return await service.list_by_task(task.resource, pagination)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT, summary="Delete comment",
)
async def delete_comment(
    comment: DeletableComment, service: CommentServiceDep
) -> None:
    await service.delete(comment)

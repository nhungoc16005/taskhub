from fastapi import APIRouter, status

from app.api.deps import (
    CurrentUser,
    OwnedWorkspace,
    ViewableWorkspace,
    WorkspaceServiceDep,
)
from app.api.documentation import WORKSPACE_EXAMPLE
from app.api.pagination import PaginationDep
from app.api.responses import RESOURCE_RESPONSES
from app.schemas.common import Page
from app.schemas.workspace import (
    MemberInvite,
    MemberRead,
    MemberUpdate,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)

router = APIRouter(
    prefix="/workspaces", tags=["workspaces"], responses=RESOURCE_RESPONSES
)


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
    openapi_extra={
        "requestBody": {"content": {"application/json": {"example": WORKSPACE_EXAMPLE}}}
    },
)
async def create_workspace(
    data: WorkspaceCreate, current_user: CurrentUser, service: WorkspaceServiceDep
):
    return await service.create(current_user, data)


@router.get("", response_model=Page[WorkspaceRead], summary="List my workspaces")
async def list_my_workspaces(
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
    pagination: PaginationDep,
):
    return await service.list_for_user(current_user, pagination)


@router.get("/{workspace_id}", response_model=WorkspaceRead, summary="Get a workspace")
async def get_workspace(workspace: ViewableWorkspace):
    return workspace


@router.patch(
    "/{workspace_id}", response_model=WorkspaceRead, summary="Update a workspace"
)
async def update_workspace(
    data: WorkspaceUpdate, workspace: OwnedWorkspace, service: WorkspaceServiceDep
):
    return await service.update(workspace, data)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace",
)
async def delete_workspace(workspace: OwnedWorkspace, service: WorkspaceServiceDep):
    await service.delete(workspace)


@router.get(
    "/{workspace_id}/members",
    response_model=list[MemberRead],
    summary="List workspace members",
)
async def list_members(workspace: ViewableWorkspace, service: WorkspaceServiceDep):
    return await service.list_members(workspace)


@router.post(
    "/{workspace_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a workspace member",
)
async def invite_member(
    data: MemberInvite, workspace: OwnedWorkspace, service: WorkspaceServiceDep
):
    return await service.add_member(workspace, data)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a workspace member",
)
async def remove_member(
    user_id: int, workspace: OwnedWorkspace, service: WorkspaceServiceDep
):
    await service.remove_member(workspace, user_id)


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=MemberRead,
    summary="Change a workspace member role",
)
async def update_member(
    user_id: int,
    data: MemberUpdate,
    workspace: OwnedWorkspace,
    service: WorkspaceServiceDep,
) -> MemberRead:
    return MemberRead.model_validate(
        await service.update_member(workspace, user_id, data)
    )

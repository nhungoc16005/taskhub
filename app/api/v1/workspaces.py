from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import (
    CurrentUser,
    OwnedWorkspace,
    ViewableWorkspace,
    WorkspaceServiceDep,
)
from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.schemas.common import Page
from app.schemas.workspace import (
    MemberInvite,
    MemberRead,
    MemberUpdate,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])

Skip = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)]


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate, current_user: CurrentUser, service: WorkspaceServiceDep
):
    return await service.create(current_user, data)


@router.get("", response_model=Page[WorkspaceRead])
async def list_my_workspaces(
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
    skip: Skip = 0,
    limit: Limit = DEFAULT_PAGE_SIZE,
):
    return await service.list_for_user(current_user, skip, limit)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(workspace: ViewableWorkspace):
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    data: WorkspaceUpdate, workspace: OwnedWorkspace, service: WorkspaceServiceDep
):
    return await service.update(workspace, data)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(workspace: OwnedWorkspace, service: WorkspaceServiceDep):
    await service.delete(workspace)


@router.get("/{workspace_id}/members", response_model=list[MemberRead])
async def list_members(workspace: ViewableWorkspace, service: WorkspaceServiceDep):
    return await service.list_members(workspace)


@router.post(
    "/{workspace_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    data: MemberInvite, workspace: OwnedWorkspace, service: WorkspaceServiceDep
):
    return await service.add_member(workspace, data)


@router.delete(
    "/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    user_id: int, workspace: OwnedWorkspace, service: WorkspaceServiceDep
):
    await service.remove_member(workspace, user_id)


@router.patch("/{workspace_id}/members/{user_id}", response_model=MemberRead)
async def update_member(
    user_id: int,
    data: MemberUpdate,
    workspace: OwnedWorkspace,
    service: WorkspaceServiceDep,
):
    return await service.update_member(workspace, user_id, data)

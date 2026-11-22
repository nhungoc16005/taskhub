from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import (
    EditableProject,
    EditableWorkspace,
    OwnedProject,
    ProjectServiceDep,
    ViewableProject,
    ViewableWorkspace,
)
from app.api.pagination import PaginationDep
from app.core.enums import ProjectStatus
from app.schemas.common import Page
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(tags=["projects"])


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    data: ProjectCreate, workspace: EditableWorkspace, service: ProjectServiceDep
):
    return await service.create(workspace, data)


@router.get("/workspaces/{workspace_id}/projects", response_model=Page[ProjectRead])
async def list_projects(
    workspace: ViewableWorkspace,
    service: ProjectServiceDep,
    pagination: PaginationDep,
    project_status: Annotated[ProjectStatus | None, Query(alias="status")] = None,
):
    return await service.list_by_workspace(workspace, pagination, project_status)


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(project: ViewableProject):
    return project


@router.patch("/projects/{project_id}", response_model=ProjectRead)
async def update_project(
    data: ProjectUpdate, project: EditableProject, service: ProjectServiceDep
):
    return await service.update(project, data)


@router.post("/projects/{project_id}/archive", response_model=ProjectRead)
async def archive_project(project: EditableProject, service: ProjectServiceDep):
    return await service.archive(project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project: OwnedProject, service: ProjectServiceDep):
    await service.delete(project)

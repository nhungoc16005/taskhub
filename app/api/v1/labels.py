from fastapi import APIRouter, status

from app.api.deps import (
    EditableLabel,
    EditableProject,
    EditableTask,
    LabelServiceDep,
    ViewableProject,
    ViewableTask,
)
from app.api.pagination import PaginationDep
from app.api.responses import RESOURCE_RESPONSES
from app.models.label import Label
from app.schemas.common import Page
from app.schemas.label import LabelCreate, LabelRead, LabelUpdate

router = APIRouter(tags=["labels"], responses=RESOURCE_RESPONSES)


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create label",
)
async def create_label(
    data: LabelCreate, project: EditableProject, service: LabelServiceDep
) -> Label:
    return await service.create(project, data)


@router.get(
    "/projects/{project_id}/labels", response_model=Page[LabelRead], summary="List labels"
)
async def list_labels(
    project: ViewableProject, service: LabelServiceDep, pagination: PaginationDep
) -> Page[Label]:
    return await service.list_by_project(project, pagination)


@router.patch("/labels/{label_id}", response_model=LabelRead, summary="Update label")
async def update_label(
    data: LabelUpdate, label: EditableLabel, service: LabelServiceDep
) -> Label:
    return await service.update(label.resource, data)


@router.delete(
    "/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete label"
)
async def delete_label(label: EditableLabel, service: LabelServiceDep) -> None:
    await service.delete(label.resource)


@router.get(
    "/tasks/{task_id}/labels", response_model=Page[LabelRead], summary="List task labels"
)
async def list_task_labels(
    task: ViewableTask, service: LabelServiceDep, pagination: PaginationDep
) -> Page[Label]:
    return await service.list_for_task(task.resource, pagination)


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Attach label",
)
async def attach_label(
    label_id: int, task: EditableTask, service: LabelServiceDep
) -> Label:
    return await service.attach(task.resource, label_id)


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT, summary="Detach label",
)
async def detach_label(
    label_id: int, task: EditableTask, service: LabelServiceDep
) -> None:
    await service.detach(task.resource, label_id)

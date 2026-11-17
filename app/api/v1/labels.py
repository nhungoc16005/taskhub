from fastapi import APIRouter, status

from app.api.deps import (
    EditableLabel,
    EditableProject,
    EditableTask,
    LabelServiceDep,
    ViewableProject,
    ViewableTask,
)
from app.schemas.label import LabelCreate, LabelRead, LabelUpdate

router = APIRouter(tags=["labels"])


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_label(
    data: LabelCreate, project: EditableProject, service: LabelServiceDep
):
    return await service.create(project, data)


@router.get("/projects/{project_id}/labels", response_model=list[LabelRead])
async def list_labels(project: ViewableProject, service: LabelServiceDep):
    return await service.list_by_project(project)


@router.patch("/labels/{label_id}", response_model=LabelRead)
async def update_label(
    data: LabelUpdate, label: EditableLabel, service: LabelServiceDep
):
    return await service.update(label, data)


@router.delete("/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(label: EditableLabel, service: LabelServiceDep):
    await service.delete(label)


@router.get("/tasks/{task_id}/labels", response_model=list[LabelRead])
async def list_task_labels(task: ViewableTask, service: LabelServiceDep):
    return await service.list_for_task(task)


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    response_model=list[LabelRead],
    status_code=status.HTTP_201_CREATED,
)
async def attach_label(label_id: int, task: EditableTask, service: LabelServiceDep):
    return await service.attach(task, label_id)


@router.delete(
    "/tasks/{task_id}/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def detach_label(label_id: int, task: EditableTask, service: LabelServiceDep):
    await service.detach(task, label_id)

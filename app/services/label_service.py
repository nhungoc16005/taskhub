from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    LabelAlreadyAttachedError,
    LabelNotAttachedError,
    LabelNotFoundError,
    ProjectNotFoundError,
)
from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.repositories.label_repository import LabelRepository
from app.schemas.label import LabelCreate, LabelUpdate
from app.services.project_service import ProjectService


class LabelService:
    def __init__(self, repo: LabelRepository, project_service: ProjectService):
        self.repo = repo
        self.project_service = project_service

    async def get_with_role(
        self, user: User, label_id: int, required: WorkspaceRole
    ) -> Label:
        label = await self.repo.get(label_id)
        if label is None:
            raise LabelNotFoundError()
        try:
            await self.project_service.get_with_role(user, label.project_id, required)
        except ProjectNotFoundError:
            raise LabelNotFoundError()
        return label

    async def create(self, project: Project, data: LabelCreate) -> Label:
        return await self.repo.create({**data.model_dump(), "project_id": project.id})

    async def list_by_project(self, project: Project):
        return await self.repo.list_by_project(project.id)

    async def update(self, label: Label, data: LabelUpdate) -> Label:
        return await self.repo.update(label, data.model_dump(exclude_unset=True))

    async def delete(self, label: Label) -> None:
        await self.repo.delete(label)

    async def list_for_task(self, task: Task):
        return await self.repo.list_for_task(task.id)

    async def _get_label_of_task_project(self, task: Task, label_id: int) -> Label:
        label = await self.repo.get(label_id)
        # label của project khác bị coi như không tồn tại (không lộ thông tin)
        if label is None or label.project_id != task.project_id:
            raise LabelNotFoundError()
        return label

    async def attach(self, task: Task, label_id: int):
        label = await self._get_label_of_task_project(task, label_id)
        if await self.repo.is_attached(task.id, label.id):
            raise LabelAlreadyAttachedError()
        try:
            await self.repo.attach(task.id, label.id)
        except IntegrityError:
            raise LabelAlreadyAttachedError()
        return await self.repo.list_for_task(task.id)

    async def detach(self, task: Task, label_id: int) -> None:
        label = await self._get_label_of_task_project(task, label_id)
        if not await self.repo.is_attached(task.id, label.id):
            raise LabelNotAttachedError()
        await self.repo.detach(task.id, label.id)

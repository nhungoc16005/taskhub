from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    LabelAlreadyAttachedError,
    LabelNameConflictError,
    LabelNotAttachedError,
    LabelNotFoundError,
    ResourceChangedError,
)
from app.core.integrity import is_unique_violation
from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.repositories.label_repository import LabelRepository
from app.schemas.common import Page, Pagination
from app.schemas.label import LabelCreate, LabelUpdate
from app.services.project_service import ProjectService
from app.services.resource_policy import AuthorizedResource, ProjectResourcePolicy
from app.services.transaction import transaction


class LabelService:
    def __init__(self, repo: LabelRepository, project_service: ProjectService):
        self.repo = repo
        self.policy = ProjectResourcePolicy(project_service)

    async def get_with_role(
        self,
        user: User,
        label_id: int,
        required: WorkspaceRole,
        *,
        writable: bool = False,
    ) -> AuthorizedResource[Label]:
        return await self.policy.load(
            self.repo.get,
            label_id,
            user,
            required,
            LabelNotFoundError,
            writable=writable,
        )

    async def create(self, project: Project, data: LabelCreate) -> Label:
        try:
            async with transaction(self.repo.session):
                return await self.repo.create(
                    {**data.model_dump(), "project_id": project.id}
                )
        except IntegrityError as error:
            self._raise_name_conflict(error)
            raise

    @staticmethod
    def _raise_name_conflict(error: IntegrityError) -> None:
        if is_unique_violation(
            error, "uq_labels_project_name", "labels.project_id, labels.name"
        ):
            raise LabelNameConflictError() from None

    async def list_by_project(
        self, project: Project, pagination: Pagination
    ) -> Page[Label]:
        return pagination.page(
            await self.repo.list_by_project(project.id, pagination),
            await self.repo.count_by_project(project.id),
        )

    async def update(self, label: Label, data: LabelUpdate) -> Label:
        try:
            async with transaction(self.repo.session):
                return await self.repo.update(
                    label, data.model_dump(exclude_unset=True)
                )
        except IntegrityError as error:
            self._raise_name_conflict(error)
            raise

    async def delete(self, label: Label) -> None:
        async with transaction(self.repo.session):
            await self.repo.delete(label)

    async def list_for_task(self, task: Task, pagination: Pagination) -> Page[Label]:
        return pagination.page(
            await self.repo.list_for_task(task.id, pagination),
            await self.repo.count_for_task(task.id),
        )

    async def _get_label_of_task_project(self, task: Task, label_id: int) -> Label:
        label = await self.repo.get(label_id)
        if label is None or label.project_id != task.project_id:
            raise LabelNotFoundError()
        return label

    async def attach(self, task: Task, label_id: int) -> Label:
        label = await self._get_label_of_task_project(task, label_id)
        if await self.repo.is_attached(task.id, label.id):
            raise LabelAlreadyAttachedError()
        try:
            async with transaction(self.repo.session):
                await self.repo.attach(task.id, label.id)
        except IntegrityError as error:
            if is_unique_violation(
                error, "task_labels_pkey", "task_labels.task_id, task_labels.label_id"
            ):
                raise LabelAlreadyAttachedError() from None
            # A concurrent delete can invalidate the FK after authorization.
            raise ResourceChangedError() from None
        return label

    async def detach(self, task: Task, label_id: int) -> None:
        label = await self._get_label_of_task_project(task, label_id)
        if not await self.repo.is_attached(task.id, label.id):
            raise LabelNotAttachedError()
        async with transaction(self.repo.session):
            await self.repo.detach(task.id, label.id)

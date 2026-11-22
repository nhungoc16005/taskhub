import hashlib
import json
import logging
import secrets
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core import messages
from app.core.constants import CACHE_VERSION_BITS, TASK_CACHE_PREFIX
from app.core.enums import TaskPriority, TaskStatus
from app.schemas.common import Pagination

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CacheLookup:
    key: str | None = None
    payload: str | None = None


class TaskCache:
    """Cache data only. Callers must authorize before lookup and invalidate after commit."""

    def __init__(self, redis: Redis, ttl: int):
        self.redis = redis
        self.ttl = ttl
        self._dirty_projects: set[int] = set()

    @staticmethod
    def version_key(project_id: int) -> str:
        return f"{TASK_CACHE_PREFIX}:{project_id}:version"

    async def _version(self, project_id: int) -> str:
        key = self.version_key(project_id)
        value = await self.redis.get(key)
        if value is None:
            await self.redis.set(key, secrets.randbits(CACHE_VERSION_BITS), nx=True)
            value = await self.redis.get(key)
        return str(value)

    async def lookup(
        self,
        project_id: int,
        pagination: Pagination,
        statuses: list[TaskStatus] | None,
        priorities: list[TaskPriority] | None,
        assignee_id: int | None,
    ) -> CacheLookup:
        try:
            if project_id in self._dirty_projects:
                await self._version(project_id)
                await self.redis.incr(self.version_key(project_id))
                self._dirty_projects.discard(project_id)
            version = await self._version(project_id)
            filters = json.dumps(
                {
                    "status": sorted({s.value for s in statuses})
                    if statuses is not None
                    else None,
                    "priority": sorted({p.value for p in priorities})
                    if priorities is not None
                    else None,
                    "assignee_id": assignee_id,
                    "skip": pagination.skip,
                    "limit": pagination.limit,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            digest = hashlib.sha256(filters.encode()).hexdigest()
            key = f"{TASK_CACHE_PREFIX}:{project_id}:{version}:{digest}"
            return CacheLookup(key, await self.redis.get(key))
        except (RedisError, OSError):
            logger.warning(messages.CACHE_UNAVAILABLE, "read")
            return CacheLookup()

    async def store(self, lookup: CacheLookup, payload: str) -> None:
        if lookup.key is None:
            return
        try:
            await self.redis.set(lookup.key, payload, ex=self.ttl)
        except (RedisError, OSError):
            logger.warning(messages.CACHE_UNAVAILABLE, "write")

    async def invalidate(self, project_id: int) -> None:
        self._dirty_projects.add(project_id)
        try:
            await self._version(project_id)
            await self.redis.incr(self.version_key(project_id))
            self._dirty_projects.discard(project_id)
        except (RedisError, OSError):
            logger.warning(messages.CACHE_UNAVAILABLE, "invalidate")

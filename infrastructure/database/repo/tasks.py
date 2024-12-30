import json
import logging
from typing import Dict, Optional, Any, Sequence

from sqlalchemy import select, update, delete
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import Task
from infrastructure.database.redis_client import RedisClient
from infrastructure.database.repo.base import BaseRepo


class TasksRepo(BaseRepo):
    def __init__(self, session, redis_client: RedisClient):
        super().__init__(session)
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)

    async def create_task(self, task_data: Dict) -> Optional[Task]:
        """
        Creates a new task in the database and invalidates the tasks list cache.

        :param task_data: A dictionary containing task attributes.
        :return: The created Task object if successful, None otherwise.
        """
        try:
            new_task = Task(**task_data)
            self.session.add(new_task)
            await self.session.commit()

            # Cache the new task in Redis
            await self._cache_task(new_task)

            # Invalidate the tasks list cache
            await self.redis_client.redis.delete("tasks:all")

            return new_task
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(f"Error creating task: {e}")
            return None

    async def get_task_by_id(self, task_id: int, language: str = "en") -> Optional[Task]:
        """
        Retrieves a task by its ID and returns the title in the specified language.

        :param task_id: The ID of the task to retrieve.
        :param language: The preferred language for task titles.
        :return: The Task object if found, None otherwise.
        """
        try:
            # Check Redis cache first
            cached_task = await self.redis_client.redis.hgetall(f"task:{task_id}")
            if cached_task:
                return self._deserialize_task(cached_task, language)

            query = select(Task).where(Task.task_id == task_id)
            result = await self.session.execute(query)
            task = result.scalar_one_or_none()

            if task:
                await self._cache_task(task)

            return task
        except SQLAlchemyError as e:
            self.logger.error(f"Error retrieving task {task_id}: {e}")
            return None

    async def update_task(self, task_id: int, task_data: Dict) -> Optional[Task]:
        """
        Updates an existing task in the database.

        :param task_id: The ID of the task to update.
        :param task_data: A dictionary of the attributes to update.
        :return: The updated Task object if successful, None otherwise.
        """
        try:
            query = update(Task).where(Task.task_id == task_id).values(**task_data).returning(Task)
            result = await self.session.execute(query)
            updated_task = result.scalar_one_or_none()

            if updated_task:
                await self.session.commit()

                # Update the cache in Redis
                await self._cache_task(updated_task)

                # Invalidate the tasks list cache
                await self.redis_client.redis.delete("tasks:all")

            return updated_task
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(f"Error updating task {task_id}: {e}")
            return None

    async def delete_task(self, task_id: int) -> bool:
        """
        Deletes a task by its ID.

        :param task_id: The ID of the task to delete.
        :return: True if the task was deleted, False otherwise.
        """
        try:
            query = delete(Task).where(Task.task_id == task_id)
            await self.session.execute(query)
            await self.session.commit()

            # Remove the task from Redis cache
            await self.redis_client.redis.delete(f"task:{task_id}")

            # Invalidate the tasks list cache
            await self.redis_client.redis.delete("tasks:all")

            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(f"Error deleting task {task_id}: {e}")
            return False

    async def list_tasks(self) -> list[Task] | Sequence[Task] | list[Any]:
        """
        Retrieves a list of all tasks.

        :return: A list of Task objects.
        """
        try:
            # Check if the task list is cached
            cache_key = "tasks:all"
            cached_tasks = await self.redis_client.redis.get(cache_key)
            if cached_tasks:
                return [self._deserialize_task(task_data) for task_data in json.loads(cached_tasks)]

            query = select(Task)
            result = await self.session.execute(query)
            tasks = result.scalars().all()

            # Cache the tasks list in Redis
            await self.redis_client.redis.setex(cache_key, 86400, json.dumps([self._serialize_task(task) for task in tasks]))

            return tasks
        except SQLAlchemyError as e:
            self.logger.error(f"Error listing tasks: {e}")
            return []

    async def _cache_task(self, task: Task):
        """
        Caches a task in Redis.

        :param task: The Task object to cache.
        """
        await self.redis_client.redis.hset(f"task:{task.task_id}", mapping=self._serialize_task(task))
        await self.redis_client.redis.expire(f"task:{task.task_id}", 86400)

    @staticmethod
    def _serialize_task(task: Task) -> Dict:
        """
        Serializes a Task object to a dictionary.

        :param task: The Task object to serialize.
        :return: The serialized dictionary.
        """
        return {
            "task_id": task.task_id,
            "titles": json.dumps(task.titles),  # Store titles as a JSON string
            "source": task.source,
            "link": task.link,
            "cover": task.cover or '',  # Use .get() to safely handle missing keys
            "descriptions": json.dumps(task.descriptions) if task.descriptions else None,
            "balance": task.balance
        }

    @staticmethod
    def _deserialize_task(task_data: Dict, language: str = "en") -> Task:
        """
        Deserializes a task dictionary to a Task object.

        :param task_data: The task data dictionary.
        :param language: The preferred language for task titles.
        :return: The deserialized Task object.
        """
        titles = json.loads(task_data["titles"])
        descriptions = json.loads(task_data.get("descriptions")) if task_data.get("descriptions") else None
        title = titles.get(language) or titles.get("en", "No title available")
        description = descriptions.get(language) if descriptions else None

        return Task(
            task_id=int(task_data["task_id"]),
            titles=title,
            source=task_data["source"],
            link=task_data["link"],
            cover=task_data.get("cover"),  # Use .get() to safely access the cover
            descriptions=description,
            balance=task_data["balance"]
        )

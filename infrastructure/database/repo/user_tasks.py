import logging
import json
from typing import List, Tuple

from sqlalchemy import select, insert
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.database.models import UserTask, Task
from infrastructure.database.repo.base import BaseRepo


class UserTaskRepo(BaseRepo):
    def __init__(self, session):
        super().__init__(session)
        self.logger = logging.getLogger(__name__)

    async def get_incomplete_tasks(self, user_id: int, language: str = "en") -> List[Tuple[int, str]]:
        """
        Retrieves a list of incomplete task IDs and their titles for a user in the preferred language.

        :param user_id: The ID of the user.
        :param language: The preferred language for task titles.
        :return: A list of tuples containing incomplete task IDs and their titles in the preferred language.
        """
        try:
            # Retrieve all tasks with their IDs and titles
            query_all_tasks = select(Task.task_id, Task.titles)
            result_all_tasks = await self.session.execute(query_all_tasks)
            all_tasks = {row[0]: row[1] for row in result_all_tasks.all()}

            # Retrieve completed task IDs for the user
            query_completed_tasks = select(UserTask.task_id).where(UserTask.user_id == user_id)
            result_completed_tasks = await self.session.execute(query_completed_tasks)
            completed_task_ids = {row[0] for row in result_completed_tasks.all()}

            # Determine the incomplete tasks by checking against all tasks
            incomplete_tasks = []
            for task_id, titles in all_tasks.items():
                if task_id not in completed_task_ids:
                    try:
                        # Ensure that titles is a dict (deserialize if necessary)
                        if isinstance(titles, str):
                            titles = json.loads(titles)

                        # Get the title in the preferred language, fallback to English if not available
                        title = titles.get(language) or titles.get("en", "No title available")
                    except (AttributeError, json.JSONDecodeError) as e:
                        self.logger.error(f"Error decoding titles for task {task_id}: {e}")
                        title = "No title available"
                    incomplete_tasks.append((task_id, title))

            return incomplete_tasks
        except SQLAlchemyError as e:
            self.logger.error(f"Error retrieving incomplete tasks for user {user_id}: {e}")
            return []

    async def complete_task(self, user_id: int, task_id: int) -> bool:
        """
        Marks a user task as complete by adding it to the UserTask table.

        :param user_id: The ID of the user.
        :param task_id: The ID of the task.
        :return: True if the task was successfully marked as complete, False otherwise.
        """
        try:
            # Check if the task is already completed for the user
            query_check = select(UserTask).where(UserTask.user_id == user_id, UserTask.task_id == task_id)
            result = await self.session.execute(query_check)
            if result.scalar_one_or_none() is not None:
                self.logger.info(f"Task {task_id} is already completed for user {user_id}.")
                return False  # Task is already completed

            # If not completed, mark it as complete
            query = insert(UserTask).values(user_id=user_id, task_id=task_id)
            await self.session.execute(query)
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(f"Error completing task {task_id} for user {user_id}: {e}")
            return False

    async def is_task_completed(self, user_id: int, task_id: int) -> bool:
        """
        Checks if a specific task has been completed by a user.

        :param user_id: The ID of the user.
        :param task_id: The ID of the task.
        :return: True if the task is completed, False otherwise.
        """
        try:
            query = select(UserTask).where(UserTask.user_id == user_id, UserTask.task_id == task_id)
            result = await self.session.execute(query)
            return result.scalar_one_or_none() is not None
        except SQLAlchemyError as e:
            self.logger.error(f"Error checking task completion for user {user_id} and task {task_id}: {e}")
            return False


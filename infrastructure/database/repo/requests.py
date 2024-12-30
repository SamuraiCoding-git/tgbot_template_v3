from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.redis_client import RedisClient
from infrastructure.database.repo.referrals import ReferralsRepo
from infrastructure.database.repo.tasks import TasksRepo
from infrastructure.database.repo.user_tasks import UserTaskRepo
from infrastructure.database.repo.users import UserRepo


@dataclass
class RequestsRepo:
    """
    Repository for handling database operations. This class holds all the repositories for the database models.

    You can add more repositories as properties to this class, so they will be easily accessible.
    """

    session: AsyncSession
    redis: RedisClient

    @property
    def users(self) -> UserRepo:
        """
        The User repository sessions are required to manage user operations.
        """
        return UserRepo(self.session, self.redis)

    @property
    def referrals(self) -> ReferralsRepo:
        """
        The User repository sessions are required to manage user operations.
        """
        return ReferralsRepo(self.session, self.redis)

    @property
    def tasks(self) -> TasksRepo:
        return TasksRepo(self.session, self.redis)

    @property
    def user_tasks(self) -> UserTaskRepo:
        return UserTaskRepo(self.session)

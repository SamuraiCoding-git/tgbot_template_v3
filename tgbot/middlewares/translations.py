from aiogram.types import User
from aiogram_i18n.managers import BaseManager

from infrastructure.database.repo.requests import RequestsRepo


class TgUserManager(BaseManager):
    def __init__(self, session_pool, redis) -> None:
        super().__init__()
        self.session_pool = session_pool
        self.redis = redis

    async def get_locale(self, event_from_user: User):
        async with self.session_pool() as session:
            repo = RequestsRepo(session, self.redis)
            user = await repo.users.select_user(event_from_user.id)
        return user.language if user else 'en'

    async def set_locale(self, locale: str):
        pass

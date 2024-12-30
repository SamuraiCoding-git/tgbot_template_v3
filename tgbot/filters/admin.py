from aiogram.filters import BaseFilter
from aiogram.types import Message
from tgbot.config import Config


class AdminFilter(BaseFilter):
    """
    A custom filter for Aiogram to check whether a user is an admin.

    Attributes:
        is_admin (bool): Indicates whether to check for admin status (True)
                         or non-admin status (False). Defaults to True.
    """

    is_admin: bool = True

    async def __call__(self, obj: Message, config: Config) -> bool:
        """
        Determines if the user's ID is in the list of admin IDs from the configuration.

        Args:
            obj (Message): The incoming message object containing user and message data.
            config (Config): The bot's configuration instance, which includes admin IDs.

        Returns:
            bool: True if the user is an admin (or non-admin if is_admin is False),
                  otherwise False.
        """
        return (obj.from_user.id in config.tg_bot.admin_ids) == self.is_admin

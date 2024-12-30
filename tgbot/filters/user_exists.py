from aiogram.filters import BaseFilter
from aiogram.types import Message

from infrastructure.database.repo.requests import RequestsRepo


class UserExistsFilter(BaseFilter):
    """
    A custom filter for Aiogram to check whether a user exists in the database.

    Attributes:
        does_user_exist (bool): Indicates whether to check if the user exists (True)
                                or does not exist (False). Defaults to False.
    """

    does_user_exist: bool = False

    async def __call__(self, message: Message, session, redis) -> bool:
        """
        Checks if the user exists in the database using the provided session.

        Args:
            message (Message): The incoming message object containing user and chat data.
            session: The database session used to interact with the database.

        Returns:
            bool: True if the user's existence status matches `does_user_exist`,
                  otherwise False.
        """
        # Create an instance of the RequestsRepo using the provided session
        repo = RequestsRepo(session, redis)

        # Check if the user exists in the database by selecting the user by chat ID
        user_exists = await repo.users.select_user(message.chat.id) is not None
        # Return True if the existence status matches the does_user_exist attribute
        return user_exists == self.does_user_exist

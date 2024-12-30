import requests

from urllib.parse import urlparse

from aiogram import Bot


def get_link_source(url: str) -> str:
    """
    Extracts the source/domain name from a URL.

    Args:
        url (str): The input URL.

    Returns:
        str: The domain name (source) of the URL.
    """
    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    # Handle cases where the domain might start with 'www.'
    if domain.startswith("www."):
        domain = domain[4:]

    return domain.split('.')[0]


def is_valid_url(url: str) -> bool:
    """
    Checks if the URL is well-formed and optionally if it is reachable.

    Args:
        url (str): The input URL.

    Returns:
        bool: True if the URL is valid and reachable, False otherwise.
    """
    try:
        # Parse the URL to ensure it is well-formed
        parsed_url = urlparse(url)

        # Check if the URL has a scheme and netloc
        if not all([parsed_url.scheme, parsed_url.netloc]):
            return False

        # Optional: Check if the URL is reachable
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.status_code == 200

    except (requests.RequestException, ValueError):
        return False

async def check_user_membership(bot: Bot, user_id: int, channel_username: str) -> bool:
    """
    Checks if a user is a member of a specified Telegram channel or chat.

    :param bot: The Bot instance.
    :param user_id: The Telegram user ID to check.
    :param channel_username: The username of the Telegram channel (without @).
    :return: True if the user is a member, False otherwise.
    """
    try:
        member = await bot.get_chat_member(chat_id=f"@{channel_username}", user_id=user_id)
        return str(member.status) in ['ChatMemberStatus.CREATOR', 'ChatMemberStatus.ADMINISTRATOR', 'ChatMemberStatus.MEMBER']
    except:
        # The chat does not exist or the bot is not an admin in the chat
        return False
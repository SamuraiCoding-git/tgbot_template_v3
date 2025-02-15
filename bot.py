import asyncio
import logging

import betterlogging as bl
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram_i18n import I18nMiddleware

from infrastructure.database.models import Base
from infrastructure.database.redis_client import RedisClient
from infrastructure.database.setup import create_engine, create_session_pool
from tgbot.config import load_config, Config
from tgbot.handlers import routers_list
from tgbot.middlewares.config import ConfigMiddleware
from tgbot.middlewares.database import DatabaseMiddleware
from tgbot.middlewares.redis import RedisMiddleware
from tgbot.middlewares.translations import TgUserManager
from aiogram_i18n.cores import FluentRuntimeCore
# from tgbot.services import broadcaster


async def on_startup(bot: Bot, admin_ids: list[int]):
    pass
    # await broadcaster.broadcast(bot, admin_ids, "Бот был запущен")

async def on_shutdown(redis_client: RedisClient):
    await redis_client.close()



def register_global_middlewares(dp: Dispatcher, config: Config, session_pool=None, redis=None):
    """
    Register global middlewares for the given dispatcher.
    Global middlewares here are the ones that are applied to all the handlers (you specify the type of update)

    :param dp: The dispatcher instance.
    :type dp: Dispatcher
    :param config: The configuration object from the loaded configuration.
    :param session_pool: Optional session pool object for the database using SQLAlchemy.
    :return: None
    """
    middleware_types = [
        ConfigMiddleware(config),
        DatabaseMiddleware(session_pool),
        RedisMiddleware(redis)
    ]

    for middleware_type in middleware_types:
        dp.message.outer_middleware(middleware_type)
        dp.callback_query.outer_middleware(middleware_type)


def setup_logging():
    """
    Set up logging configuration for the application.

    This method initializes the logging configuration for the application.
    It sets the log level to INFO and configures a basic colorized log for
    output. The log format includes the filename, line number, log level,
    timestamp, logger name, and log message.

    Returns:
        None

    Example usage:
        setup_logging()
    """
    log_level = logging.INFO
    bl.basic_colorized_config(level=log_level)

    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting bot")


def get_storage(config):
    """
    Return storage based on the provided configuration.

    Args:
        config (Config): The configuration object.

    Returns:
        Storage: The storage object based on the configuration.

    """
    if config.tg_bot.use_redis:
        return RedisStorage.from_url(
            config.redis.dsn(),
            key_builder=DefaultKeyBuilder(with_bot_id=True, with_destiny=True),
        )
    else:
        return MemoryStorage()


async def create_tables(engine):
    async with engine.begin() as conn:
        logging.info("Creating tables if not exist...")
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)


async def main():
    setup_logging()

    config = load_config(".env")
    storage = get_storage(config)

    bot = Bot(token=config.tg_bot.token, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher(storage=storage)

    engine = create_engine(config.db)
    session_pool = create_session_pool(engine)

    redis = RedisClient(config.redis.dsn())
    await redis.connect()

    i18n_middleware = I18nMiddleware(
        core=FluentRuntimeCore("tgbot/locales"),
        default_locale="ru",
        manager=TgUserManager(session_pool, redis)
    )
    i18n_middleware.setup(dp)

    await create_tables(engine)

    dp.include_routers(*routers_list)

    register_global_middlewares(dp, config, session_pool, redis)

    await on_startup(bot, config.tg_bot.admin_ids)
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown(redis)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Бот был выключен!")

import re
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram_i18n.context import I18nContext

from funcs import check_user_membership
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.config import Config
from tgbot.filters.user_exists import UserExistsFilter
from tgbot.keyboards.inline import language_keyboard, Language, main_keyboard, back_keyboard, referral_keyboard, \
    tasks_list_keyboard, Tasks, task_keyboard

user_router = Router()

async def handle_start_command(message: Message, i18n: I18nContext, state: FSMContext,
                               referred_by: Optional[int] = None, is_first_start: bool = True):
    if is_first_start:
        if referred_by:
            await state.update_data(referred_by=referred_by)
        await message.answer_photo(i18n.image.language(), caption=i18n.text.language(), reply_markup=language_keyboard())
    else:
        await message.answer_photo(i18n.image.main(), caption=i18n.text.main(), reply_markup=main_keyboard(i18n))


@user_router.message(CommandStart(deep_link=True, magic=F.args.regexp(re.compile(r'^task_\d+$'))))
async def task_deeplink(message: Message, session, redis, i18n: I18nContext, state: FSMContext):
    repo = RequestsRepo(session, redis)

    # Extract the task ID from the deep link argument
    task_id_str = message.text.split("_")[-1]
    task_id = int(task_id_str)
    await state.update_data(task_id=task_id)

    # Retrieve the task from the database
    task = await repo.tasks.get_task_by_id(task_id, i18n.locale)

    if task is None:
        await message.answer("Задание не найдено.")
        return

    # Check if the task is already completed by the user
    task_completed = await repo.user_tasks.is_task_completed(user_id=message.from_user.id, task_id=task_id)
    if task_completed:
        await message.answer("Вы уже выполнили это задание.")
        return

    # Prepare the text and media to be sent
    task_text = f"<b>{task.titles}</b>\n\n{task.descriptions or ''}\n\n<i>{i18n.info.reward(reward=str(task.balance))}</i>"

    # Check if the task has a cover
    if task.cover:
        await message.answer_photo(
            photo=task.cover,
            caption=task_text,
            reply_markup=task_keyboard(i18n, task.link, task.titles) # Add any relevant buttons or keyboard here if needed
        )
    else:
        await message.answer(
            text=task_text,
            reply_markup=task_keyboard(i18n, task.link, task.titles)  # Add any relevant buttons or keyboard here if needed
        )

@user_router.message(UserExistsFilter(), CommandStart())
async def first_start(message: Message, i18n: I18nContext, command: CommandObject, state: FSMContext):
    await handle_start_command(message, i18n, state, command.args)

@user_router.message(CommandStart())
async def user_start(message: Message, i18n: I18nContext, state: FSMContext):
    await handle_start_command(message, i18n, state, is_first_start=False)

async def notify_referrers(referral_chain: list, new_user_id: int, reward_amount: int, bot: Bot, i18n: I18nContext, repo: RequestsRepo):
    """
    Notify the referrer and referrer of the referrer if they exist, and apply referral rewards.
    """
    for level, referrer_info in enumerate(referral_chain):
        if referrer_info and "referral" in referrer_info:
            referral = referrer_info["referral"]
            reward_type = referral.reward_type
            language = referrer_info.get("language", "en")  # Fallback to "en" if language is not provided

            # Set the i18n context to the referrer's language
            await i18n.set_locale(language)

            if level == 0:
                message_key = "notification-referrer-first_level"
                reward_percentage = 0.1 if reward_type == 1 else 0.15  # 10% for reward_type 1, 15% for reward_type 2
            else:
                message_key = "notification-referrer-second_level"
                reward_percentage = 0.05 if reward_type == 1 else 0.075  # 5% for reward_type 1, 7.5% for reward_type 2

            message_template = getattr(i18n, message_key)

            # Calculate the reward and update the user's balance
            reward = int(reward_amount * reward_percentage)
            user = await repo.users.select_user(referral.referral_id)
            if user:
                await repo.users.update_user(user_id=referral.referral_id, balance=reward)

            await bot.send_message(referral.referral_id, message_template(new_user=str(new_user_id), points=reward))


async def handle_language_change(call: CallbackQuery, callback_data: Language, i18n: I18nContext, state: FSMContext,
                                 session, redis, bot: Bot, config: Config):
    repo = RequestsRepo(session, redis)
    data = await state.get_data()
    referred_by = int(data.get("referred_by")) if data.get("referred_by") else None
    new_user = await repo.users.create_user(call.message.chat.id, callback_data.lang_code, referred_by)

    if referred_by:
        referrer_info = await repo.referrals.get_referral(referred_by)
        if referrer_info:
            referrer_of_referrer_info = await repo.referrals.get_referral(referrer_info["referral"].referred_by)
        else:
            referrer_of_referrer_info = None
    else:
        referrer_info = None
        referrer_of_referrer_info = None

    reward_amount = config.misc.start_reward

    # Notify referrers and apply referral rewards
    await notify_referrers([referrer_info, referrer_of_referrer_info], new_user.user_id, reward_amount, bot, i18n, repo)

    await i18n.set_locale(callback_data.lang_code)
    await call.message.edit_media(InputMediaPhoto(media=i18n.image.main(), caption=i18n.text.main()),
                                  reply_markup=main_keyboard(i18n))

@user_router.callback_query(Language.filter())
async def choose_language(call: CallbackQuery, callback_data: Language, i18n: I18nContext, state: FSMContext, session,
                          redis, bot: Bot, config: Config):
    await handle_language_change(call, callback_data, i18n, state, session, redis, bot, config)

async def update_media(call: CallbackQuery, i18n: I18nContext, image_key: str, caption_key: str, keyboard=None,
                       **kwargs):
    photo = InputMediaPhoto(media=getattr(i18n.image, image_key)(), caption=getattr(i18n.text, caption_key)(**kwargs))
    await call.message.edit_media(photo, reply_markup=keyboard)

@user_router.callback_query(F.data == "tasks")
async def tasks(call: CallbackQuery, i18n: I18nContext, state: FSMContext, session, redis):
    repo = RequestsRepo(session, redis)
    tasks = await repo.user_tasks.get_incomplete_tasks(call.message.chat.id, i18n.locale)
    await update_media(call, i18n, "tasks", "tasks", tasks_list_keyboard(tasks))

@user_router.callback_query(Tasks.filter())
async def tasks_choice(call: CallbackQuery, state: FSMContext, i18n: I18nContext, callback_data: Tasks, session, redis):
    await call.message.delete()
    task_id = callback_data.task_id
    await state.update_data(task_id=task_id)
    repo = RequestsRepo(session, redis)
    task = await repo.tasks.get_task_by_id(task_id, i18n.locale)

    if task is None:
        await call.answer("Задание не найдено.", show_alert=True)
        return
    text = f"<b>{task.titles}</b>\n\n{task.descriptions or ''}\n\n<i>{i18n.info.reward(reward=str(task.balance))}</i>"
    if task.cover:
        # If cover exists, send the task with the cover image
        await call.message.answer_photo(
            photo=task.cover,
            caption=text,
            reply_markup=task_keyboard(i18n, task.link, task.titles)
        )
    else:
        # If cover does not exist, send the task as a text message
        await call.message.answer(
            text=text,
            reply_markup=task_keyboard(i18n, task.link, task.titles)
        )


@user_router.callback_query(F.data == "check_task")
async def check_task(call: CallbackQuery, i18n: I18nContext, state: FSMContext, bot: Bot, session, redis):
    """
    Checks if the user has completed the task.
    """
    # Retrieve task details from the state
    data = await state.get_data()
    task_id = int(data.get("task_id"))
    repo = RequestsRepo(session, redis)

    # Get task details from the repository
    task = await repo.tasks.get_task_by_id(task_id, i18n.locale)

    # Verify if task exists
    if not task:
        await call.answer("Задание не найдено.", show_alert=True)
        return

    # Check if the task has already been completed by the user
    is_task_completed = await repo.user_tasks.is_task_completed(call.from_user.id, task_id)
    if is_task_completed:
        await call.answer("Вы уже выполнили это задание.", show_alert=True)
        return

    # Check if the task source is 't' (Telegram)
    if task.source == 't':
        # Extract the channel or chat username from the task link
        channel_username = task.link.split('/')[-1]

        # Check if the user is a member of the specified channel
        is_member = await check_user_membership(bot, call.from_user.id, channel_username)

        if is_member:
            await call.answer(i18n.notification.task.completed(), show_alert=True)
            # Mark the task as complete in the database
            await repo.user_tasks.complete_task(call.from_user.id, task_id)
        else:
            await call.answer(i18n.notification.task.not_completed(), show_alert=True)
            return

    else:
        # Handle tasks with other sources if necessary
        await call.answer(i18n.notification.task.completed(), show_alert=True)
    await repo.users.update_user(call.message.chat.id, balance=int(task.balance))
    tasks = await repo.user_tasks.get_incomplete_tasks(call.message.chat.id, i18n.locale)
    try:
        await update_media(call, i18n, "tasks", "tasks", tasks_list_keyboard(tasks))
    except:
        await call.message.delete()
        await call.message.answer_photo(i18n.image.tasks(), i18n.text.tasks(), reply_markup=tasks_list_keyboard(tasks))


@user_router.callback_query(F.data == "friends")
async def friends(call: CallbackQuery, i18n: I18nContext, session, redis):
    repo = RequestsRepo(session, redis)
    referrals = await repo.referrals.count_referrals_by_user(call.message.chat.id)
    await update_media(call, i18n, "friends", "friends", referral_keyboard(i18n, call.message.chat.id),
                       first_referrals=referrals['first_referrals'], second_referrals=referrals['second_referrals'])

@user_router.callback_query(F.data == "leaders")
async def leaders(call: CallbackQuery, i18n: I18nContext, session, redis):
    repo = RequestsRepo(session, redis)
    leaderboard_data = await repo.users.select_leaderboard(call.message.chat.id)

    formatted_leaderboard = "\n".join(f"{entry['place']}. {entry['user_id']} - {entry['balance']}" for entry in leaderboard_data["leaderboard"])

    await update_media(call, i18n, "leaders", "leaders", back_keyboard(i18n), leaders=formatted_leaderboard,
                       place=leaderboard_data['place'])

@user_router.callback_query(F.data == "profile")
async def user_profile(call: CallbackQuery, i18n: I18nContext, session, redis):
    repo = RequestsRepo(session, redis)
    user = await repo.users.select_user(call.message.chat.id)
    await update_media(call, i18n, "profile", "profile", back_keyboard(i18n), balance=str(user.balance).replace(",", " "))


@user_router.callback_query(F.data == "language")
async def change_language(call: CallbackQuery, i18n: I18nContext, session, redis):
    repo = RequestsRepo(session, redis)
    new_language = "en" if i18n.locale == "ru" else "ru"
    await repo.users.update_user(call.message.chat.id, new_language)
    await i18n.set_locale(new_language)
    await update_media(call, i18n, "main", "main", main_keyboard(i18n))


@user_router.callback_query(F.data == "back")
async def back(call: CallbackQuery, i18n: I18nContext):
    try:
        await update_media(call, i18n, "main", "main", main_keyboard(i18n))
    except:
        await call.message.delete()
        await call.message.answer_photo(i18n.image.main(), i18n.text.main(), reply_markup=main_keyboard(i18n))

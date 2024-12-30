import time

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

from funcs import get_link_source, is_valid_url
from infrastructure.database.repo.requests import RequestsRepo
from tgbot.filters.admin import AdminFilter
from tgbot.keyboards.inline import admin_keyboard, task_creation_keyboard, admin_back_keyboard, BackCallbackData, \
    broadcast_creation_keyboard, mailing_keyboard, mailing_tasks_choice
from tgbot.misc.states import TaskCreation, BroadcastCreation

# Create a router specifically for admin-related commands
admin_router = Router()

# Apply the AdminFilter to the router, ensuring that only admins can trigger the handlers
admin_router.message.filter(AdminFilter())

@admin_router.message(Command("admin"))
async def admin_start(message: Message):
    """
    Handles the /admin command for admins.
    """
    await message.answer("Привет, админ!", reply_markup=admin_keyboard())


@admin_router.callback_query(F.data == "mailing")
async def mailing(call: CallbackQuery, state: FSMContext):
    """
    Initiates the broadcast (mailing) creation process.
    """
    await state.clear()  # Clear any existing state data
    broadcast_data = {}
    await state.update_data(broadcast_data=broadcast_data)
    await call.message.edit_text("Выберите элемент для добавления:", reply_markup=broadcast_creation_keyboard(broadcast_data))

@admin_router.callback_query(F.data == "create_broadcast")
async def start_broadcast_creation(call: CallbackQuery, state: FSMContext):
    broadcast_data = await state.get_data()
    await call.message.edit_text("Выберите элемент для добавления:", reply_markup=broadcast_creation_keyboard(broadcast_data))

@admin_router.callback_query(F.data == "set_broadcast_text")
async def set_broadcast_text(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Введите текст рассылки:", reply_markup=admin_back_keyboard("broadcast"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(BroadcastCreation.text)

@admin_router.callback_query(F.data == "set_broadcast_photo")
async def set_broadcast_photo(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Отправьте фото для рассылки:", reply_markup=admin_back_keyboard("broadcast"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(BroadcastCreation.photo)

@admin_router.callback_query(F.data == "set_broadcast_video")
async def set_broadcast_video(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Отправьте видео для рассылки:", reply_markup=admin_back_keyboard("broadcast"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(BroadcastCreation.video)

@admin_router.callback_query(F.data == "set_broadcast_album")
async def set_broadcast_album(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Отправьте альбом (несколько фото) для рассылки:", reply_markup=admin_back_keyboard("broadcast"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(BroadcastCreation.album)


@admin_router.callback_query(F.data == "set_broadcast_button_ru")
async def set_broadcast_button_ru(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Введите текст кнопки на русском:", reply_markup=admin_back_keyboard("broadcast"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(BroadcastCreation.button_text_ru)


@admin_router.callback_query(F.data == "set_broadcast_button_en")
async def set_broadcast_button_en(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Введите текст кнопки на английском:", reply_markup=admin_back_keyboard("broadcast"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(BroadcastCreation.button_text_en)

@admin_router.callback_query(F.data == "select_task_for_mailing")
async def select_task_for_mailing(call: CallbackQuery, state: FSMContext, session, redis):
    repo = RequestsRepo(session, redis)
    tasks = await repo.tasks.list_tasks()
    await call.message.edit_text("Выберите задание для рассылки:", reply_markup=mailing_tasks_choice(tasks))


@admin_router.callback_query(F.data.startswith("task_selected:"))
async def task_selected(call: CallbackQuery, state: FSMContext, bot: Bot):
    task_id = int(call.data.split(":")[1])
    bot_info = await bot.get_me()
    deeplink = f"https://t.me/{bot_info.username}?start=task_{task_id}"

    await state.update_data(task_id=task_id, task_deeplink=deeplink)
    data = await state.get_data()
    await call.message.edit_text("Задание добавлено в рассылку.", reply_markup=broadcast_creation_keyboard(data))

@admin_router.message(BroadcastCreation.photo)
async def enter_broadcast_photo(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    if message.photo:
        photo = message.photo[-1].file_id
        await state.update_data(photo=photo)
    data = await state.get_data()
    await bot.edit_message_text("Фото сохранено.", reply_markup=broadcast_creation_keyboard(data), chat_id=message.from_user.id, message_id=data.get("last_message_id"))

@admin_router.message(BroadcastCreation.video)
async def enter_broadcast_video(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    if message.video:
        video = message.video.file_id
        await state.update_data(video=video)
    data = await state.get_data()
    await bot.edit_message_text("Видео сохранено.", reply_markup=broadcast_creation_keyboard(data), chat_id=message.from_user.id, message_id=data.get("last_message_id"))


@admin_router.message(BroadcastCreation.album)
async def enter_broadcast_album(message: Message, state: FSMContext, bot: Bot):
    await message.delete()

    # Получение текущего состояния данных
    data = await state.get_data()

    # Получение текущей группы медиа
    media_group = data.get("media_group", [])

    # Добавление нового фото в группу
    new_media_group = media_group + [message.photo[-1].file_id]

    # Проверка, изменилось ли содержимое альбома
    if new_media_group != media_group:
        await state.update_data(media_group=new_media_group)

        # Обновляем сообщение только если содержимое изменилось
        await bot.edit_message_text(
            "Фото добавлено в альбом.",
            chat_id=message.from_user.id,
            message_id=data.get("last_message_id"),
            reply_markup=broadcast_creation_keyboard(data)
        )
    else:
        # Если фото уже добавлено, не обновляем сообщение
        await message.answer("Это фото уже было добавлено в альбом.")


@admin_router.callback_query(F.data == "set_broadcast_text_ru")
async def set_broadcast_text_ru(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Введите текст рассылки на русском:", reply_markup=admin_back_keyboard("broadcast"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(BroadcastCreation.text_ru)


@admin_router.callback_query(F.data == "set_broadcast_text_en")
async def set_broadcast_text_en(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Введите текст рассылки на английском:", reply_markup=admin_back_keyboard("broadcast"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(BroadcastCreation.text_en)


@admin_router.message(BroadcastCreation.text_ru)
async def enter_broadcast_text_ru(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    await state.update_data(text_ru=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Текст на русском сохранен.", reply_markup=broadcast_creation_keyboard(data), chat_id=message.from_user.id, message_id=data.get("last_message_id"))

@admin_router.message(BroadcastCreation.text_en)
async def enter_broadcast_text_en(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    await state.update_data(text_en=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Текст на английском сохранен.", reply_markup=broadcast_creation_keyboard(data), chat_id=message.from_user.id, message_id=data.get("last_message_id"))

@admin_router.message(BroadcastCreation.button_text_ru)
async def enter_button_text_ru(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    await state.update_data(button_text_ru=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Текст кнопки на русском сохранен. Теперь введите URL:", reply_markup=admin_back_keyboard("broadcast"), chat_id=message.from_user.id, message_id=data.get("last_message_id"))
    await state.set_state(BroadcastCreation.button_url)


@admin_router.message(BroadcastCreation.button_text_en)
async def enter_button_text_en(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    await state.update_data(button_text_en=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Текст кнопки на английском сохранен. Теперь введите URL:", reply_markup=admin_back_keyboard("broadcast"), chat_id=message.from_user.id, message_id=data.get("last_message_id"))
    await state.set_state(BroadcastCreation.button_url)


@admin_router.message(BroadcastCreation.button_url)
async def enter_button_url(message: Message, state: FSMContext, bot: Bot):
    await message.delete()

    # Capture the button URL entered by the admin
    button_url = message.text

    # Update the FSM context with the button URL
    await state.update_data(button_url=button_url)

    # Retrieve the updated data to use in the keyboard
    data = await state.get_data()

    # Inform the admin that the button URL has been saved
    await bot.edit_message_text(
        "URL кнопки сохранен. Теперь можно сохранить и отправить рассылку.",
        reply_markup=broadcast_creation_keyboard(data),
        chat_id=message.from_user.id,
        message_id=data.get("last_message_id")
    )

@admin_router.callback_query(F.data == "save_broadcast")
async def save_broadcast(call: CallbackQuery, state: FSMContext, session, redis, bot: Bot):
    repo = RequestsRepo(session, redis)
    broadcast_data = await state.get_data()

    users = await repo.users.get_all_users()
    button = None
    button_text_ru = broadcast_data.get("button_text_ru")
    button_text_en = broadcast_data.get("button_text_en")
    button_url = broadcast_data.get("button_url")

    # Check for task deeplink and set button text accordingly
    if broadcast_data.get("task_deeplink"):
        button_text_ru = broadcast_data.get("button_text_ru", "Перейти к заданию")
        button_text_en = broadcast_data.get("button_text_en", "Go to the task")
        button_url = broadcast_data.get("task_deeplink")

    for user in users:
        try:
            # Determine which text and button to send based on the user's language preference
            if user.language == "ru":
                text_to_send = broadcast_data.get("text_ru", '')
                button_text = button_text_ru
            else:
                text_to_send = broadcast_data.get("text_en", '')
                button_text = button_text_en

            # Create the button if the text and URL are provided
            if button_text and button_url:
                button = mailing_keyboard(button_text, button_url)

            if broadcast_data.get("photo"):
                await bot.send_photo(
                    chat_id=user.user_id,
                    photo=broadcast_data['photo'],
                    caption=text_to_send,
                    reply_markup=button
                )
            elif broadcast_data.get("video"):
                await bot.send_video(
                    chat_id=user.user_id,
                    video=broadcast_data['video'],
                    caption=text_to_send,
                    reply_markup=button
                )
            elif broadcast_data.get("media_group"):
                media = [InputMediaPhoto(media=media_id) for media_id in broadcast_data["media_group"]]
                await bot.send_media_group(chat_id=user.user_id, media=media)
                if text_to_send:
                    await bot.send_message(chat_id=user.user_id, text=text_to_send, reply_markup=button)
            else:
                await bot.send_message(chat_id=user.user_id, text=text_to_send, reply_markup=button)
            time.sleep(0.25)
        except Exception as e:
            await call.message.answer(f"Ошибка отправки сообщения пользователю {user.user_id}: {e}")

    await call.message.edit_text("Рассылка успешно завершена!")
    await state.clear()



@admin_router.callback_query(F.data == "cancel_broadcast_creation")
async def cancel_broadcast_creation(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Создание рассылки отменено.", show_alert=True)
    await call.message.edit_text("Привет, админ!", reply_markup=admin_keyboard())

@admin_router.callback_query(F.data == "create_the_task")
async def start_task_creation(call: CallbackQuery, state: FSMContext):
    """
    Initiates the task creation process with a keyboard.
    """
    task_data = await state.get_data()
    await call.message.edit_text("Выберите параметр для настройки:", reply_markup=task_creation_keyboard(task_data))


@admin_router.callback_query(F.data == "set_task_title_ru")
async def set_task_title_ru(call: CallbackQuery, state: FSMContext):
    """
    Asks the admin to enter the task title in Russian.
    """
    m = await call.message.edit_text("Введите название задания на русском:",
                                     reply_markup=admin_back_keyboard("task"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(TaskCreation.title_ru)


@admin_router.callback_query(F.data == "set_task_title_en")
async def set_task_title_en(call: CallbackQuery, state: FSMContext):
    """
    Asks the admin to enter the task title in English.
    """
    m = await call.message.edit_text("Введите название задания на английском:",
                                     reply_markup=admin_back_keyboard("task"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(TaskCreation.title_en)


@admin_router.callback_query(F.data == "set_task_cover")
async def set_task_cover(call: CallbackQuery, state: FSMContext):
    """
    Asks the admin to enter the task cover or send an image.
    """
    m = await call.message.edit_text("Отправьте обложку задания или введите ссылку на изображение:",
                                     reply_markup=admin_back_keyboard("task"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(TaskCreation.cover)


@admin_router.callback_query(F.data == "set_task_link")
async def set_task_link(call: CallbackQuery, state: FSMContext):
    """
    Asks the admin to enter the task link.
    """
    m = await call.message.edit_text("Введите ссылку на задание:",
                                     reply_markup=admin_back_keyboard("task"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(TaskCreation.link)


@admin_router.callback_query(F.data == "set_task_description_ru")
async def set_task_description_ru(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Введите описание задания на русском:",
                                     reply_markup=admin_back_keyboard("task"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(TaskCreation.description_ru)


@admin_router.callback_query(F.data == "set_task_description_en")
async def set_task_description_en(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Введите описание задания на английском:",
                                     reply_markup=admin_back_keyboard("task"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(TaskCreation.description_en)

@admin_router.callback_query(F.data == "set_task_balance")
async def set_task_balance(call: CallbackQuery, state: FSMContext):
    m = await call.message.edit_text("Введите баланс задания:",
                                     reply_markup=admin_back_keyboard("task"))
    await state.update_data(last_message_id=m.message_id)
    await state.set_state(TaskCreation.balance)


# Handler for capturing the task description in Russian
@admin_router.message(TaskCreation.description_ru)
async def enter_task_description_ru(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    """
    Captures the task description in Russian from the admin.
    """
    await state.update_data(description_ru=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Описание задания на русском сохранено.",
                                reply_markup=task_creation_keyboard(data),
                                chat_id=message.from_user.id,
                                message_id=data.get("last_message_id"))


# Handler for capturing the task description in English
@admin_router.message(TaskCreation.description_en)
async def enter_task_description_en(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    """
    Captures the task description in English from the admin.
    """
    await state.update_data(description_en=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Описание задания на английском сохранено.",
                                reply_markup=task_creation_keyboard(data),
                                chat_id=message.from_user.id,
                                message_id=data.get("last_message_id"))


# Handler for capturing the task title in Russian
@admin_router.message(TaskCreation.title_ru)
async def enter_task_title_ru(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    """
    Captures the task title in Russian from the admin.
    """
    await state.update_data(title_ru=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Название задания на русском сохранено.",
                                reply_markup=task_creation_keyboard(data),
                                chat_id=message.from_user.id,
                                message_id=data.get("last_message_id"))


# Handler for capturing the task title in English
@admin_router.message(TaskCreation.title_en)
async def enter_task_title_en(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    """
    Captures the task title in English from the admin.
    """
    await state.update_data(title_en=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Название задания на английском сохранено.",
                                reply_markup=task_creation_keyboard(data),
                                chat_id=message.from_user.id,
                                message_id=data.get("last_message_id"))


# Handler for capturing the task link
@admin_router.message(TaskCreation.link)
async def enter_task_link(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if not is_valid_url(message.text):
        await bot.edit_message_text("Введите валидную ссылку.",
                                    reply_markup=admin_back_keyboard("task"),
                                    chat_id=message.from_user.id,
                                    message_id=data.get("last_message_id"))
        return
    await message.delete()
    """
    Captures the task link from the admin.
    """
    await state.update_data(link=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Ссылка на задание сохранена.",
                                reply_markup=task_creation_keyboard(data),
                                chat_id=message.from_user.id,
                                message_id=data.get("last_message_id"))


# Handler for capturing the task cover
@admin_router.message(TaskCreation.cover)
async def enter_task_cover(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    """
    Captures the task cover from the admin and finalizes the task creation.
    """
    if message.photo:
        cover = message.photo[-1].file_id  # Use the file_id for storing the photo
    else:
        cover = message.text  # Assume it's a URL if no photo is provided

    await state.update_data(cover=cover)
    data = await state.get_data()
    await bot.edit_message_text("Обложка задания сохранена.",
                                reply_markup=task_creation_keyboard(data),
                                chat_id=message.from_user.id,
                                message_id=data.get("last_message_id"))


@admin_router.message(TaskCreation.balance)
async def enter_task_balance(message: Message, state: FSMContext, bot: Bot):
    await message.delete()
    await state.update_data(balance=message.text)
    data = await state.get_data()
    await bot.edit_message_text("Баланс задания сохранен.",
                                reply_markup=task_creation_keyboard(data),
                                chat_id=message.from_user.id,
                                message_id=data.get("last_message_id"))

@admin_router.callback_query(F.data == "save_task")
async def save_task(call: CallbackQuery, state: FSMContext, session, redis):
    repo = RequestsRepo(session, redis)
    task_data = await state.get_data()

    if not task_data.get('title_ru') or not task_data.get('title_en'):
        await call.answer("Название задания обязательно на обоих языках. Пожалуйста, введите название.")
        return

    if not task_data.get('link'):
        await call.answer("Ссылка на ресурс обязательна. Пожалуйста, отправьте ссылку на ресурс.")
        return

    await repo.tasks.create_task({
        "titles": {"ru": task_data['title_ru'], "en": task_data['title_en']},
        "link": task_data.get('link'),
        "cover": task_data.get('cover') or '',
        "source": get_link_source(task_data.get('link')),
        "descriptions": {
            "ru": task_data.get('description_ru'),
            "en": task_data.get('description_en')
        },
        "balance": int(task_data.get('balance')),
    })

    await call.message.edit_text("Задание успешно создано!")
    await state.clear()


@admin_router.callback_query(F.data == "cancel_task_creation")
async def cancel_task_creation(call: CallbackQuery, state: FSMContext):
    """
    Cancels the task creation process.
    """
    await state.clear()
    await call.answer("Создание задания отменено.", show_alert=True)
    await call.message.edit_text("Привет, админ!", reply_markup=admin_keyboard())


@admin_router.callback_query(BackCallbackData.filter())
async def back_callback_data(call: CallbackQuery, state: FSMContext, callback_data: BackCallbackData):
    data = await state.get_data()
    if callback_data.state == "task":
        await call.message.edit_text("Выберите параметр для настройки:", reply_markup=task_creation_keyboard(data))
    elif callback_data.state == "broadcast":
        await call.message.edit_text("Выберите элемент для добавления:", reply_markup=broadcast_creation_keyboard(data))

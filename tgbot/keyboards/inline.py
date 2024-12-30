from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class BackCallbackData(CallbackData, prefix="back"):
    state: str

def admin_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="Рассылка", callback_data="mailing")
        ],
        [
            InlineKeyboardButton(text="Создать задание", callback_data="create_the_task"),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

def admin_back_keyboard(state):
    buttons = [
        [
            InlineKeyboardButton(text="🔙Назад", callback_data=BackCallbackData(state=state).pack())
        ]
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

def broadcast_creation_keyboard(broadcast_data: dict) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"Текст (RU){' ✅' if broadcast_data.get('text_ru') else ''}",
                callback_data="set_broadcast_text_ru"
            ),
            InlineKeyboardButton(
                text=f"Текст (EN){' ✅' if broadcast_data.get('text_en') else ''}",
                callback_data="set_broadcast_text_en"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Кнопка (RU){' ✅' if broadcast_data.get('button_text_ru') else ''}",
                callback_data="set_broadcast_button_ru"
            ),
            InlineKeyboardButton(
                text=f"Кнопка (EN){' ✅' if broadcast_data.get('button_text_en') else ''}",
                callback_data="set_broadcast_button_en"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Фото{' ✅' if broadcast_data.get('photo') else ''}",
                callback_data="set_broadcast_photo"
            ),
            InlineKeyboardButton(
                text=f"Видео{' ✅' if broadcast_data.get('video') else ''}",
                callback_data="set_broadcast_video"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Альбом{' ✅' if broadcast_data.get('media_group') else ''}",
                callback_data="set_broadcast_album"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Кнопка с ссылкой{' ✅' if broadcast_data.get('button_text') else ''}",
                callback_data="set_broadcast_button"
            ),
            InlineKeyboardButton(
                text=f"Задание{' ✅' if broadcast_data.get('task_id') else ''}",
                callback_data="select_task_for_mailing"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Сохранить и отправить",
                callback_data="save_broadcast"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Отменить",
                callback_data="cancel_broadcast_creation"
            ),
        ]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


def mailing_keyboard(button_text, button_url):
    buttons = [
        [
            InlineKeyboardButton(text=button_text, url=button_url)
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def mailing_tasks_choice(tasks):
    keyboard = InlineKeyboardBuilder()
    for task in tasks:
        keyboard.button(
                text=task.titles,
                callback_data=f"task_selected:{task.task_id}"
        )

    keyboard.adjust(1, True)
    return keyboard.as_markup()

def task_creation_keyboard(task_data: dict) -> InlineKeyboardMarkup:
    """
    Generates a keyboard for task creation, showing checkmarks for completed fields.

    :param task_data: A dictionary containing the current task data from FSMContext.
    :return: InlineKeyboardMarkup object for the task creation process.
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=f"Название (RU){' ✅' if task_data.get('title_ru') else ''}",
                callback_data="set_task_title_ru"
            ),
            InlineKeyboardButton(
                text=f"Название (EN){' ✅' if task_data.get('title_en') else ''}",
                callback_data="set_task_title_en"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Описание (RU){' ✅' if task_data.get('description_ru') else ''}",
                callback_data="set_task_description_ru"
            ),
            InlineKeyboardButton(
                text=f"Описание (EN){' ✅' if task_data.get('description_en') else ''}",
                callback_data="set_task_description_en"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Обложка{' ✅' if task_data.get('cover') else ''}",
                callback_data="set_task_cover"
            ),
            InlineKeyboardButton(
                text=f"Ссылка{' ✅' if task_data.get('link') else ''}",
                callback_data="set_task_link"
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"Баланс{' ✅' if task_data.get('balance') else ''}",
                callback_data="set_task_balance"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Сохранить",
                callback_data="save_task"
            ),
        ],
        [
            InlineKeyboardButton(
                text="Отменить",
                callback_data="cancel_task_creation"
            ),
        ]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard


class Tasks(CallbackData, prefix="tasks"):
    task_id: int

def tasks_list_keyboard(tasks):
    keyboard = InlineKeyboardBuilder()
    for task in tasks:
        keyboard.button(text=task[1], callback_data=Tasks(task_id=task[0]).pack())
    keyboard.button(text="🔙Назад", callback_data="back")
    keyboard.adjust(1)
    return keyboard.as_markup()


def task_keyboard(i18n, link, title):
    buttons = [
        [
            InlineKeyboardButton(text=title, url=link),
        ],
        [
            InlineKeyboardButton(text=i18n.button.check_task(), callback_data="check_task"),
        ],
        [
            InlineKeyboardButton(text=i18n.button.back(), callback_data="back")
        ]
    ]
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

class Language(CallbackData, prefix="language"):
    lang_code: str


def language_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="🇷🇺", callback_data=Language(lang_code="ru").pack()),
            InlineKeyboardButton(text="🇬🇧", callback_data=Language(lang_code="en").pack()),
        ],
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def main_keyboard(i18n):
    buttons = [
        [
            InlineKeyboardButton(text=i18n.button.tasks(), callback_data="tasks"),
            InlineKeyboardButton(text=i18n.button.friends(), callback_data="friends"),
        ],
        [
            InlineKeyboardButton(text=i18n.button.leaders(), callback_data="leaders"),
            InlineKeyboardButton(text=i18n.button.profile(), callback_data="profile"),
        ],
        [
            InlineKeyboardButton(text="🇬🇧" if i18n.locale == "ru" else "🇷🇺", callback_data="language")
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

def back_keyboard(i18n):
    buttons = [
        [
            InlineKeyboardButton(text=i18n.button.back(), callback_data="back")
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard


def referral_keyboard(i18n, user_id):
    buttons = [
        [
          InlineKeyboardButton(text=i18n.button.invite(), url=f'https://t.me/share/url?url=https://t.me/tsar_dynasty_bot?start={user_id}')
        ],
        [
            InlineKeyboardButton(text=i18n.button.back(), callback_data="back")
        ]
    ]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )
    return keyboard

from aiogram.fsm.state import StatesGroup, State


class TaskCreation(StatesGroup):
    title = State()
    link = State()
    cover = State()
    title_ru = State()
    title_en = State()
    description_ru = State()
    description_en = State()
    balance = State()


class BroadcastCreation(StatesGroup):
    text_ru = State()
    text_en = State()
    photo = State()
    video = State()
    album = State()
    button_text_ru = State()
    button_text_en = State()
    button_url = State()

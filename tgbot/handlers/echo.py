from aiogram import types, Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hcode

# Create a router for handling echo messages
echo_router = Router()


@echo_router.message(F.text, StateFilter(None))
async def bot_echo(message: types.Message):
    """
    Handles echo messages when the user is not in any FSM state.

    Args:
        message (types.Message): The incoming message object containing user and message data.

    Response:
        Replies with an echo of the user's message, indicating that no state is active.
    """
    text = [
        "Эхо без состояния.",  # Indicates that the user is not in any state
        "Содержание:",  # Label for the content of the message
        message.text,  # The content of the user's message
    ]

    # Reply with the formatted text
    await message.answer("\n".join(text))


@echo_router.message(F.text)
async def bot_echo_all(message: types.Message, state: FSMContext):
    """
    Handles echo messages when the user is in any FSM state.

    Args:
        message (types.Message): The incoming message object containing user and message data.
        state (FSMContext): The current finite state machine (FSM) context for the user.

    Response:
        Replies with an echo of the user's message, including the current state information.
    """
    # Get the current state of the user
    state_name = await state.get_state()

    # Prepare the response text with the current state and message content
    text = [
        f"Эхо в состоянии {hcode(state_name)}",  # Echo message with state information
        "Содержание:",  # Label for the content of the message
        hcode(message.text),  # The content of the user's message, formatted with hcode
    ]

    # Reply with the formatted text
    await message.answer("\n".join(text))

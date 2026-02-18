from aiogram import Router
from bot.handlers.registration import router as registration_router
from aiogram.types import Message
from aiogram.filters import Command
from loguru import logger



router = Router(name="main")
router.include_router(registration_router)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "<b>Справка по AI University</b>\n\n"
        "Доступные команды:\n"
        "/start - Начать регистрацию / войти\n"
        "/help - Справка"
    )

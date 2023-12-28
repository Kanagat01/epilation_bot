from aiogram import Router, F
from aiogram.types import Message

from create_bot import bot


router = Router()
@router.message(F.text == "Написать Оксане в личку")
async def write_to_personal(message: Message):
    text = "Сюда ➡️ https://t.me/neprostowaxing"
    await bot.send_message(chat_id=message.from_user.id, text=text)
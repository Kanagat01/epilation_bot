from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from create_bot import bot
from tgbot.models.sql_connector import TextsDAO

router = Router()


async def address_render(user_id: int | str):
    videos = []
    video1 = await TextsDAO.get_one_or_none(chapter="video_1|address")
    video2 = await TextsDAO.get_one_or_none(chapter="video_2|address")
    if video1:
        videos.append(video1)
    if video2:
        videos.append(video2)
    if len(videos) != 0:
        media_group = [{"media": video["text"], "type": "video"}
                       for video in videos]
        await bot.send_media_group(chat_id=user_id, media=media_group)

    text = await TextsDAO.get_one_or_none(chapter="text|address")
    location = await TextsDAO.get_one_or_none(chapter="location|address")
    if text:
        await bot.send_message(chat_id=user_id, text=text["text"])
    if location:
        latitude = location["text"].split("|")[1]
        longitude = location["text"].split("|")[0]
        await bot.send_location(chat_id=user_id, latitude=latitude, longitude=longitude)


@router.message(Command("address"))
@router.message(F.text == "Адрес")
async def address(message: Message):
    await address_render(user_id=message.from_user.id)
    await message.delete()


@router.callback_query(F.data == "address")
async def address(callback: CallbackQuery):
    await address_render(user_id=callback.from_user.id)
    await bot.answer_callback_query(callback.id)

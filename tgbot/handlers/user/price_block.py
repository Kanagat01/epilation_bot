from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from create_bot import bot
from tgbot.models.sql_connector import RegistrationsDAO, TextsDAO, StaticsDAO
from tgbot.keyboards.inline import UserInlineKeyboard as inline_kb
from tgbot.models.sql_connector import ClientsDAO

router = Router()


async def price_main(user_id: int | str, gender: str):
    finished_registrations = await RegistrationsDAO.get_by_user_id(user_id=user_id)
    no_photo = await StaticsDAO.get_one_or_none(title="no_photo")
    if len(finished_registrations) == 0:
        new_clients_photo = await TextsDAO.get_one_or_none(chapter="new_clients|price_list")
        new_clients_photo = new_clients_photo["text"] if new_clients_photo is not None else no_photo["file_id"]
        await bot.send_photo(chat_id=user_id, photo=new_clients_photo)
    await price_render(user_id=user_id, gender=gender)


async def price_render(user_id: str, gender: str):
    no_photo = await StaticsDAO.get_one_or_none(title="no_photo")
    laser_photo = await TextsDAO.get_one_or_none(chapter=f"laser_{gender}|price_list")
    bio_photo = await TextsDAO.get_one_or_none(chapter=f"bio_{gender}|price_list")
    bio_abonements = await TextsDAO.get_one_or_none(chapter="bio_abonements|price_list")
    laser_photo = laser_photo["text"] if laser_photo is not None else no_photo["file_id"]
    bio_photo = bio_photo["text"] if bio_photo is not None else no_photo["file_id"]
    bio_abonements = bio_abonements["text"] if bio_abonements is not None else no_photo["file_id"]
    kb = inline_kb.price_gender_kb(gender=gender)
    await bot.send_photo(chat_id=user_id, photo=laser_photo)
    await bot.send_photo(chat_id=user_id, photo=bio_photo)
    await bot.send_photo(chat_id=user_id, photo=bio_abonements, reply_markup=kb)


@router.message(F.text == "Прайс")
async def price_list(message: Message):
    user = await ClientsDAO.get_one_or_none(user_id=str(message.from_user.id))
    gender = user["gender"] if user["gender"] not in [
        "", "unknown"] else "girls"
    await price_main(user_id=str(message.from_user.id), gender=gender)


@router.callback_query(F.data == "price")
async def price_list(callback: CallbackQuery):
    user = await ClientsDAO.get_one_or_none(user_id=str(callback.from_user.id))
    gender = user["gender"] if user["gender"] not in [
        "", "unknown"] else "girls"
    await price_main(user_id=str(callback.from_user.id), gender=gender)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data.split(":")[0] == "price_gender")
async def price_list(callback: CallbackQuery):
    gender = callback.data.split(":")[1]
    await price_render(gender=gender, user_id=callback.from_user.id)
    await bot.answer_callback_query(callback.id)

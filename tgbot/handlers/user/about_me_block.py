from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from create_bot import bot
from tgbot.handlers.helpers import feedbacks_media_group
from tgbot.models.sql_connector import TextsDAO, ClientsDAO, StaticsDAO
from tgbot.keyboards.inline import UserInlineKeyboard as inline_kb

router = Router()


@router.message(F.text == "Обо мне и отзывы")
@router.message(Command("about_me"))
async def about_me_render(message: Message):
    photo = await TextsDAO.get_one_or_none(chapter="photo|about_me")
    text = await TextsDAO.get_one_or_none(chapter="text|about_me")
    kb = inline_kb.about_me_kb()
    if photo:
        await message.answer_photo(photo=photo["text"])
    else:
        photo = await StaticsDAO.get_one_or_none(title="no_photo")
        await message.answer_photo(photo=photo["file_id"])
    if text:
        await message.answer(text=text["text"], reply_markup=kb)
    else:
        await message.answer(text="ТЕКСТ ОТСУТСТВУЕТ", reply_markup=kb)


@router.callback_query(F.data == "about_me_video")
async def about_me_video(callback: CallbackQuery):
    video = await TextsDAO.get_one_or_none(chapter="video|about_me")
    kb = inline_kb.about_me_kb()
    if video:
        await callback.message.answer_video(video=video["text"], reply_markup=kb)
    else:
        await callback.message.answer(text="ВИДЕО ОТСУТСТВУЕТ", reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.message(F.text == "Написать отзыв")
async def write_feedback(message: Message):
    text = [
        "Буду благодарна 😇 вашему отзыву:",
        "https://yandex.ru/maps/org/ne_prosto_waxing/47348048631/reviews/"
    ]
    await message.answer("\n".join(text))


async def girls_feedbacks_choice(user_id: int | str):
    text = "🙌  осталось выбрать о каком виде депиляции вы хотели бы почитать отзывы?"
    kb = inline_kb.feedbacks_categories_kb()
    await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)


async def boys_feedback_render(user_id: str | int, page: int):
    user_id = int(user_id)
    next_page = await feedbacks_media_group(page, "feedback_boys", user_id)
    kb = inline_kb.feedbacks_boys_kb(page=next_page)
    if next_page != 0:
        text = 'Чтобы посмотреть больше отзывов, нажмите на кнопку "Читать ещё".'
    else:
        text = "Пока это все отзывы, которые я выложила"
    await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)


@router.callback_query(F.data == "read_feedbacks")
async def read_feedbacks(callback: CallbackQuery):
    user = await ClientsDAO.get_one_or_none(user_id=str(callback.from_user.id))
    if not user:
        return
    if user["gender"] == "boys":
        await boys_feedback_render(page=1, user_id=callback.from_user.id)
    elif user["gender"] == "girls":
        await girls_feedbacks_choice(user_id=callback.from_user.id)
    else:
        text = "😎  Отзывов у меня очень много. Для вашего удобства я их разделила на  👩‍🦰 и 👨   , и сделала 2 " \
               "категории. Выбирайте пожалуйста интересную вам ☘"
        kb = inline_kb.feedbacks_gender_kb()
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.split("|")[0] == "feedbacks_boys")
async def refresh_feedback_boys(callback: CallbackQuery):
    page = callback.data.split("|")[1].split(":")[1]
    if page == "start":
        page = 1
    else:
        page = int(page)
    await callback.message.delete()
    await boys_feedback_render(user_id=callback.from_user.id, page=page)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data == "feedbacks_girls")
async def feedbacks_girls(callback: CallbackQuery):
    await girls_feedbacks_choice(user_id=callback.from_user.id)


@router.callback_query(F.data.split(":")[0] == "feedback_girls_laser")
@router.callback_query(F.data.split(":")[0] == "feedback_girls_bio")
async def feedback_girls_category(callback: CallbackQuery):
    category, page = callback.data.split(":")
    page = int(page)
    user_id = callback.from_user.id
    next_page = await feedbacks_media_group(page, category, user_id)
    kb = inline_kb.feedbacks_girls_kb(page=next_page, category=category)
    if next_page != 0:
        text = "Чтобы посмотреть больше отзывов, нажмите на кнопку \"Читать еще \""
    else:
        text = "Отзывов больше нет"
    await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)

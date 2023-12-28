import glob
import os
from typing import Literal

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram import F, Router

from create_bot import bot
from tgbot.filters.admin import AdminFilter
from tgbot.keyboards.inline import AdminInlineKeyboard as inline_kb
from tgbot.keyboards.reply import AdminReplyKeyboard as reply_kb
from tgbot.misc.states import AdminFSM
from tgbot.models.redis_connector import RedisConnector as rds
from tgbot.models.sql_connector import TextsDAO, ServicesDAO, StaticsDAO

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


async def refresh_static_file(
        category: str,
        file_type: Literal["photo", "video"],
        file_name: str,
        chat_id: str | int
):
    file = FSInputFile(path=file_name)
    if file_type == "photo":
        msg = await bot.send_photo(chat_id=chat_id, photo=file)
        file_id = msg.photo[-1].file_id
    elif file_type == "video":
        msg = await bot.send_video(chat_id=chat_id, video=file)
        file_id = msg.video.file_id
    else:
        msg, file_id = None, None

    if "\\" in file_name:
        file_name = file_name.split("\\")[-1].split(".")[0]
    else:
        file_name = file_name.split("/")[-1].split(".")[0]

    await bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
    await StaticsDAO.create(category=category, title=file_name, file_id=file_id)


@router.message(Command("refresh_static"))
async def refresh_static(message: Message):
    await message.delete()
    await StaticsDAO.delete_all()
    static_path = f"{os.getcwd()}/tgbot/static"
    directories = ["", "create_reg", "feedback_boys", "feedback_girls_laser", "feedback_girls_bio", "laser_boys", "laser_girls", "bio_boys", "bio_girls"]
    for directory in directories:
        file_list = []
        for file_type in ["jpg", "jpeg", "png"]:
            file_list.extend(
                glob.glob(f"{static_path}/{directory}/*.{file_type}"))
        for file in file_list:
            await refresh_static_file(category=directory, file_type="photo", file_name=file, chat_id=message.from_user.id)

        file_list = []
        for file_type in ["mp4", "mov"]:
            file_list.extend(
                glob.glob(f"{static_path}/{directory}/*.{file_type}"))
        for file in file_list:
            await refresh_static_file(category=directory, file_type="video", file_name=file, chat_id=message.from_user.id)


@router.message(F.text == "Управлять контентом")
async def content_management(message: Message):
    text = 'Раздел "Управление контентом".\nВыберите, что вы хотите сделать:'
    kb = inline_kb.content_management_kb()
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "content_management")
async def content_management(callback: CallbackQuery):
    text = 'Раздел "Управление контентом".\nВыберите, что вы хотите сделать:'
    kb = inline_kb.content_management_kb()
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


##############
# Редактура текстов авторассылки

@router.callback_query(F.data == "edit_auto_texts")
async def edit_auto_texts(callback: CallbackQuery):
    text = "Выберите контент, который вы хотите изменить:"
    kb = inline_kb.edit_auto_texts_kb()
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data.split(":")[0] == "auto_text")
async def current_text_clb(callback: CallbackQuery, state: FSMContext):
    chapter = callback.data.split(":")[1]
    current_text_dict = await TextsDAO.get_one_or_none(chapter=f"text|{chapter}")
    current_photo_dict = await TextsDAO.get_one_or_none(chapter=f"photo|{chapter}")
    if current_photo_dict and current_photo_dict["text"] != "":
        current_text = None if current_text_dict["text"] == "" else current_text_dict["text"]
        await callback.message.answer_photo(photo=current_photo_dict["text"], caption=current_text)
    else:
        if current_text_dict:
            first_msg = current_text_dict["text"]
        else:
            first_msg = "Текст не задан"
        await callback.message.answer(first_msg)
    second_msg = "Текущее сообщение ☝️\nОтправьте сообщение, на которое нужно его заменить:"
    kb = inline_kb.back_btn(cb_data="edit_auto_texts")
    await state.update_data(current_photo=current_photo_dict, current_text=current_text_dict, chapter=chapter)
    await state.set_state(AdminFSM.auto_texts)
    await callback.message.answer(second_msg, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.message(AdminFSM.auto_texts)
async def update_auto_text(message: Message, state: FSMContext):
    state_data = await state.get_data()
    current_photo = state_data["current_photo"]
    current_text = state_data["current_text"]
    chapter = state_data["chapter"]
    if message.content_type == "text":
        new_text = message.html_text
        if current_text:
            await TextsDAO.update(chapter=f"text|{chapter}", text=new_text)
        else:
            await TextsDAO.create(chapter=f"text|{chapter}", text=new_text)
        await state.set_state(AdminFSM.home)
        text = "Выберите контент, который вы хотите изменить:"
        kb = inline_kb.edit_auto_texts_kb()
    elif message.content_type == "photo":
        new_text = message.html_text if message.caption else ""
        new_photo = message.photo[-1].file_id
        if current_text:
            await TextsDAO.update(chapter=f"text|{chapter}", text=new_text)
        else:
            await TextsDAO.create(chapter=f"text|{chapter}", text=new_text)
        if current_photo:
            await TextsDAO.update(chapter=f"photo|{chapter}", text=new_photo)
        else:
            await TextsDAO.create(chapter=f"photo|{chapter}", text=new_photo)
        await state.set_state(AdminFSM.home)
        text = "Выберите контент, который вы хотите изменить:"
        kb = inline_kb.edit_auto_texts_kb()
    else:
        if current_text:
            first_msg = current_text
        else:
            first_msg = "Текст не задан"
        text = "Текущее сообщение ☝️\nОтправьте сообщение, на которое нужно его заменить:"
        kb = inline_kb.back_btn(cb_data="edit_auto_texts")
        await state.update_data(current_text=current_text, chapter=chapter)
        await state.set_state(AdminFSM.auto_texts)
        await message.answer(first_msg)
    await message.answer(text, reply_markup=kb)


##############
# Редактура услуг

def service_profile_render(service: dict, service_id: int):
    duration_int = service["duration"]
    duration_str = f"{duration_int // 60}ч {duration_int % 60}мин"
    status_dict = {"enabled": "Активная", "disabled": "Неактивная"}
    category_dict = {"bio": "Био", "laser": "Лазер"}
    gender_dict = {"boys": "Мужчины", "girls": "Девушки"}
    service_profile = [
        f"Раздел {gender_dict[service['gender']]} - {category_dict[service['category']]}",
        f"<b>{service['title']}</b>",
        f"Цена: <i>{service['price']}₽</i>",
        f"Длительность: <i>{duration_str}</i>",
        f"Порядок отображения клиенту: <i>{service['ordering']}</i>",
        f"Статус: {status_dict[service['status']]}\n",
        "Выберите, что вы хотите отредактировать.\n"
        'Услугу можно скрыть. Тогда она не будет отображаться клиентам при записи на процедуру. Это не повлияет '
        'на запись через кнопку "Повторить" (клиенты смогут записаться на эту же услугу, если они записывались на '
        'неё ранее).'
    ]
    text = "\n".join(service_profile)
    kb = inline_kb.edit_service_kb(service_id=service_id, status=service["status"], gender=service["gender"],
                                   category=service["category"])
    return text, kb


@router.callback_query(F.data == "edit_prices")
async def edit_prices(callback: CallbackQuery):
    text = "Выберите вид эпиляции и пол:"
    kb = inline_kb.epil_gender_kb()
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data.split(":")[0] == "epil_gender")
async def epil_gender(callback: CallbackQuery):
    category = callback.data.split(":")[1].split("|")[0]
    gender = callback.data.split(":")[1].split("|")[1]
    services = await ServicesDAO.get_order_list(category=category, gender=gender)
    text = "Текущие услуги в боте:"
    kb = inline_kb.services_kb(
        services=services, category=category, gender=gender)
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data.split(":")[0] == "new_service")
async def new_service(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1].split("|")[0]
    gender = callback.data.split(":")[1].split("|")[1]
    category_dict = {"bio": "Био", "laser": "Лазер"}
    gender_dict = {"boys": "Мужчины", "girls": "Девушки"}
    await state.set_state(AdminFSM.new_service)
    await state.update_data(category=category, gender=gender)
    text = [
        f"<b>Создание услуги {category_dict[category]} для {gender_dict[gender]}:</b>",
        "Введите, разделяя новой строкой, данные:",
        "Название услуги",
        "Цену в рублях (только число)",
        "Длительность в минутах (только число)",
        "<b>Пример:</b>",
        "Глубокое бикини",
        "1900",
        "90",
    ]
    await callback.message.answer("\n".join(text))
    await bot.answer_callback_query(callback.id)


@router.message(F.text, AdminFSM.new_service)
async def new_service(message: Message, state: FSMContext):
    try:
        service_list = message.text.split("\n")
        title = service_list[0].strip()
        price = int(service_list[1].strip())
        duration = int(service_list[2].strip())
        state_data = await state.get_data()
        category = state_data["category"]
        gender = state_data["gender"]
        await ServicesDAO.create(category=category, gender=gender, title=title, price=price, duration=duration)
        services = await ServicesDAO.get_many(category=category, gender=gender)
        text = "Текущие услуги в боте:"
        kb = inline_kb.services_kb(
            services=services, category=category, gender=gender)
        await state.set_state(AdminFSM.home)
    except (IndexError, ValueError):
        text = "Вы ввели данные в неверном формате"
        kb = None
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "service_profile")
async def edit_service(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1])
    service = await ServicesDAO.get_one_or_none(id=service_id)
    if service:
        text, kb = service_profile_render(service, service_id)
    else:
        text = "Что-то пошло не так. Услуга не найдена"
        kb = None
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data.split(":")[0] == "edit_service")
async def edit_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1].split("|")[0])
    edit_object = callback.data.split(":")[1].split("|")[1]
    if edit_object in ["price", "duration", "ordering"]:
        text = "Введите целое число"
    else:
        text = "Введите новое значение"
    await state.update_data(edit_object=edit_object, service_id=service_id)
    await state.set_state(AdminFSM.edit_service)
    await callback.message.answer(text)
    await bot.answer_callback_query(callback.id)


@router.message(F.text, AdminFSM.edit_service)
async def edit_service(message: Message, state: FSMContext):
    state_data = await state.get_data()
    edit_object = state_data["edit_object"]
    service_id = state_data["service_id"]
    try:
        if edit_object in ["price", "duration", "ordering"]:
            new_value = int(message.text)
        else:
            new_value = message.text
        data = {edit_object: new_value}
        await ServicesDAO.update(service_id=service_id, data=data)
        service = await ServicesDAO.get_one_or_none(id=service_id)
        text, kb = service_profile_render(service, service_id)
    except ValueError:
        text = "Нужно ввести целое число"
        kb = None
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "edit_service_status")
async def edit_service_status(callback: CallbackQuery):
    service_id = int(callback.data.split(":")[1].split("|")[0])
    new_state_rus = callback.data.split(":")[1].split("|")[1]
    new_status_dict = {"🚫 Скрыть": "disabled", "Показать": "enabled"}
    data = {"status": new_status_dict[new_state_rus]}
    await ServicesDAO.update(service_id=service_id, data=data)
    service = await ServicesDAO.get_one_or_none(id=service_id)
    text, kb = service_profile_render(service, service_id)
    await callback.message.edit_text(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


##############
# Редактура инфо блока


@router.callback_query(F.data == "edit_info_blocks")
async def edit_info_blocks(callback: CallbackQuery):
    text = "Выберите раздел:"
    kb = inline_kb.edit_info_block_kb()
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data.split(":")[0] == "edit_info_block")
async def edit_info_blocks(callback: CallbackQuery):
    text = "Выберите контент, который вы хотите изменить:"
    block = callback.data.split(":")[1]
    if block == "address":
        kb = inline_kb.edit_address_kb()
    elif block == "about_me":
        kb = inline_kb.edit_about_me_kb()
    else:
        kb = inline_kb.edit_price_list_kb()
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


###################
# Редактура адреса

@router.callback_query(F.data.split(":")[0] == "edit_address")
async def edit_address(callback: CallbackQuery, state: FSMContext):
    edit_subject = callback.data.split(":")[1]
    chapter = f"{edit_subject}|address"
    current_subject = await TextsDAO.get_one_or_none(chapter=chapter)
    if edit_subject == "video_from_kremlin":
        if current_subject:
            await callback.message.answer_video(video=current_subject["text"])
        else:
            await callback.message.answer("🤷 Данные отсутствуют")
        text = "Текущее видео ☝️\nОтправьте ответным сообщением видео, на которое его следует заменить:"
        await state.set_state(AdminFSM.address_video)
        
    elif edit_subject == "video_from_river":
        if current_subject:
            await callback.message.answer_video(video=current_subject["text"])
        else:
            await callback.message.answer("🤷 Данные отсутствуют")
        text = "Текущее видео ☝️\nОтправьте ответным сообщением видео, на которое его следует заменить:"
        await state.set_state(AdminFSM.address_video)
        
    elif edit_subject == "location":
        if current_subject:
            longitude = current_subject["text"].split("|")[0]
            latitude = current_subject["text"].split("|")[1]
            await callback.message.answer_location(longitude=longitude, latitude=latitude)
        else:
            await callback.message.answer("🤷 Данные отсутствуют")
        text = "Текущая геометка ☝️\nОтправьте ответным сообщением геометку, на которую её следует " \
               "заменить.\nВажно! Геометка заменится также в сообщении за 2 часа до приёма."
        await state.set_state(AdminFSM.address_location)
    else:
        if current_subject:
            await callback.message.answer(text=current_subject["text"])
        else:
            await callback.message.answer("🤷 Данные отсутствуют")
        text = "Текущий текст ☝️\nОтправьте ответным сообщением новый текст, на который его следует заменить:"
        await state.set_state(AdminFSM.address_text)
    await state.update_data(current_subject=current_subject, edit_subject=edit_subject)
    chapter = "address"
    kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.message(AdminFSM.address_video)
async def address_video(message: Message, state: FSMContext):
    state_data = await state.get_data()
    current_subject = state_data["current_subject"]
    edit_subject = state_data["edit_subject"]
    if message.content_type == "video":
        video_id = message.video.file_id
        if current_subject:
            await TextsDAO.update(chapter=f"{edit_subject}|address", text=video_id)
        else:
            await TextsDAO.create(chapter=f"{edit_subject}|address", text=video_id)
        text = "Выберите контент, который вы хотите изменить:"
        kb = inline_kb.edit_address_kb()
        await state.set_state(AdminFSM.home)
    else:
        current_subject = await TextsDAO.get_one_or_none(chapter=f"{edit_subject}|address")
        if current_subject:
            await message.answer_video(video=current_subject["text"])
        else:
            await message.answer("🤷 Данные отсутствуют")
        text = "Текущее видео ☝️\nОтправьте ответным сообщением видео, на которое его следует заменить:"
        chapter = "address"
        kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
        await state.set_state(AdminFSM.address_video)
    await message.answer(text, reply_markup=kb)


@router.message(AdminFSM.address_location)
async def address_location(message: Message, state: FSMContext):
    state_data = await state.get_data()
    current_subject = state_data["current_subject"]
    if message.content_type == "location":
        longitude = message.location.longitude
        latitude = message.location.latitude
        if current_subject:
            await TextsDAO.update(chapter="location|address", text=f"{longitude}|{latitude}")
        else:
            await TextsDAO.create(chapter="location|address", text=f"{longitude}|{latitude}")
        text = "Выберите контент, который вы хотите изменить:"
        kb = inline_kb.edit_address_kb()
        await state.set_state(AdminFSM.home)
    else:
        current_subject = await TextsDAO.get_one_or_none(chapter="location|address")
        if current_subject:
            await message.answer_video(video=current_subject["text"])
        else:
            await message.answer("🤷 Данные отсутствуют")
        text = "Текущая геометка ☝️\nОтправьте ответным сообщением геометку, на которую её следует " \
               "заменить.\nВажно! Геометка заменится также в сообщении за 2 часа до приёма."
        chapter = "address"
        kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
        await state.set_state(AdminFSM.address_location)
    await message.answer(text, reply_markup=kb)


@router.message(AdminFSM.address_text)
async def address_text(message: Message, state: FSMContext):
    state_data = await state.get_data()
    current_subject = state_data["current_subject"]
    if message.content_type == "text":
        if current_subject:
            await TextsDAO.update(chapter="text|address", text=message.text)
        else:
            await TextsDAO.create(chapter="text|address", text=message.text)
        text = "Выберите контент, который вы хотите изменить:"
        kb = inline_kb.edit_address_kb()
        await state.set_state(AdminFSM.home)
    else:
        current_subject = await TextsDAO.get_one_or_none(chapter="text|address")
        if current_subject:
            await message.answer(current_subject["text"])
        else:
            await message.answer("🤷 Данные отсутствуют")
        text = "Текущий текст ☝️\nОтправьте ответным сообщением новый текст, на который его следует заменить:"
        chapter = "address"
        kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
        await state.set_state(AdminFSM.address_video)
    await message.answer(text, reply_markup=kb)


##################
#  Редактура обо мне

@router.callback_query(F.data.split(":")[0] == "edit_about_me")
async def edit_about_me(callback: CallbackQuery, state: FSMContext):
    edit_subject = callback.data.split(":")[1]
    chapter = f"{edit_subject}|about_me"
    current_subject = await TextsDAO.get_one_or_none(chapter=chapter)
    if edit_subject == "video":
        if current_subject:
            await callback.message.answer_video(video=current_subject["text"])
        else:
            await callback.message.answer("🤷 Данные отсутствуют")
        text = "Текущее видео ☝️\nОтправьте ответным сообщением видео, на которое его следует заменить:"
        await state.set_state(AdminFSM.about_me_video)
    elif edit_subject == "photo":
        if current_subject:
            await callback.message.answer_photo(photo=current_subject["text"])
        else:
            await callback.message.answer("🤷 Данные отсутствуют")
        text = "Текущая картинка ☝️\nОтправьте ответным сообщением изображение, на которое её следует заменить:"
        await state.set_state(AdminFSM.about_me_photo)
    else:
        if current_subject:
            await callback.message.answer(text=current_subject["text"])
        else:
            await callback.message.answer("🤷 Данные отсутствуют")
        text = "Текущий текст ☝️\nОтправьте ответным сообщением новый текст, на который его следует заменить:"
        await state.set_state(AdminFSM.about_me_text)
    await state.update_data(current_subject=current_subject)
    chapter = "about_me"
    kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.message(AdminFSM.about_me_video)
async def about_me_video(message: Message, state: FSMContext):
    state_data = await state.get_data()
    current_subject = state_data["current_subject"]
    if message.content_type == "video":
        video_id = message.video.file_id
        if current_subject:
            await TextsDAO.update(chapter="video|about_me", text=video_id)
        else:
            await TextsDAO.create(chapter="video|about_me", text=video_id)
        text = "Выберите контент, который вы хотите изменить:"
        kb = inline_kb.edit_about_me_kb()
        await state.set_state(AdminFSM.home)
    else:
        current_subject = await TextsDAO.get_one_or_none(chapter="video|about_me")
        if current_subject:
            await message.answer_video(video=current_subject["text"])
        else:
            await message.answer("🤷 Данные отсутствуют")
        text = "Текущее видео ☝️\nОтправьте ответным сообщением видео, на которое его следует заменить:"
        chapter = "about_me"
        kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
        await state.set_state(AdminFSM.about_me_video)
    await message.answer(text, reply_markup=kb)


@router.message(AdminFSM.about_me_photo)
async def about_me_photo(message: Message, state: FSMContext):
    state_data = await state.get_data()
    current_subject = state_data["current_subject"]
    if message.content_type == "photo":
        photo_id = message.photo[-1].file_id
        if current_subject:
            await TextsDAO.update(chapter="photo|about_me", text=photo_id)
        else:
            await TextsDAO.create(chapter="photo|about_me", text=photo_id)
        text = "Выберите контент, который вы хотите изменить:"
        kb = inline_kb.edit_about_me_kb()
        await state.set_state(AdminFSM.home)
    else:
        current_subject = await TextsDAO.get_one_or_none(chapter="photo|about_me")
        if current_subject:
            await message.answer_photo(photo=current_subject["text"])
        else:
            await message.answer("🤷 Данные отсутствуют")
        text = "Текущая картинка ☝️\nОтправьте ответным сообщением изображение, на которое её следует заменить:"
        chapter = "about_me"
        kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
        await state.set_state(AdminFSM.about_me_photo)
    await message.answer(text, reply_markup=kb)


@router.message(AdminFSM.about_me_text)
async def about_me_text(message: Message, state: FSMContext):
    state_data = await state.get_data()
    current_subject = state_data["current_subject"]
    if message.content_type == "text":
        if current_subject:
            await TextsDAO.update(chapter="text|about_me", text=message.text)
        else:
            await TextsDAO.create(chapter="text|about_me", text=message.text)
        text = "Выберите контент, который вы хотите изменить:"
        kb = inline_kb.edit_about_me_kb()
        await state.set_state(AdminFSM.home)
    else:
        current_subject = await TextsDAO.get_one_or_none(chapter="text|about_me")
        if current_subject:
            await message.answer(current_subject["text"])
        else:
            await message.answer("🤷 Данные отсутствуют")
        text = "Текущий текст ☝️\nОтправьте ответным сообщением новый текст, на который его следует заменить:"
        chapter = "about_me"
        kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
        await state.set_state(AdminFSM.about_me_text)
    await message.answer(text, reply_markup=kb)


##################
#  Редактура прайс-листа

@router.callback_query(F.data.split(":")[0] == "edit_price")
async def edit_price_photo(callback: CallbackQuery, state: FSMContext):
    price_type = callback.data.split(":")[1]
    current_subject = await TextsDAO.get_one_or_none(chapter=f"{price_type}|price_list")
    if current_subject:
        await callback.message.answer_photo(photo=current_subject["text"])
    else:
        await callback.message.answer("🤷 Данные отсутствуют")
    text = "Текущая картинка ☝️\nОтправьте ответным сообщением изображение, на которое её следует заменить:"
    chapter = "price_list"
    kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
    await state.update_data(current_subject=current_subject, price_type=price_type)
    await state.set_state(AdminFSM.price_list_photo)
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.message(AdminFSM.price_list_photo)
async def edit_price_photo(message: Message, state: FSMContext):
    state_data = await state.get_data()
    price_type = state_data["price_type"]
    if message.content_type == "photo":
        photo_id = message.photo[-1].file_id
        if state_data["current_subject"]:
            await TextsDAO.update(chapter=f"{price_type}|price_list", text=photo_id)
        else:
            await TextsDAO.create(chapter=f"{price_type}|price_list", text=photo_id)
        text = "Выберите контент, который вы хотите изменить:"
        kb = inline_kb.edit_price_list_kb()
        await state.set_state(AdminFSM.home)
    else:
        current_subject = await TextsDAO.get_one_or_none(chapter=f"{price_type}|price_list")
        if current_subject:
            await message.answer_photo(photo=current_subject)
        else:
            await message.answer("🤷 Данные отсутствуют")
        text = "Текущая картинка ☝️\nОтправьте ответным сообщением изображение, на которое её следует заменить:"
        chapter = "price_list"
        kb = inline_kb.back_btn(cb_data=f"edit_info_block:{chapter}")
        await state.update_data(current_subject=current_subject, price_type=price_type)
        await state.set_state(AdminFSM.price_list_photo)
    await message.answer(text, reply_markup=kb)

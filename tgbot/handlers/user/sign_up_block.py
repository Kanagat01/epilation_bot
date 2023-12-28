import asyncio
from datetime import datetime, timedelta
from typing import Literal

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery
from aiogram.types.labeled_price import LabeledPrice

from create_bot import bot, scheduler, payments_token
from tgbot.calendar_api.calendar import create_event, delete_event_by_reg_id
from tgbot.misc.registrations import create_registration
from tgbot.misc.scheduler import HolidayScheduler, PayRegistration2HoursScheduler
from tgbot.misc.states import UserFSM
from tgbot.models.sql_connector import ClientsDAO, RegistrationsDAO, StaticsDAO, ServicesDAO, category_translation
from tgbot.keyboards.inline import UserSignUpInline
from tgbot.services.schedule_proof import date_slots_checker, time_three_slots_checker, one_slot_checker, \
    check_free_slot

router = Router()


@router.message(F.text == "Записаться")
@router.message(F.text == "Записаться с бонусом 🎁")
@router.message(F.text == "Записаться / Информация о ближайшей записи")
@router.message(Command("sign_up"))
async def sign_up(message: Message):
    await check_user(user_id=message.from_user.id)


@router.callback_query(F.data == "sign_up")
async def sign_up(callback: CallbackQuery):
    await check_user(user_id=callback.from_user.id)
    await bot.answer_callback_query(callback.id)


async def check_user(user_id: str | int):
    user_id = str(user_id)
    user = await ClientsDAO.get_one_or_none(user_id=user_id)
    if user:
        last_regs = await RegistrationsDAO.get_last_4_ordering(user_id=user_id)
        created_registration = None
        if len(last_regs) > 0:
            if last_regs[0]["status"] in ["created", "moved", "blocked", "confirmation_sent", "approved"]:
                created_registration = last_regs[0]
        if created_registration:
            await is_created_reg(user_id=user_id, user=user, reg_profile=created_registration)
        else:
            cancel_counter = 0
            for reg in last_regs:
                if reg["status"] == "cancelled":
                    cancel_counter += 1
            if cancel_counter < 3:
                finished_regs = await RegistrationsDAO.get_many(user_id=user_id, status="finished")
                if len(finished_regs) > 0:
                    await is_finished_reg(user_id=user_id, reg_type="finished_reg")
                else:
                    await no_finished_reg(user_id=user_id, greeting=True)
            else:
                text = "✍🏻Напишите мне лично, и я запишу вас на процедуры"
                kb = UserSignUpInline.msg_to_admin_kb()
                await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)
    else:
        await no_finished_reg(user_id=user_id, greeting=True)


# РАЗДЕЛ А. Есть предстоящая запись
###################################


async def is_created_reg(user_id: str | int, user: dict, reg_profile: dict):
    full_name = user["full_name"]
    reg_date = reg_profile["reg_date"].strftime("%d-%m-%Y")
    reg_time = reg_profile["reg_time_start"].strftime("%H:%M")
    total_price = reg_profile["total_price"]
    services = []
    for id in reg_profile["services"]:
        service = await ServicesDAO.get_one_or_none(id=id)
        services.append(service["title"])
    services = "\n".join(services)
    text = f"👋🏻Приветики, {full_name}! У тебя имеется запись на {reg_date} {reg_time} на следующие процедуры: {services}.\nСумма к оплате: {total_price}р.\nХорошего дня и отличного настроения!🌼"
    kb = UserSignUpInline.created_reg_kb(reg_profile["id"])
    await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "cancel_or_move_reg")
async def cancel_or_move_reg(callback: CallbackQuery):
    reg_id = callback.data.split(":")[1]
    finished_regs = await RegistrationsDAO.get_by_user_id(user_id=str(callback.from_user.id), finished=True)
    client = await ClientsDAO.get_one_or_none(user_id=str(callback.from_user.id))
    if len(finished_regs) == 0:
        text = [
            f'Приветствую, {client["full_name"]}!',
            "Получила от вас просьбу об отмене 😔 записи. Надеюсь,🤞🏻 у вас",
            "всё хорошо, просто поменялись планы. С радостью перенесу",
            "запись на ближайшую неделю с сохранением аванса💰, но при",
            "переносе больше чем один раз аванс сгорает. ☠️\n",
            "❗При отмене записи 3 раза подряд, бот заблокирует ⛔ возможность он-лайн записи.\n",
            "Но вы сможете записаться лично через меня. Давайте уважать время друг друга 🤗 и взаимодействовать эффективно.",
            "Хорошего дня и отличного настроения!💐"
        ]
    else:
        text = [
            f'Добрый день, {client["full_name"]}!',
            "Получила от вас просьбу об отмене ❌ записи, надеюсь,🤞🏻 у тебя",
            "всё хорошо, просто поменялись планы. Буду ждать от тебя новостей",
            "о новой записи или перенести ⏭ твою запись прямо сейчас?",
            "переносе больше чем один раз аванс сгорает. ☠️\n",
            "❗При отмене записи 3 раза подряд, бот заблокирует ⛔ возможность он-лайн записи.\n",
            "Но вы сможете записаться лично через меня.",
            "Хорошего дня и отличного настроения!💐"
        ]
    kb = UserSignUpInline.cancel_or_move_reg_kb(reg_id)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "cancel_reg")
async def cancel_reg(callback: CallbackQuery):
    reg_id = int(callback.data.split(":")[1])
    await RegistrationsDAO.update(reg_id=reg_id, status="cancelled")
    await delete_event_by_reg_id(reg_id)

    text = "Ваша запись успешно отменена. Хорошего дня 💐"
    await callback.message.answer(text)

    last_regs = await RegistrationsDAO.get_last_4_ordering(user_id=str(callback.from_user.id))
    cancel_counter = 0
    for reg in last_regs:
        if reg["status"] == "cancelled":
            cancel_counter += 1
    if cancel_counter >= 3:
        text = "🤷‍♀️К сожалению из-за большого количества отмен, он-лайн запись для вас больше недоступна. ✍🏻Напишите мне лично, и я запишу вас на процедуры."
        kb = UserSignUpInline.msg_to_admin_kb()
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "move_reg")
async def move_reg(callback: CallbackQuery):
    reg_id = int(callback.data.split(":")[1])
    await RegistrationsDAO.update(reg_id=reg_id, status="moved")
    reg_type = "move_reg"
    await is_finished_reg(str(callback.from_user.id), reg_type)


# РАЗДЕЛ B. Есть завершенная запись
###################################


@router.callback_query(F.data == "finished_reg")
async def finished_reg(callback: CallbackQuery):
    await is_finished_reg(callback.from_user.id, "finished_reg")


async def is_finished_reg(user_id: str | int, reg_type: str):
    user_id = str(user_id)
    reg_status = "moved" if reg_type == "move_reg" else "finished"
    regs = await RegistrationsDAO.get_last_4_ordering(user_id)
    last_reg = None
    for reg in regs:
        if reg["status"] == reg_status:
            last_reg = reg
            break

    services_text = []
    duration = 0
    price = 0
    category = None

    for service_id in last_reg["services"]:
        service = await ServicesDAO.get_one_or_none(id=service_id)
        if not category:
            category = category_translation(service["category"])
        services_text.append(service["title"])
        duration += service["duration"]
        price += service["price"]

    text = [
        "В прошлый раз Вы были на следующих процедурах",
        f'{category}: {", ".join(services_text)}',
        f"Общее примерное время выполнения процедур: {duration} минут",
        f"Актуальная стоимость услуг: {price}р.",
        "Желаете повторить запись? 😍"
    ]
    kb = UserSignUpInline.finished_reg_kb(user_id, reg_type)
    await bot.send_message(chat_id=user_id, text="\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "repeat_reg_user")
async def repeat_reg_user(callback: CallbackQuery, state: FSMContext):
    _, user_id, reg_type = callback.data.split(":")
    reg_status = "moved" if reg_type == "move_reg" else "finished"
    regs = await RegistrationsDAO.get_last_4_ordering(user_id)
    last_reg = None
    for reg in regs:
        if reg["status"] == reg_status:
            last_reg = reg
            break

    services = []
    duration = 0
    price = 0
    category = None

    for service_id in last_reg["services"]:
        service = await ServicesDAO.get_one_or_none(id=service_id)
        if not category:
            category = service["category"]
        services.append(service)
        duration += service["duration"]
        price += service["price"]

    await state.update_data({"duration": duration, "category": category, "price": price, "services": services, "reg_type": reg_type, "reg_id": last_reg["id"]})
    await select_data(callback, state)


@router.callback_query(F.data == "create_reg_user")
async def create_reg_user(callback: CallbackQuery):
    await no_finished_reg(user_id=callback.from_user.id, greeting=False)


# РАЗДЕЛ C. Нет завершенных записей
###################################


async def no_finished_reg(user_id: str | int, greeting: bool):
    text = "Я очень рада, что Вы выбрали меня! 🤗\nВаша процедура пройдет на высшем уровне 🔝, гарантирую!\nТак же на " \
           "первое посещение у вас будет 🎁бонус - 30% (на одну из зон)\nПри бронировании будет указана полная " \
           "💯стоимость, но не переживайте, на месте я все пересчитаю и ваша сумма станет на 30% меньше🌻"
    if greeting:
        await bot.send_message(chat_id=user_id, text=text)
    text = "Эпиляция для девушки или мужчины?"
    kb = UserSignUpInline.create_reg_gender_kb()
    await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "create_reg|gender")
async def create_reg_c(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    gender = callback.data.split(":")[1]
    gender_str = "Девушки" if gender == "girls" else "Мужчины"
    user = await ClientsDAO.get_one_or_none(user_id=user_id)
    if user["gender"] == "":
        await ClientsDAO.update(user_id=user_id, gender=gender)
    text = f"Выберите тип эпиляции для {gender_str}:"
    kb = UserSignUpInline.create_reg_category_kb()
    await state.update_data(gender=gender)
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data == "back_to_block_c")
async def back_to_c(callback: CallbackQuery):
    await no_finished_reg(user_id=callback.from_user.id, greeting=False)
    await bot.answer_callback_query(callback.id)


async def menu_render(
        user_id: str | int,
        gender: Literal["boys", "girls"],
        category: Literal["bio", "laser"],
        header: bool
):
    if header:
        category_str = "Биоэпиляция" if category == "bio" else "Лазер"
        text = f"{category_str}\nВыберите зоны эпиляции:"
        await bot.send_message(chat_id=user_id, text=text)
    no_photo = await StaticsDAO.get_one_or_none(title="no_photo")
    photo = await StaticsDAO.get_one_or_none(category="create_reg", title=f"{category}_{gender}")
    photo = photo["file_id"] if photo else no_photo["file_id"]
    services_list = await ServicesDAO.get_order_list(gender=gender, category=category, status="enabled")
    kb = UserSignUpInline.menu_services_kb(
        services=services_list, ok_services=[], gender=gender)
    await bot.send_photo(chat_id=user_id, photo=photo, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "create_reg|category")
async def create_reg_c(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    state_data = await state.get_data()
    gender = state_data["gender"]
    await state.update_data(ok_services=[], category=category)
    await menu_render(user_id=callback.from_user.id, gender=gender, category=category, header=True)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data.split(":")[0] == "switch_service")
async def switch_service(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split(":")[1])
    state_data = await state.get_data()
    ok_services = state_data["ok_services"]
    gender = state_data["gender"]
    category = state_data["category"]
    if service_id in ok_services:
        ok_services.remove(service_id)
    else:
        ok_services.append(service_id)
    services_list = await ServicesDAO.get_order_list(gender=gender, category=category, status="enabled")
    kb = UserSignUpInline.menu_services_kb(
        services=services_list, ok_services=ok_services, gender=gender)
    await state.update_data(ok_services=ok_services)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data == "main_menu_c_accept")
async def accept_reg(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    ok_services = state_data["ok_services"]
    gender = state_data["gender"]
    gender_str = "Девушки" if gender == "girls" else "Мужчины"
    category = state_data["category"]
    category_str = "Биоэпиляция воском" if category == "bio" else "Лазерная эпиляция"
    services = await ServicesDAO.get_order_list(gender=gender, category=category, status="enabled")
    services_text = []
    services_list = []
    price_counter, duration_counter = 0, 0
    for service in services:
        if service["id"] in ok_services:
            services_text.append(f"{service['title']} - {service['price']}р")
            services_list.append(service)
            price_counter += service["price"]
            duration_counter += service["duration"]
    duration_str = f"{duration_counter // 60}ч {duration_counter % 60}мин"
    text = [
        "Вы выбрали:",
        f"Эпиляция для {gender_str}.",
        f"Вид эпиляции: {category_str}",
        "Зоны эпиляции:",
        "\n".join(services_text),
        f"Ориентировочное суммарное время процедур - {duration_str}",
        f"Итого стоимость: {price_counter}р*",
        "* - стоимость указана, без учёта бонуса -30% на 1 зону для новых клиентов."
    ]
    kb = UserSignUpInline.create_reg_accept_kb(category=category)
    await state.update_data(duration=duration_counter, price=price_counter, services=services_list, reg_type="new_reg")
    await callback.message.answer(text="\n".join(text), reply_markup=kb)
    await bot.answer_callback_query(callback.id)


def services_text_render(services: list, category: str) -> list:
    category_str = "Биоэпиляция воском" if category == "bio" else "Лазер"
    services_text = []
    for service in services:
        services_text.append(
            f"{service['title']} - {category_str} ({service['duration']} минут)")
    return services_text


@router.callback_query(F.data == "choose_date")
async def select_data(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    duration = state_data["duration"]
    category = state_data["category"]
    price = state_data["price"]
    services = state_data["services"]
    reg_type = state_data["reg_type"]
    days_list = await date_slots_checker(0, duration)
    offset = (days_list[-1] - datetime.today()
              ).days if len(days_list) == 6 else None
    services_text = services_text_render(services=services, category=category)
    duration_str = f"{duration // 60}ч {duration % 60}мин"
    text = [
        "Выбранные процедуры:",
        *services_text,
        f"Общее примерное время процедур: {duration_str}",
        f"Стоимость: {price}р.",
        "Выберите желаемую дату для записи📝:"
    ]
    back_data = "main_menu_c_accept" if reg_type == "new_reg" else "finished_reg"
    kb = UserSignUpInline.choose_date_kb(
        date_list=days_list, back_data=back_data, offset=offset)
    await callback.message.answer("\n".join(text), reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data.split(":")[0] == "date_offset")
async def date_circle(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    duration = state_data["duration"]
    offset = int(callback.data.split(":")[1])
    days_list = await date_slots_checker(offset, duration)
    offset = (days_list[-1] - datetime.today()
              ).days if len(days_list) == 6 else 0
    kb = UserSignUpInline.choose_date_kb(
        date_list=days_list, back_data="main_menu_c_accept", offset=offset)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data.split(":")[0] == "select_date")
async def select_time(callback: CallbackQuery, state: FSMContext):
    date = datetime.strptime(callback.data.split(":")[1], "%d.%m.%Y")
    state_data = await state.get_data()
    duration = state_data["duration"]
    category = state_data["category"]
    price = state_data["price"]
    services = state_data["services"]
    slots_list = await time_three_slots_checker(date=date, duration=duration)
    services_text = services_text_render(services=services, category=category)
    duration_str = f"{duration // 60}ч {duration % 60}мин"
    text = [
        "Выбранные вами процедуры:",
        *services_text,
        f"Общее примерное время процедур: {duration_str}",
        f"Стоимость: {price}р.",
        f"Выбранная дата: {callback.data.split(':')[1]}\n",
        "Выберите удобное для вас время 📝",
        "✅Это можно сделать двумя способами:",
        "1) Выберите доступный интервал (утро, день, вечер), и бот назначит время автоматически в рамках интервала с "
        "учетом выбранных вами услуг 😊",
        "2) Напишите желаемое точное время в формате 11:00, и бот проверит наличие этого времени."
    ]
    kb = UserSignUpInline.choose_time_kb(slots=slots_list)
    await state.update_data(reg_date=date)
    await state.set_state(UserFSM.reg_time)
    await callback.message.answer("\n".join(text), reply_markup=kb)
    await bot.answer_callback_query(callback.id)


async def finish_registration(user_id: str | int, state: FSMContext):
    state_data = await state.get_data()
    reg_date = state_data["reg_date"]
    reg_time = state_data["reg_time"]
    duration = state_data["duration"]
    reg_type = state_data["reg_type"]
    services = state_data["services"]
    category = state_data["category"]
    price = state_data["price"]
    duration_str = f"{duration // 60}ч {duration % 60}мин"
    services_text = services_text_render(services=services, category=category)
    if reg_type in ["new_reg", "finished_reg"]:
        text = [
            "Выбранные процедуры:",
            *services_text,
            f"Общее примерное время процедур: {duration_str}",
            f"Стоимость: {price}р.",
            f"Выбранная дата: {reg_date.strftime('%d.%m.%Y')}\n",
            f"Выбранное время: {reg_time.strftime('%H.%M')}\n",
        ]
        text = "\n".join(text)
        kb = UserSignUpInline.finish_reg_accept_kb(date=reg_date)
    else:
        reg_id = state_data["reg_id"]
        reg_time_finish = (datetime.combine(
            reg_date, reg_time) + timedelta(minutes=duration)).time()
        client = await ClientsDAO.get_one_or_none(user_id=str(user_id))

        await delete_event_by_reg_id(reg_id=reg_id)
        await RegistrationsDAO.update(reg_id=reg_id, reg_date=reg_date, reg_time_start=reg_time, reg_time_finish=reg_time_finish)
        await create_event(client["full_name"], reg_date, reg_time, reg_time_finish)

        text = f"Ваша запись успешно перенесена на {reg_date.strftime('%d.%m.%Y')} {reg_time.strftime('%H.%M')}." \
               f"\nХорошего дня и отличного настроения 🌻"
        kb = None
    await bot.send_message(chat_id=user_id, reply_markup=kb, text=text)


@router.message(F.text, UserFSM.reg_time)
async def select_time(message: Message, state: FSMContext):
    try:
        dtime = datetime.strptime(
            message.text, "%H:%M").time()
        await state.update_data(reg_time=dtime)
    except ValueError:
        await message.answer("Неверный формат. Напишите время в формате 11:00")
        return
    state_data = await state.get_data()
    date = state_data["reg_date"]
    duration = state_data["duration"]
    free_slot = await check_free_slot(reg_date=date, reg_time=dtime, duration=duration)
    if free_slot:
        await finish_registration(user_id=message.from_user.id, state=state)
    else:
        text = "Введенное время недоступно для записи. Введите пожалуйста другое время или выберите один из " \
               "предложенных интервалов и бот поможет вам подобрать время. Если у вас возникли трудности напишите " \
               "Оксане в личку."
        await message.answer(text)


@router.callback_query(F.data.split(":")[0] == "select_time")
async def select_time(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    date = state_data["reg_date"]
    duration = state_data["duration"]
    slot = callback.data.split(":")[1]
    slot_start_time = await one_slot_checker(date=date, day_part=slot, duration=duration)
    if slot_start_time:
        await state.update_data(reg_time=slot_start_time)
        await finish_registration(user_id=callback.from_user.id, state=state)
    else:
        text = "Введенное время недоступно для записи. Введите пожалуйста другое время или выберите один из " \
               "предложенных интервалов и бот поможет вам подобрать время. Если у вас возникли трудности напишите " \
               "Оксане в личку."
        await callback.message.answer(text)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data == "finish_reg")
async def finish_reg(callback: CallbackQuery, state: FSMContext):
    finished_regs = await RegistrationsDAO.get_by_user_id(user_id=str(callback.from_user.id), finished=True)
    state_data = await state.get_data()
    reg_date = state_data["reg_date"]
    reg_time = state_data["reg_time"]
    services = state_data["services"]
    duration = state_data["duration"]
    price = state_data["price"]
    category = state_data["category"]
    user_id = str(callback.from_user.id)
    user = await ClientsDAO.get_one_or_none(user_id=user_id)
    if user:
        full_name = user["full_name"]
        phone = user["phone"]
    else:
        return
    if len(finished_regs) == 0:
        free_slot = await check_free_slot(reg_date=reg_date, reg_time=reg_time, duration=duration)
        if free_slot:
            duration_str = f"{duration // 60}ч {duration % 60}мин"
            services_text = services_text_render(
                services=services, category=category)
            text = [
                "Время за вами забронировано!\n",
                "Выбранные процедуры:",
                *services_text,
                f"Общее примерное время процедур: {duration_str}",
                f"Стоимость: {price}р.",
                f"Выбранная дата: {reg_date.strftime('%d.%m.%Y')}",
                f"Выбранное время: {reg_time.strftime('%H.%M')}\n",
            ]
            text = "\n".join(text)
            await create_registration(
                data=state_data,
                phone=phone,
                user_id=user_id,
                client_service_duration=user["service_duration"]
            )
            chat_id = callback.from_user.id
            await bot.send_message(chat_id=chat_id, text=text)

            if full_name == "":
                await state.set_state(UserFSM.full_name_sign)
                name_text = "Осталось ввести ваши ФИ, для завершения записи.\n\nНапишите, пожалуйста, свою Фамилию " \
                            "и Имя.\nФормат: Иванова Светлана"
                await bot.send_message(chat_id=chat_id, text=name_text)
            else:
                await check_birthday(user_id=user_id, state=state)
        else:
            text = "К сожалению выбранное вами время уже недоступно😔\nВыберите🙏 другое время"
            await callback.message.answer(text)
    else:
        service_text = []
        for service in services:
            service_text.append(service["title"])
        service_text = ", ".join(service_text)
        text = [
            f"👋🏻Приветики, {full_name}! Записала тебя на {reg_date.strftime('%d.%m.%Y')} {reg_time.strftime('%H.%M')} ",
            f"на следующие процедуры: {service_text}.",
            f"Сумма к оплате: {price} ₽.",
            "Хорошего дня и отличного настроения!🌼"
        ]
        text = "\n".join(text)
        await create_registration(
            data=state_data,
            phone=phone,
            user_id=user_id,
            client_service_duration=user["service_duration"]
        )
        await callback.message.answer(text)
        await bot.answer_callback_query(callback.id)


@router.message(F.text, UserFSM.full_name_sign)
async def finish_reg(message: Message, state: FSMContext):
    full_name = message.text.strip()
    await ClientsDAO.update(user_id=str(message.from_user.id), full_name=full_name)
    await state.set_state(UserFSM.home)
    await check_birthday(user_id=message.from_user.id, state=state)


async def check_birthday(user_id: str | int, state: FSMContext):
    user = await ClientsDAO.get_one_or_none(user_id=str(user_id))
    birthday = user["birthday"]
    if birthday:
        birthday_str = birthday.strftime("%d.%m.%Y")
        if birthday_str != "01.01.1900":
            job_id = "at_birthday" + birthday_str + "_holiday"
            job = scheduler.get_job(job_id)
            if not job:
                week_before = birthday - timedelta(days=7)
                await HolidayScheduler.create("1week_before_birthday", week_before)
                await HolidayScheduler.create("at_birthday", birthday)
        await resource_menu(user_id=user_id)
    else:
        text = "Введите вашу дату рождения. Эти данные позволяют мне радовать вас поздравлениями 💌 и " \
               "бонусами 🎁\nФормат: 01.01.1980"
        kb = UserSignUpInline.no_birthday_kb()
        await state.set_state(UserFSM.birthday_sign)
        await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)


@router.message(F.text, UserFSM.birthday_sign)
async def finish_reg(message: Message, state: FSMContext):
    try:
        birthday = datetime.strptime(message.text, "%d.%m.%Y")
        job_id = "at_birthday" + birthday.strftime("%d.%m.%Y") + "_holiday"
        job = scheduler.get_job(job_id)
        if not job:
            week_before = birthday - timedelta(days=7)
            await HolidayScheduler.create("1week_before_birthday", week_before)
            await HolidayScheduler.create("at_birthday", birthday)

        await ClientsDAO.update(user_id=message.from_user.id, birthday=birthday)
        await state.set_state(UserFSM.home)
        await resource_menu(user_id=message.from_user.id)
    except ValueError:
        text = "К сожалению, не удалось введённое сообщение определить как дату рождения. Пожалуйста, напишите " \
               "дату рождения в формате: 07.02.1990"
        kb = UserSignUpInline.no_birthday_kb()
        await message.answer(text=text, reply_markup=kb)


@router.callback_query(F.data == "no_birthday")
async def finish_reg(callback: CallbackQuery, state: FSMContext):
    birthday = datetime.strptime("01.01.1900", "%d.%m.%Y")
    await ClientsDAO.update(user_id=callback.from_user.id, birthday=birthday)
    await state.set_state(UserFSM.home)
    await resource_menu(user_id=callback.from_user.id)
    await bot.answer_callback_query(callback.id)


async def resource_menu(user_id: int | str):
    text = "Понимаю, вы немного устали  🙁 Это последний вопросик  🙏  Откуда вы узнали обо мне ?"
    kb = UserSignUpInline.resource_menu_kb()
    await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "resource")
async def finish_reg(callback: CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    resource = callback.data.split(":")[1]
    await ClientsDAO.update(user_id=user_id, resource=resource)
    sticker_id = "CAACAgIAAxkBAAIju2S3AtDthsNHP4KChB9UNAgmk4VEAAKOFQACJU3BSY8WTX7r0TbzLwQ"
    await callback.message.answer_sticker(sticker=sticker_id)
    user = await ClientsDAO.get_one_or_none(user_id=user_id)
    state_data = await state.get_data()
    if user["entry_point"] == "office":
        reg_date = state_data["reg_date"]
        reg_time = state_data["reg_time"]
        services = state_data["services"]
        service_text = []
        for service in services:
            service_text.append(service["title"])
        service_text = ", ".join(service_text)
        text = f"Ехуууу!! 🎉🎉🎉  Все данные заполнены.\n\n\nЗаписала тебя на " \
               f"{reg_date.strftime('%d.%m.%Y')} {reg_time.strftime('%H.%M')} на следующие процедуры: " \
               f"{service_text}.\nСумма к оплате: {user['price']} ₽.\nХорошего дня и отличного настроения!🌼"
        kb = None
    else:
        text = "Ехуууу!! 🎉🎉🎉  Все данные заполнены. Запись сформирована. После внесения вам аванса придёт " \
               "сообщение 💚"
        await callback.message.answer(text)
        await asyncio.sleep(1)
        text = "Так как мы еще с вами не знакомы 🤷 ‍♀️\n\nВо избежание новых недобросовестных клиентов, " \
               "которые занимают время и не приходят, я вынуждена попросить у вас внести аванс в размере 500р. 🍓\nОн " \
               "позволит мне быть уверенной в том, что вы точно придете  😉\n\nАванс будет учтен при оплате " \
               "процедуры. Чек о его внесение придет сразу после оплаты. Благодарю за понимание 💚"
        await callback.message.answer(text)
        last_regs = await RegistrationsDAO.get_last_4_ordering(user_id=str(callback.from_user.id))
        reg_id = last_regs[0]["id"]
        await RegistrationsDAO.update(reg_id=reg_id, advance="processing")
        await PayRegistration2HoursScheduler.create(callback.from_user.id, reg_id)
        text = 'Нажмите "Оплатить 500р" и вас перенаправит на платёжную форму для оплаты. Она безопасно!'
        kb = UserSignUpInline.pay_advance_kb(reg_id=reg_id)
        await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "pay_advance")
async def pay_advance(callback: CallbackQuery, state: FSMContext):
    await state.update_data({"reg_id": callback.data.split(":")[1]})
    price = LabeledPrice(label="Аванс", amount=500*100)
    await bot.send_invoice(callback.message.chat.id,
                           title="Аванс",
                           description="Оплата аванса 500р новым клиентам",
                           provider_token=payments_token,
                           currency="rub",
                           is_flexible=False,
                           prices=[price],
                           payload="advance-invoice-payload")


@router.pre_checkout_query()
async def pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext):
    state_data = await state.get_data()
    reg_id = state_data["reg_id"]
    reg = await RegistrationsDAO.get_one_or_none(id=reg_id)
    client = await ClientsDAO.get_one_or_none(user_id=reg["user_id"])
    await delete_event_by_reg_id(reg_id=reg_id)
    await RegistrationsDAO.update(reg_id=reg_id, advance="finished")
    await create_event(client["full_name"], reg["reg_date"], reg["reg_time_start"], reg["reg_time_finish"])

    await bot.send_message(message.chat.id,
                           f"Платеж на сумму {message.successful_payment.total_amount // 100} {message.successful_payment.currency} прошел успешно!!!")

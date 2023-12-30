import os
import csv
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from create_bot import bot, dp
from tgbot.calendar_api.calendar import check_interval_for_events, get_events
from tgbot.filters.admin import AdminFilter
from tgbot.misc.registrations import create_registration
from tgbot.models.sql_connector import RegistrationsDAO, ClientsDAO, ServicesDAO, TextsDAO, category_translation, gender_translation, status_translation
from tgbot.keyboards.inline import AdminInlineKeyboard as inline_kb
from tgbot.misc.states import AdminFSM

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(F.text == "Клиенты")
async def clients(message: Message, state: FSMContext):
    text = [
        "Введите ФИО или номер телефона (формат +79871234567)",
        'клиента. Или нажмите кнопку "Все клиенты"'
    ]
    kb = inline_kb.all_clients_btn_kb()
    await state.set_state(AdminFSM.find_client)
    await message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "clients")
async def clients(callback: CallbackQuery, state: FSMContext):
    text = [
        "Введите ФИО или номер телефона (формат +79871234567)",
        'клиента. Или нажмите кнопку "Все клиенты"'
    ]
    kb = inline_kb.all_clients_btn_kb()
    await state.set_state(AdminFSM.find_client)
    await callback.message.answer("\n".join(text), reply_markup=kb)


async def clients_text_and_kb(page=0):
    clients = await ClientsDAO.get_many()
    start_idx = page * 10
    end_idx = start_idx + 10 if start_idx + \
        10 <= len(clients) else len(clients)
    clients_text = []
    for client in clients[start_idx:end_idx]:
        client_registrations = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], finished=True, is_sorted=True)

        id = client["id"]
        full_name = client["full_name"]
        username = client["username"]
        phone = client["phone"]

        client_info = [
            f"{id}. {full_name} {'🆕 ' if len(client_registrations) == 0 else ''}- {username} +{phone} - {len(client_registrations)} приёмов."
        ]

        if len(client_registrations) > 0:
            reg_date = client_registrations[0]["reg_date"]
            reg_time_start = client_registrations[0]["reg_time_start"]
            service_id = client_registrations[0]["services"][0]
            service = await ServicesDAO.get_one_or_none(id=service_id)
            category = category_translation(service["category"])
            duration = service["duration"]

            client_info.append(
                f"Последняя запись - {category} на {reg_date} {reg_time_start}.")
            client_info.append(
                f"Время процедур - {duration} минут (авто).")

        client_info = "\n".join(client_info) + "\n"
        clients_text.append(client_info)

    text = [
        "Введите номер клиента для подробностей.",
        "Клиенты:",
        "\n".join(clients_text)
    ]
    prev_ten = page > 0
    next_ten = end_idx < len(clients)
    kb = inline_kb.clients_kb(page, prev_ten=prev_ten, next_ten=next_ten)
    return text, kb


@router.callback_query(F.data == "all_clients")
@router.callback_query(F.data.split(":")[0] == "prev")
@router.callback_query(F.data.split(":")[0] == "next")
async def all_clients(callback: CallbackQuery, state: FSMContext):
    callback_data_lst = callback.data.split(":")
    if len(callback_data_lst) == 2:
        await callback.message.delete()

        page = int(callback_data_lst[1])
        text, kb = await clients_text_and_kb(page=page)
    else:
        text, kb = await clients_text_and_kb()

    await state.set_state(AdminFSM.find_client)
    await callback.message.answer("\n".join(text), reply_markup=kb)


async def export_to_csv(chat_id: int, data: list):
    file_name = f"{os.getcwd()}/tgbot/static/output.csv"

    with open(file_name, 'w', newline='', encoding='cp1251') as file:
        writer = csv.writer(file)
        writer.writerows(data)

    file = FSInputFile(path=file_name)
    await bot.send_document(chat_id, document=file)

    os.remove(file_name)


@router.callback_query(F.data == "export_to_csv_min")
async def export_to_csv_min(callback: CallbackQuery):
    data = [
        ['id', 'Полное имя', 'Username', "Номер телефона",
            "Количество приёмов", "Последняя запись", "Время процедур (авто)"]
    ]
    clients = await ClientsDAO.get_many()
    for client in clients:
        row = []
        id = client["id"]
        full_name = client["full_name"]
        username = client["username"]
        phone = client["phone"]

        client_registrations = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], finished=True, is_sorted=True)

        row.extend([id, full_name, username, phone, len(client_registrations)])

        if len(client_registrations) > 0:
            first_reg = client_registrations[0]
            reg_date = first_reg["reg_date"]
            reg_time_start = first_reg["reg_time_start"]
            service_id = first_reg["services"][0]
            service = await ServicesDAO.get_one_or_none(id=service_id)
            category = category_translation(service["category"])
            duration = service["duration"]
            row.extend(
                [f"{category} на {reg_date} {reg_time_start}", duration])

        data.append(row)
    await export_to_csv(callback.from_user.id, data)


@router.callback_query(F.data == "export_to_csv_max")
async def export_to_csv_max(callback: CallbackQuery):
    data = []
    clients = await ClientsDAO.get_many()
    for client in clients:
        user_id = client["user_id"]
        full_name = client["full_name"]

        data.append([
            'ID клиента', 'Полное имя', 'Username', 'Номер телефона', 'Пол',
            'Дата рождения', 'Примечание', 'Источник', 'Продолжительность услуги'
        ])
        row = [
            client["id"],
            full_name,
            client["username"],
            client["phone"],
            gender_translation(client["gender"]),
            client["birthday"],
            client["note"],
            client["resource"],
            client["service_duration"]
        ]
        data.append(row)

        data.extend([[
            f"Записи клиента {full_name if full_name != '' else client['username']}:"
        ], [
            'ID записи', 'Телефон', 'Дата записи', 'Время начала', 'Время окончания',
            'Список услуг', 'Общая стоимость', 'Статус', 'Аванс'
        ]])

        client_registrations = await RegistrationsDAO.get_by_user_id(user_id=user_id)
        if len(client_registrations) != 0:
            for reg in client_registrations:
                reg_services = []
                for service_id in reg['services']:
                    service = await ServicesDAO.get_one_or_none(id=service_id)
                    reg_services.append(service["title"])

                registration_data = [
                    reg['id'],
                    reg['phone'],
                    reg['reg_date'],
                    reg['reg_time_start'],
                    reg['reg_time_finish'],
                    ", ".join(reg_services),
                    reg['total_price'],
                    status_translation(reg['status']),
                    reg['advance']
                ]
                data.append(registration_data)
        else:
            data.append(["У этого клиента пока нет записей"])
    await export_to_csv(callback.from_user.id, data)


async def client_text_and_kb(client, page=0):
    registrations = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], is_sorted=True)
    text = [
        f"Клиент № {client['id']}:",
        f"Фамилия Имя: {client['full_name']}",
        f"Пол: {gender_translation(client['gender'])}",
        f"Телеграм: {client['username']}",
        f"Телефон: +{client['phone']}",
        f"Дата рождения: {client['birthday']}",
        f"Количество приёмов: {len(registrations)}"
    ]
    end_idx = None
    if len(registrations) > 0:
        last_reg = registrations[0]
        last_reg_service = await ServicesDAO.get_one_or_none(id=last_reg["services"][0])
        category = category_translation(last_reg_service['category'])

        duration_auto = 0
        for service_id in last_reg["services"]:
            service = await ServicesDAO.get_one_or_none(id=service_id)
            duration_auto += service["duration"]

        last_regs = registrations[0:4]
        cancel_counter = 0
        for reg in last_regs:
            if reg["status"] == "cancelled":
                cancel_counter += 1

        regs_text = [
            "Последние записи (отображать по 10 последних записей, т.е. обратная сортировка):"]

        start_idx = page * 10
        end_idx = start_idx + 10
        for reg in registrations[start_idx:end_idx]:
            service = await ServicesDAO.get_one_or_none(id=reg["services"][0])
            reg_category = category_translation(service["category"])
            reg_status = status_translation(reg["status"])
            regs_text.append(
                f"{reg['id']}. {reg_category} на {reg['reg_date']} {reg['reg_time_start']} / {reg_status}")

        text.extend([
            f"Последняя запись: {category}: {last_reg_service['title']}.",
            f"Время процедур - {duration_auto} минут (авто)",
            f"Время процедур - {client['service_duration']} минут (вручную)",
            f"Комментарий мастера: {client['note']}",
            f"Количество отмен онлайн-записи подряд: {cancel_counter}\n",
            "\n".join(regs_text)
        ])
    prev = page > 0
    next = end_idx < len(registrations) if end_idx else False
    kb = inline_kb.client_kb(page=page, have_regs=len(registrations) > 0, prev=prev,
                             next=next)
    return text, kb


@router.message(AdminFSM.find_client)
async def find_client(message: Message, state: FSMContext):
    if message.text.startswith("+"):
        phone = message.text.replace("+", "")
        client = await ClientsDAO.get_one_or_none(phone=phone)
        if client:
            await state.set_data({"client": client})
            text, kb = await client_text_and_kb(client)
            await message.answer("\n".join(text), reply_markup=kb)
        else:
            await message.answer("Клиента с таким номером телефона не найдено")

    else:
        client = await ClientsDAO.get_one_or_none(full_name=message.text)
        if client:
            await state.set_data({"client": client})
            text, kb = await client_text_and_kb(client)
            await message.answer("\n".join(text), reply_markup=kb)
        else:
            await message.answer("Клиентов с таким ФИО не найдено")


@router.callback_query(F.data == "back_to_client")
async def back_to_client(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    text, kb = await client_text_and_kb(client)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "prev_regs")
@router.callback_query(F.data.split(":")[0] == "next_regs")
async def client_regs_pagination(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    page = int(callback.data.split(":")[1])
    state_data = await state.get_data()
    client = state_data["client"]

    text, kb = await client_text_and_kb(client, page=page)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "export_client_to_csv")
async def export_client_to_csv(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    data = [[
            'ID', 'user_id', 'Полное имя', 'Username', 'Номер телефона', 'Пол',
            'Дата рождения', 'Примечание', 'Источник', 'Продолжительность услуги'
            ],
            [
                client["id"], client["user_id"], client["full_name"], client["username"], client["phone"], gender_translation(
                    client["gender"]),
                client["birthday"], client["note"], client["resource"], client["service_duration"]
    ],
        ["Записи клиента"]]
    client_regs = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"])
    if len(client_regs) > 0:
        data.append(["id", "Дата записи", "Время начала", "Время окончания",
                    "Список услуг", "Общая Сумма", "Статус", "Источник", "Аванс"])
        for reg in client_regs:
            reg_services = []
            for service_id in reg['services']:
                service = await ServicesDAO.get_one_or_none(id=service_id)
                reg_services.append(service["title"])

            registration_data = [
                reg['id'],
                reg['phone'],
                reg['reg_date'],
                reg['reg_time_start'],
                reg['reg_time_finish'],
                ", ".join(reg_services),
                reg['total_price'],
                status_translation(reg['status']),
                reg['resource'],
                reg['advance']
            ]
            data.append(registration_data)
    else:
        data.append(["Записей нет"])

    await export_to_csv(callback.from_user.id, data)


async def edit_client_text_and_kb(client):
    gender = gender_translation(client['gender'])
    regs = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], is_sorted=True)

    text = [
        f"Клиент № {client['id']}:",
        f"Фамилия Имя: {client['full_name']}",
        f"Пол: {gender}",
        f"Телеграм: {client['username']}",
        f"Телефон: +{client['phone']}",
        f"Дата рождения: {client['birthday']}",
        f"Количество приёмов: {len(regs)}",
    ]

    if len(regs) != 0:
        category = None
        services_text = []
        duration = 0
        for service_id in regs[0]["services"]:
            service = await ServicesDAO.get_one_or_none(id=service_id)
            duration += service["duration"]
            if not category:
                category = category_translation(service["category"])
            services_text.append(service["title"])

        text.extend([
            f"Последняя запись: {category}: {', '.join(services_text)}.",
            f"Время процедур - {duration} минут (авто)",
            f"Время процедур - {client['service_duration']} минут (вручную)",
            f"Комментарий мастера: {client['note']}"
        ])
    kb = inline_kb.edit_client_kb(user_id=client["user_id"])
    return text, kb


@router.callback_query(F.data == "edit_client")
async def edit_client(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    text, kb = await edit_client_text_and_kb(client)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "change_full_name")
async def change_full_name(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    text = f'Введите фамилию и имя для клиента "{client["full_name"]}":'
    await state.set_state(AdminFSM.client_full_name)
    await callback.message.answer(text)


@router.message(AdminFSM.client_full_name)
async def set_client_full_name(message: Message, state: FSMContext):
    state_data = await state.get_data()
    user_id = state_data["client"]["user_id"]
    await ClientsDAO.update(user_id=user_id, full_name=message.text)
    await message.answer('Поле "Фамилия и Имя" изменено')

    client = await ClientsDAO.get_one_or_none(user_id=user_id)
    text, kb = await edit_client_text_and_kb(client)
    await message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "change_gender")
async def change_gender(callback: CallbackQuery):
    user_id = callback.data.split(":")[1]
    client = await ClientsDAO.get_one_or_none(user_id=user_id)
    id, full_name = client["id"], client["full_name"]
    text = f"Выберите пол для клиента #{id}: {full_name}:"
    kb = inline_kb.set_client_gender_kb(user_id)
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "set_client_gender")
async def set_client_gender(callback: CallbackQuery, state: FSMContext):
    _, user_id, gender = callback.data.split(":")
    await ClientsDAO.update(user_id=user_id, gender=gender)
    client = await ClientsDAO.get_one_or_none(user_id=user_id)
    text, kb = await edit_client_text_and_kb(client)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "change_service_duration")
async def change_service_duration(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    text = f'Введите время процедуры для клиента "{client["full_name"]}" для повторных записей. Формат - целое число в минутах:'
    await state.set_state(AdminFSM.client_service_duration)
    await callback.message.answer(text)


@router.message(AdminFSM.client_service_duration)
async def set_client_service_duration(message: Message, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    if message.text.isdigit():
        user_id = client["user_id"]
        await ClientsDAO.update(user_id=user_id, service_duration=int(message.text))
        await message.answer("Время процедур изменено")

        client = await ClientsDAO.get_one_or_none(user_id=user_id)
        text, kb = await edit_client_text_and_kb(client)
        await message.answer("\n".join(text), reply_markup=kb)

    else:
        text = f'Это не число. Введите время процедуры для клиента "{client["full_name"]}" для повторных записей. Формат - целое число в минутах:'
        await message.answer(text)


@router.callback_query(F.data.split(":")[0] == "change_phone")
async def change_phone(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    text = f'Введите номер телефона для клиента "{client["full_name"]}" в формате +79506238760'
    await state.set_state(AdminFSM.client_phone)
    await callback.message.answer(text)


@router.message(AdminFSM.client_phone)
async def set_client_phone(message: Message, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]

    valid_phone = message.text.startswith("+")
    phone = message.text.replace("+", "")
    valid_phone = valid_phone and phone.isdigit() and len(phone) == 11
    if valid_phone:
        client_with_this_phone = await ClientsDAO.get_one_or_none(phone=phone)
        if client_with_this_phone:
            text = "Такой телефон уже у другого клиента. Чтобы добавить телефон клиенту, нужно сначала удалить его из карточки другого клиента"
            await message.answer(text)
        else:
            await ClientsDAO.update(user_id=client["user_id"], phone=phone)
            regs = await RegistrationsDAO.get_many(user_id=client["user_id"])
            for reg in regs:
                await RegistrationsDAO.update(reg_id=reg["id"], phone=phone)

            text = "Телефон изменён"
            await message.answer(text)

            client = await ClientsDAO.get_one_or_none(user_id=client["user_id"])
            text, kb = await edit_client_text_and_kb(client)
            await message.answer("\n".join(text), reply_markup=kb)
    else:
        text = f'Неправильный формат ввода. Введите номер телефона для клиента "{client["full_name"]}" в формате +79506238760'
        await message.answer(text)


@router.callback_query(F.data.split(":")[0] == "change_birthday")
async def change_birthday(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    text = f'Введите дату рождения клиента "{client["full_name"]}". Формат: 11.05.1995'
    await state.set_state(AdminFSM.client_birthday)
    await callback.message.answer(text)


@router.message(AdminFSM.client_birthday)
async def set_client_birthday(message: Message, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    user_id = client["user_id"]
    try:
        birthday = datetime.strptime(message.text, "%d.%m.%Y")
        await ClientsDAO.update(user_id=user_id, birthday=birthday)
        await message.answer("Дата рождения изменена")

        client = await ClientsDAO.get_one_or_none(user_id=user_id)
        text, kb = await edit_client_text_and_kb(client)
        await message.answer("\n".join(text), reply_markup=kb)

    except ValueError:
        text = f'Неправильный формат ввода. Введите дату рождения клиента "{client["full_name"]}". Формат: 11.05.1995'
        await message.answer(text)


@router.callback_query(F.data.split(":")[0] == "change_note")
async def change_note(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    text = f'Введите ваш комментарий для клиента "{client["full_name"]}"'
    await state.set_state(AdminFSM.client_note)
    await callback.message.answer(text)


@router.message(AdminFSM.client_note)
async def set_client_note(message: Message, state: FSMContext):
    state_data = await state.get_data()
    user_id = state_data["client"]["user_id"]
    await ClientsDAO.update(user_id=user_id, note=message.text)
    await message.answer("Комментарий изменен")

    client = await ClientsDAO.get_one_or_none(user_id=user_id)
    text, kb = await edit_client_text_and_kb(client)
    await message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "add_reg")
async def add_reg(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    client_regs = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], finished=True, is_sorted=True)
    if len(client_regs) > 0:
        last_reg = client_regs[0]
        duration_auto = 0
        service = await ServicesDAO.get_one_or_none(id=last_reg["services"][0])
        reg_category = category_translation(service["category"])

        service_text = []
        selected_services = []
        for service_id in last_reg["services"]:
            service = await ServicesDAO.get_one_or_none(id=service_id)
            selected_services.append(service)
            duration_auto += service["duration"]
            service_text.append(service["title"])
        text = [
            f"Клиент №{client['id']} {client['full_name']}.",
            "Последняя запись:",
            f"{reg_category}: {', '.join(service_text)}.",
            f"Время процедур (авто): {duration_auto} минут",
            f"Время процедур (вручную): {client['service_duration']} минут",
            "Повторить запись?"
        ]
        await state.update_data({"callback_data": callback.data, "selected_services": selected_services, "category": reg_category})
        kb = inline_kb.add_reg_1_kb()
        await callback.message.answer("\n".join(text), reply_markup=kb)
    else:
        text, kb = await choose_gender_text_and_kb()
        await callback.message.answer("\n".join(text), reply_markup=kb)


async def choose_gender_text_and_kb():
    text = ["Клиент хочет записать девушку или мужчину?"]
    kb = inline_kb.choose_gender_kb()
    return text, kb


@router.callback_query(F.data == "create_reg")
async def choose_gender(callback: CallbackQuery):
    text, kb = await choose_gender_text_and_kb()
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "reg_gender")
async def choose_epilation_type(callback: CallbackQuery):
    gender = callback.data.split(":")[1]
    text = f"Выберите тип эпиляции для {gender_translation(gender)}"
    kb = inline_kb.choose_epilation_type_kb(gender)
    await callback.message.answer(text, reply_markup=kb)


async def choose_services_text_and_kb(services: list, category: str, gender: str, selected_services=[]):
    kb = inline_kb.choose_services(services, selected_services, gender)
    text = [
        f"Выбранный вид эпиляции: {category_translation(category)}",
        "Выберите зоны эпиляции:"
    ]
    return text, kb


@router.callback_query(F.data.split(":")[0] == "epilation_type")
async def choose_services(callback: CallbackQuery, state: FSMContext):
    _, category, gender = callback.data.split(":")
    services = await ServicesDAO.get_many(category=category, gender="boys" if gender == "male" else "girls")
    await state.update_data({"category": category, "gender": gender, "services": services, "selected_services": []})
    text, kb = await choose_services_text_and_kb(services, category, gender)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "select_service")
async def select_service(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    category = state_data["category"]
    gender = state_data["gender"]
    services = state_data["services"]
    selected_services = state_data["selected_services"] if "selected_services" in state_data else [
    ]

    service = services[int(callback.data.split(":")[1])]

    if service not in selected_services:
        selected_services.append(service)
    else:
        selected_services.remove(service)
    await state.update_data({"selected_services": selected_services, "callback_data": callback.data})

    kb = inline_kb.choose_services(services, selected_services, gender)
    await callback.message.edit_reply_markup(reply_markup=kb)


@router.callback_query(F.data == "repeat_reg")
@router.callback_query(F.data == "set_reg_date")
async def set_reg_date(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    category = state_data["category"]
    selected_services = state_data["selected_services"]
    services_titles = ", ".join([service['title']
                                for service in selected_services])
    duration = sum([service['duration'] for service in selected_services])
    await state.update_data({"services_titles": services_titles, "duration": duration})

    text = [
        f"Клиент №{client['id']} {client['full_name']}.\n",
        f"{category}: {services_titles}.",
        f"Время процедур (авто): {duration} минут",
        f"Время процедур (вручную): {client['service_duration']} минут\n",
        "Напишите дату для записи клиента в формате 05.02.2022"
    ]
    cb_data = state_data["callback_data"]
    await state.set_state(AdminFSM.clients_reg_date)
    kb = inline_kb.back_btn(cb_data=cb_data)
    await callback.message.answer("\n".join(text), reply_markup=kb)


async def set_reg_date_text_and_kb(state: FSMContext, date_object):
    state_data = await state.get_data()
    client = state_data["client"]
    category = category_translation(state_data["category"])
    events = await get_events(schedule_date=date_object)
    regs = []
    for event in events:
        date_string = event["start"]["dateTime"].split('T')[0]
        date_object = datetime.strptime(date_string, "%Y-%m-%d")
        start_time = event["start"]["dateTime"].split('T')[1][:5]
        end_time = event["end"]["dateTime"].split('T')[1][:5]

        time_start = datetime.strptime(start_time, "%H:%M").time()
        time_finish = datetime.strptime(end_time, "%H:%M").time()
        reg = await RegistrationsDAO.get_one_or_none(reg_date=date_object, reg_time_start=time_start, reg_time_finish=time_finish)
        if reg:
            regs.append(reg)

    regs_text = []
    for reg in regs:
        client = await ClientsDAO.get_one_or_none(user_id=reg["user_id"])
        regs_text.append(
            f"{reg['reg_time_start'].strftime('%H:%M')} - {reg['reg_time_finish'].strftime('%H:%M')} {client['full_name']}")

    await state.set_state(AdminFSM.clients_reg_time)

    text = [
        f"Клиент №{client['id']} {client['full_name']}.\n",
        f"{category}: {state_data['services_titles']}.",
        f"Время процедур (авто): {state_data['duration']} минут",
        f"Время процедур (вручную): {client['service_duration']} минут\n",
        f"Выберите время в формате 09:00"
    ]
    if regs_text != []:
        text.insert(
            4, f"На дату {date_object.strftime('%d.%m.%Y')} уже есть следующие записи клиентов:")
        text.insert(5, "\n".join(regs_text) + "\n")
    kb = inline_kb.back_btn(cb_data="set_reg_date")
    return text, kb


@router.message(AdminFSM.clients_reg_date)
async def set_reg_date(message: Message, state: FSMContext):
    date_string = message.text
    format_string = '%d.%m.%Y'

    try:
        date_object = datetime.strptime(date_string, format_string)
        if datetime.date(date_object) <= datetime.date(datetime.today()):
            await message.answer("Невозможно записать на эту дату. Напишите дату для записи клиента в формате 05.02.2022")
            return
    except ValueError:
        await message.answer("Неправильный формат ввода. Напишите дату для записи клиента в формате 05.02.2022")
        return

    await state.update_data({"reg_date": date_object})

    text, kb = await set_reg_date_text_and_kb(state, date_object)
    await message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.clients_reg_time)
async def set_reg_time(message: Message, state: FSMContext):
    date_string = message.text
    format_string = '%H:%M'

    try:
        reg_time_start = datetime.strptime(date_string, format_string).time()

    except ValueError:
        await message.answer("Неправильный формат ввода. Напишите время в формате 09:00")
        return

    state_data = await state.get_data()
    client = state_data["client"]
    reg_time_finish = (datetime.combine(datetime.now(
    ), reg_time_start) + timedelta(minutes=state_data["duration"])).time()
    free_slot = await check_interval_for_events(
        state_data["reg_date"], reg_time_start, reg_time_finish)

    if free_slot:
        total_price = sum([service["price"]
                           for service in state_data["selected_services"]])
        state_data["price"] = total_price
        state_data["reg_time"] = reg_time_start
        state_data["services"] = state_data["selected_services"]
        await create_registration(
            state_data, phone=client["phone"], user_id=client["user_id"], client_service_duration=client["service_duration"])

        events = await get_events(schedule_date=state_data["reg_date"])
        regs = []
        for event in events:
            date_string = event["start"]["dateTime"].split('T')[0]
            date_object = datetime.strptime(date_string, "%Y-%m-%d")
            start_time = event["start"]["dateTime"].split('T')[1][:5]
            end_time = event["end"]["dateTime"].split('T')[1][:5]

            time_start = datetime.strptime(start_time, "%H:%M").time()
            time_finish = datetime.strptime(end_time, "%H:%M").time()
            reg = await RegistrationsDAO.get_one_or_none(reg_date=date_object, reg_time_start=time_start, reg_time_finish=time_finish)
            if reg:
                regs.append(reg)
        regs_text = []
        for reg in regs:
            client = await ClientsDAO.get_one_or_none(user_id=reg["user_id"])
            regs_text.append(
                f"{reg['reg_time_start'].strftime('%H:%M')} - {reg['reg_time_finish'].strftime('%H:%M')} {client['full_name']}")
        text = [
            f"Клиент №{client['id']} {client['full_name']} ЗАПИСАН на {reg_time_start.strftime('%H:%M')}.\n",
            f"{state_data['category']}: {state_data['services_titles']}.",
            f"Время процедур (авто): {state_data['duration']} минут",
            f"Время процедур (вручную): {client['service_duration']} минут\n",
            f"ИТОГО на дату {state_data['reg_date'].strftime('%d.%m.%Y')} список записей:",
            "\n".join(regs_text),
        ]
        await message.answer("\n".join(text))

        text = [
            f"👋🏻Приветики, {client['full_name']}!,",
            f"Записала тебя на {state_data['reg_date'].strftime('%d.%m.%Y')} {reg_time_start.strftime('%H:%M')}",
            f"на следующие процедуры: {state_data['services_titles']}.",
            f"Сумма к оплате: {total_price}.",
            "НАПОМИНАЮ - оплата наличными дешевле.",
            "Хорошего дня и отличного настроения!🌼"
        ]
        await bot.send_message(client["user_id"], "\n".join(text))

        current_datetime = datetime.now()
        date_time_str = f"{datetime.date(state_data['reg_date'])} {reg_time_start}"
        record_datetime = datetime.strptime(
            date_time_str, "%Y-%m-%d %H:%M:%S")
        time_difference = record_datetime - current_datetime

        less_than_24_hour = time_difference.total_seconds() <= 24 * 3600
        address = await TextsDAO.get_one_or_none(chapter="text|address")
        text = [
            f"Адрес: {address['text']}",
            "За сутки до записи я пришлю Вам напоминание😃, с подробным",
            "описанием как меня найти.",
            "Хорошего дня! 🌼"
        ]
        if less_than_24_hour:
            text2 = [
                "!!️ ВАЖНО: в ответ на мое сообщение (за 24 часа) обязательно",
                "подтвердите запись, иначе она автоматически отменяется!!️",
                "Если что-то изменится - предупредите меня🙏🏻, пожалуйста,",
                "заранее."
            ]
            text.insert(3, "\n".join(text2))
        kb = inline_kb.msg_to_personal_kb()
        await bot.send_message(client["user_id"], "\n".join(text), reply_markup=kb)
    else:
        text = "Невозможно произвести бронирование на указанное время, т.к. есть пересечения с другими записями"
        await message.delete()
        kb = inline_kb.back_btn(cb_data="set_reg_date")
        await message.answer(text, reply_markup=kb)
        text, kb = await set_reg_date_text_and_kb(state, state_data["reg_date"])
        await message.answer("\n".join(text), reply_markup=kb)

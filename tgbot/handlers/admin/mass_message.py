from datetime import datetime
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from tgbot.filters.admin import AdminFilter
from tgbot.keyboards.inline import AdminInlineKeyboard as inline_kb
from tgbot.misc.states import AdminFSM
from tgbot.models.sql_connector import MailingsDAO, client_group_translation, get_client_group_by_num, get_client_group_num
from tgbot.misc.scheduler import MailingScheduler

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


async def mass_message_text_and_kb():
    text = [
        'Раздел "Массовые сообщения".',
        "Выберите, что вы хотите сделать:"
    ]
    kb = inline_kb.mass_message_kb()
    return text, kb


@router.callback_query(F.data == "mass_message")
@router.callback_query(F.data == "cancel")
async def mass_message(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text, kb = await mass_message_text_and_kb()
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "new_mailing")
async def new_mailing(callback: CallbackQuery, state: FSMContext):
    new_clients = await MailingsDAO.get_clients_from_client_group(client_group="new_clients")
    all_clients = await MailingsDAO.get_clients_from_client_group(client_group="all_clients")
    not_new_clients = await MailingsDAO.get_clients_from_client_group(client_group="not_new_clients")
    bio_group = await MailingsDAO.get_clients_from_client_group(client_group="bio")
    laser_group = await MailingsDAO.get_clients_from_client_group(client_group="laser")

    await state.set_data({"new_clients": new_clients, "all_clients": all_clients, "not_new_clients": not_new_clients, "bio_group": bio_group, "laser_group": laser_group})

    text = [
        "Список доступных меток:",
        f"1. Новые клиенты - {len(new_clients)} клиент",
        f"2. Все клиенты - {len(all_clients)} клиента",
        f"3. Кроме новых клиентов - {len(not_new_clients)} клиентов",
        f"4. Био - {len(bio_group)} клиентов",
        f"5. Лазер - {len(laser_group)} клиентов",
        "Выберите группу клиентов (напишите номер метки), для которой",
        "вы хотите сделать рассылку:"
    ]
    await state.set_state(AdminFSM.mailing_client_group)
    kb = inline_kb.new_mailing_kb()
    await callback.message.answer("\n".join(text), reply_markup=kb)


async def get_mailing_text(status: str, only_ten=False):
    mailings = await MailingsDAO.get_many_sorted_by_dtime(status=status, reverse=True)

    if only_ten:
        mailings = mailings[:10]
    mailings_text = []
    ids = []

    for mailing in mailings:
        client_group = client_group_translation(mailing['client_group'])
        if mailing['client_group'] == "group_by_date":
            client_group = "Клиенты, записанные на определнную дату"

        mailings_text.append(
            f"{mailing['id']}. {mailing['dtime'].strftime('%d.%m.%Y %H:%M')} / {client_group}")
        ids.append(mailing["id"])

    if mailings_text == []:
        mailings_text.append("Таких рассылок нет")
    return mailings_text, ids


@router.callback_query(F.data == "mailings_list")
async def mailings_list(callback: CallbackQuery, state: FSMContext):
    sent_mailings_text, sent_ids = await get_mailing_text(status="sent", only_ten=True)
    waiting_mailings_text, waiting_ids = await get_mailing_text(status="waiting")
    ids = [*sent_ids, *waiting_ids]
    await state.set_data({"mailing_ids": ids})
    text = [
        "Отправленные рассылки (10 последних):",
        "\n".join(sent_mailings_text) + "\n",
        "Рассылки, ожидающие отправки (все):",
        "\n".join(waiting_mailings_text)
    ]
    if waiting_mailings_text != [] or sent_mailings_text != []:
        text.append("Выберите номер группы клиентов для подробностей:")

    await state.set_state(AdminFSM.mailing_id)
    kb = inline_kb.back_btn(cb_data="mass_message")
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.mailing_id)
async def mailing_info(message: Message, state: FSMContext):
    state_data = await state.get_data()
    mailing_ids = state_data["mailing_ids"]
    if message.text.isdigit():
        id = int(message.text)
        if id in mailing_ids:
            mailing = await MailingsDAO.get_one_or_none(id=id)
            num = get_client_group_num(mailing["client_group"])
            client_group = client_group_translation(mailing["client_group"])
            text = [
                f"Рассылка для группы клиентов: {num}. {client_group}",
                f"Дата и время отправки. {mailing['dtime']}",
                "Сообщение"
            ]
            await message.answer("\n".join(text))

            cancel = mailing["dtime"] > datetime.now()
            kb = inline_kb.mailing_info_kb(cancel=cancel, mailing_id=id)
            await message.answer(mailing["text"], reply_markup=kb)

        else:
            await message.answer("Введите номер из предложенного списка")
    else:
        await message.answer("Это не число. Введите номер из предложенного списка")


@router.callback_query(F.data.split(":")[0] == "cancel_mailing")
async def cancel_waiting(callback: CallbackQuery):
    id = int(callback.data.split(":")[1])
    mailing = await MailingsDAO.get_one_or_none(id=id)
    if mailing["dtime"] <= datetime.now():
        mailing_date = datetime.date(mailing["dtime"])
        mailing_time = datetime.time(mailing["dtime"])
        await callback.message.answer(f"Рассылка уже была отправлена {mailing_date} в {mailing_time}")
    else:
        await MailingsDAO.delete(id=id)
        await MailingScheduler.delete(job_id=id)

        await callback.message.answer("Рассылка отменена")
        await mass_message(callback)


@router.callback_query(F.data == "group_by_date")
async def group_by_date(callback: CallbackQuery, state: FSMContext):
    text = [
        "Рассылка будет отправлена для клиентов, у которых запись на определённую дату.",
        "Напишите эту дату записи в формате 05.03.2022:"
    ]
    await state.set_state(AdminFSM.group_by_date)
    await callback.message.answer("\n".join(text))


async def mailing_client_group_text_and_kb(client_group_num: int, client_group: str, state_data: dict, reg_date=None):
    clients = state_data[client_group]
    client_group = client_group_translation(client_group)
    text = [
        "Рассылка для группы клиентов:",
        f"{client_group_num}. {client_group} - {len(clients)} клиента",
        "Выберите дату и время отправки.",
        "Формат 05.03.2022 11:00"
    ]
    if reg_date:
        text[1] = f"{client_group} {reg_date} - {len(clients)} клиента"

    kb = inline_kb.mailing_for_group()
    return text, kb


@router.message(AdminFSM.group_by_date)
async def get_client_group_by_date(message: Message, state: FSMContext):
    reg_date = message.text
    format_str = "%d.%m.%Y"
    try:
        reg_date = datetime.date(datetime.strptime(reg_date, format_str))
    except ValueError:
        await message.answer("Ошибка. Введите дату в формате 05.03.2022")
        return

    client_group = "group_by_date"
    clients = await MailingsDAO.get_clients_from_client_group(client_group, reg_date=reg_date)
    if len(clients) == 0:
        await message.answer("На эту дату нет записей. Выберите другую дату")
        return

    await state.update_data({"client_group": client_group, client_group: clients, "reg_date": reg_date})
    await state.set_state(AdminFSM.mailing_dtime)
    state_data = await state.get_data()
    text, kb = await mailing_client_group_text_and_kb(client_group_num=0, client_group=client_group, state_data=state_data, reg_date=reg_date)
    await message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.mailing_client_group)
async def mailing_client_group(message: Message, state: FSMContext):
    state_data = await state.get_data()
    if message.text in ["1", "2", "3", "4", "5"]:
        client_group_num = int(message.text)
        client_group = get_client_group_by_num(client_group_num)
        await state.update_data({"client_group": client_group})

        text, kb = await mailing_client_group_text_and_kb(client_group_num, client_group, state_data)
        await state.set_state(AdminFSM.mailing_dtime)
        await message.answer("\n".join(text), reply_markup=kb)
    else:
        await message.answer("Введите номер метки")
        return


@router.callback_query(F.data == "mailing_client_group")
async def back_to_mailing_client_group(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client_group = state_data["client_group"]
    client_group_num = get_client_group_num(client_group)
    reg_date = state_data["reg_date"] if "reg_date" in state_data else None

    text, kb = await mailing_client_group_text_and_kb(client_group_num, client_group, state_data, reg_date)
    await state.set_state(AdminFSM.mailing_dtime)
    await callback.message.answer("\n".join(text), reply_markup=kb)


async def mailing_dtime_text_and_kb(dtime: datetime, state: FSMContext, reg_date=None):
    state_data = await state.get_data()
    client_group = state_data["client_group"]
    group_name = client_group_translation(client_group)

    text = [
        f"Рассылка для группы клиентов: {group_name}.",
        f"Дата отправки: {datetime.date(dtime)}",
        f"Время отправки: {datetime.time(dtime)}",
        "Напишите сообщение."
    ]
    if reg_date:
        text[0] = f"Рассылка для группы клиентов: {group_name} {reg_date}."

    await state.update_data({"dtime": dtime})
    await state.set_state(AdminFSM.mailing_text)
    kb = inline_kb.mailing_dtime_kb()
    return text, kb


@router.message(AdminFSM.mailing_dtime)
async def mailing_dtime(message: Message, state: FSMContext):
    dtime = message.text
    format_str = "%d.%m.%Y %H:%M"
    try:
        dtime = datetime.strptime(dtime, format_str)
        if dtime < datetime.now():
            await message.answer("Вы ввели прошедшую дату. Введите другую дату в формате 05.03.2022 11:00")
            return

    except ValueError:
        await message.answer("Ошибка. Введите дату и время в формате 05.03.2022 11:00")
        return

    state_data = await state.get_data()
    reg_date = state_data["reg_date"] if "reg_date" in state_data else None
    text, kb = await mailing_dtime_text_and_kb(dtime, state, reg_date=reg_date)
    await message.answer("\n".join(text), reply_markup=kb)


async def mailing_dtime_now_text_and_kb(client_group: str, reg_date=None):
    text = [
        f"Рассылка для группы клиентов: {client_group}.",
        "Дата и время отправки: Сейчас (сразу после ввода)",
        "Напишите сообщение."
    ]
    if reg_date:
        text[0] = f"Рассылка для группы клиентов: {client_group} {reg_date}."

    kb = inline_kb.mailing_dtime_kb()
    return text, kb


@router.callback_query(F.data == "send_now")
async def mailing_dtime_now(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client_group = client_group_translation(state_data["client_group"])
    reg_date = state_data["reg_date"] if "reg_date" in state_data else None

    await state.update_data({"dtime": "now"})
    await state.set_state(AdminFSM.mailing_text)

    text, kb = await mailing_dtime_now_text_and_kb(client_group, reg_date=reg_date)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "mailing_dtime")
async def back_to_mailing_dtime(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    dtime = state_data["dtime"]
    reg_date = state_data["reg_date"] if "reg_date" in state_data else None

    if dtime == "now":
        client_group = client_group_translation(state_data["client_group"])
        text, kb = await mailing_dtime_now_text_and_kb(client_group, reg_date=reg_date)
    else:
        text, kb = await mailing_dtime_text_and_kb(dtime, state, reg_date)

    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.mailing_text)
async def mailing_text(message: Message, state: FSMContext):
    state_data = await state.get_data()
    client_group = client_group_translation(state_data["client_group"])
    dtime = state_data["dtime"]
    dtime_text = "Сейчас" if dtime == "now" else dtime
    text = [
        f"Рассылка для группы клиентов: {client_group}.",
        f"Дата и время отправки: {dtime_text}",
        "Ваше сообщение, которое будет отправлено:"
    ]
    if "reg_date" in state_data:
        text[0] = f"Рассылка для группы клиентов: {client_group} {state_data['reg_date']}."

    await message.answer("\n".join(text))
    kb = inline_kb.mailing_text_kb()
    if message.content_type == "photo":
        new_text = message.html_text if message.caption else ""
        new_photo = message.photo[-1].file_id
        await message.answer_photo(photo=new_photo, caption=new_text, reply_markup=kb)
        await state.update_data({"mailing_photo": new_photo, "mailing_text": new_text})
    else:
        await state.update_data({"mailing_text": message.html_text})
        await message.answer(message.html_text, reply_markup=kb)


@router.callback_query(F.data == "send_mailing")
async def send_mailing(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    dtime = state_data["dtime"]
    text = state_data["mailing_text"]
    client_group = state_data["client_group"]
    photo = state_data["mailing_photo"] if "mailing_photo" in state_data else None

    mailing_dtime = dtime if dtime != "now" else datetime.now()
    await MailingsDAO.create(dtime=mailing_dtime, text=text, client_group=client_group, photo=photo)
    mailing = await MailingsDAO.get_one_or_none(dtime=mailing_dtime, text=text, client_group=client_group)

    if dtime == "now":
        await MailingScheduler.func(mailing_id=mailing["id"])
        await callback.message.answer("Рассылка сделано")
    else:
        await MailingScheduler.create(mailing_id=mailing["id"], dtime=mailing_dtime)
        await callback.message.answer("Рассылка создана успешно")

    text, kb = await mass_message_text_and_kb()
    await callback.message.answer("\n".join(text), reply_markup=kb)

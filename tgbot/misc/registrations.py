from datetime import datetime, timedelta

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from create_bot import bot, dp
from tgbot.handlers.user.registration_block import UserMainMenu
from tgbot.misc.scheduler import create_auto_texts, delete_auto_texts
from tgbot.models.sql_connector import ClientsDAO, RegistrationsDAO
from tgbot.calendar_api.calendar import create_event, delete_event_by_reg_id


async def create_registration(data: dict, phone: str, user_id: str | int, client_service_duration=None) -> int:
    start_time = data["reg_time"]
    if client_service_duration:
        finish_time = (datetime.combine(datetime.today(), start_time) +
                       timedelta(minutes=client_service_duration)).time()
    else:
        finish_time = (datetime.combine(datetime.today(), start_time) +
                       timedelta(minutes=data["duration"])).time()

    services_ids = []
    for service in data["services"]:
        services_ids.append(service["id"])

    await RegistrationsDAO.create(
        reg_date=data["reg_date"],
        reg_time_start=start_time,
        reg_time_finish=finish_time,
        services=services_ids,
        total_price=data["price"],
        phone=phone,
        user_id=str(user_id)
    )
    client = await ClientsDAO.get_one_or_none(user_id=str(user_id))
    registration = await RegistrationsDAO.get_one_or_none(
        reg_date=data["reg_date"],
        reg_time_start=start_time
    )
    await create_event(f'{client["first_name"]} {client["last_name"]}', data["reg_date"], start_time, finish_time)
    await create_auto_texts(reg_id=int(registration["id"]), user_id=user_id)
    return registration["id"]


async def cancel_registration(user_id: int | str, reg_id: int, send_message=True):
    await update_registration(reg_id=reg_id, status="cancelled")
    text = "Запись отменена"
    state: FSMContext = FSMContext(
        bot=bot,
        storage=dp.storage,
        key=StorageKey(
            chat_id=user_id,
            user_id=user_id,
            bot_id=bot.id
        )

    )
    if send_message:
        await bot.send_message(chat_id=user_id, text=text)
    await UserMainMenu.menu_type(user_id=str(user_id), state=state)


async def update_registration(reg_id: int, **data):
    reg = await RegistrationsDAO.get_one_or_none(id=reg_id)
    if any(key in data for key in ["reg_date", "reg_time_start", "reg_time_finish"]) or ("status" in data and data["status"].startswith("cancelled")):
        await delete_event_by_reg_id(reg_id)
        await delete_auto_texts(reg_id, reg["user_id"])

    await RegistrationsDAO.update(reg_id=reg_id, **data)
    if any(key in data for key in ["reg_date", "reg_time_start", "reg_time_finish"]):
        client = await ClientsDAO.get_one_or_none(user_id=str(reg["user_id"]))
        full_name = client['first_name'] + " " + client['last_name']
        event_data = {"event_name": full_name, "event_date": reg["reg_date"],
                      "start_time": reg["reg_time_start"], "end_time": reg["reg_time_finish"]}
        await create_event(**event_data)
        await create_auto_texts(reg_id, reg["user_id"])

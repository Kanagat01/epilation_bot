from datetime import datetime, timedelta

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from create_bot import bot, dp
from tgbot.handlers.user.registration_block import UserMainMenu
from tgbot.misc.scheduler import AutoTextScheduler
from tgbot.models.sql_connector import ClientsDAO, MailingsDAO, RegistrationsDAO, ServicesDAO
from tgbot.calendar_api.calendar import create_event, delete_event_by_reg_id


async def create_registration(data: dict, phone: str, user_id: str | int, client_service_duration=None, advance="not_required") -> int:
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
        user_id=str(user_id),
        advance=advance
    )
    client = await ClientsDAO.get_one_or_none(user_id=str(user_id))
    await create_event(f'{client["first_name"]} {client["last_name"]}', data["reg_date"], start_time, finish_time)

    registration = await RegistrationsDAO.get_one_or_none(
        reg_date=data["reg_date"],
        reg_time_start=start_time
    )
    reg_datetime = datetime.combine(data["reg_date"], start_time)

    auto_texts = [
        ("before_2h", reg_datetime - timedelta(hours=2)),
        ("after_5h", reg_datetime + timedelta(hours=5)),
        ("after_1m", reg_datetime + timedelta(days=30)),
        ("after_3m", reg_datetime + timedelta(days=90))
    ]

    finished_regs = await RegistrationsDAO.get_many(user_id=str(user_id), status="finished")
    if len(finished_regs) > 0:
        auto_texts.append(("before_24h_old", reg_datetime - timedelta(days=1)))
    else:
        auto_texts.append(("before_24h_new", reg_datetime - timedelta(days=1)))

    service = await ServicesDAO.get_one_or_none(id=services_ids[0])
    if service["category"] == "laser":
        auto_texts.append(
            ("after_3h_laser", reg_datetime + timedelta(hours=3)))
    else:
        auto_texts.append(("after_3h_bio", reg_datetime + timedelta(hours=3)))

    for auto_text, dtime in auto_texts:
        pass
        # await AutoTextScheduler.create(auto_text, user_id, dtime)

    return registration["id"]


async def cancel_registration(user_id: int | str, reg_id: int, send_message=True):
    await RegistrationsDAO.update(reg_id=reg_id, status="cancelled")
    text = "Запись отменена"
    state_with: FSMContext = FSMContext(
        bot=bot,
        storage=dp.storage,
        key=StorageKey(
            chat_id=user_id,
            user_id=user_id,
            bot_id=bot.id
        )

    )
    await delete_event_by_reg_id(reg_id)
    state = await state_with.get_state()
    if send_message:
        await bot.send_message(chat_id=user_id, text=text)
    await UserMainMenu.menu_type(user_id=str(user_id), state=state)

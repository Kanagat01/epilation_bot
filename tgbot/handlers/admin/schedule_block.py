import re
from datetime import datetime as dt
from datetime import timedelta, time

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from create_bot import bot
from tgbot.filters.admin import AdminFilter
from tgbot.misc.registrations import update_registration
from tgbot.models.sql_connector import RegistrationsDAO
from tgbot.keyboards.inline import AdminInlineKeyboard as inline_kb
from tgbot.misc.states import AdminFSM
from tgbot.handlers.admin.clients import export_to_csv
from tgbot.calendar_api.calendar import *
from tgbot.handlers.helpers import reset_state


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


def schedule_text_and_kb():
    text = [
        "Напишите дату. Формат: 25.05.2022",
        "Или нажмите на одну из кнопок:"
    ]
    kb = inline_kb.schedule_kb()
    return text, kb


@router.callback_query(F.data == "schedule")
async def schedule(callback: CallbackQuery, state: FSMContext):
    text, kb = schedule_text_and_kb()
    await state.set_state(AdminFSM.schedule_date)
    await callback.message.answer("\n".join(text), reply_markup=kb)


async def schedule_date_text_and_kb(schedule_date: date | datetime, page=0):
    try:
        schedule_date = dt.date(schedule_date)
    except TypeError:
        pass
    events = await get_events(schedule_date)
    events_text = ["На эту дату нет записей"] if events == [] else []
    start_idx = page * 10
    end_idx = start_idx + 10
    for event in events[start_idx:end_idx]:
        event_name = event["summary"]
        start_time = event["start"]["dateTime"].split('T')[1][:5]
        end_time = event["end"]["dateTime"].split('T')[1][:5]
        events_text.append(f'{start_time}-{end_time} {event_name}')
    text = [
        f"Расписание на {schedule_date}.",
        "\n".join(events_text)
    ]
    prev_page = page > 0
    next_page = end_idx < len(events)
    kb = inline_kb.schedule_date_kb(
        schedule_date=schedule_date, page=page, prev_page=prev_page, next_page=next_page)
    return text, kb


@router.callback_query(F.data == "schedule_for_today")
async def schedule_for_today(callback: CallbackQuery):
    schedule_date = dt.today()
    text, kb = await schedule_date_text_and_kb(schedule_date)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "schedule_for_tomorrow")
async def schedule_for_tomorrow(callback: CallbackQuery):
    schedule_date = dt.today() + timedelta(days=1)
    text, kb = await schedule_date_text_and_kb(schedule_date)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "date_range")
async def date_range(callback: CallbackQuery, state: FSMContext):
    text = [
        "Диапазон хх.хх.хххх - хх.хх.хххх.",
        "Напишите первую дату диапазона в формате 01.01.2001:"
    ]
    kb = inline_kb.back_btn(cb_data="schedule")
    await state.set_state(AdminFSM.first_date_of_range)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.first_date_of_range)
async def first_date_of_range(message: Message, state: FSMContext):
    format_str = "%d.%m.%Y"
    try:
        first_date = dt.strptime(message.text, format_str)
    except ValueError:
        await message.answer("Неверный формат. Введите дату в формате 01.01.2001")
        return

    await state.set_data({"first_date": dt.date(first_date)})
    await state.set_state(AdminFSM.second_date_of_range)

    text = [
        f"Диапазон {message.text} - хх.хх.хххх.",
        "Напишите вторую дату диапазона в формате 01.01.2001:"
    ]
    kb = inline_kb.back_btn(cb_data="date_range")
    await message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.second_date_of_range)
async def second_date_of_range(message: Message, state: FSMContext):
    format_str = "%d.%m.%Y"
    try:
        second_date = dt.strptime(message.text, format_str)
    except ValueError:
        await message.answer("Неверный формат. Введите дату в формате 01.01.2001")
        return
    state_data = await state.get_data()
    first_date = state_data["first_date"]
    second_date = second_date.date()
    current_date = first_date
    while current_date <= second_date:
        text, kb = await schedule_date_text_and_kb(current_date)
        if text[1] != "На эту дату нет записей":
            await message.answer("\n".join(text), reply_markup=kb)
        current_date += timedelta(days=1)


@router.message(AdminFSM.schedule_date)
async def schedule_date(message: Message):
    format_str = "%d.%m.%Y"
    try:
        schedule_date = dt.strptime(message.text, format_str)
    except ValueError:
        await message.answer("Неверный формат. Введите дату в формате 01.01.2001")
        return

    text, kb = await schedule_date_text_and_kb(schedule_date)
    await message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "back_to_schedule_date")
async def schedule_date(callback: CallbackQuery, state: FSMContext):
    schedule_date = dt.strptime(callback.data.split(":")[1], "%Y-%m-%d")
    text, kb = await schedule_date_text_and_kb(schedule_date)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "schedule_prev_regs")
@router.callback_query(F.data.split(":")[0] == "schedule_next_regs")
async def schedule_pagination(callback: CallbackQuery):
    await callback.message.delete()
    _, current_date, page = callback.data.split(":")
    current_date = dt.strptime(current_date, "%Y-%m-%d")
    text, kb = await schedule_date_text_and_kb(current_date, page=int(page))
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "symbols")
async def symbols(callback: CallbackQuery):
    text = [
        "Условные обозначения:",
        "✅ - Клиент подтвердил запись.",
        "⏳ - Клиенту выслан запрос на подтверждение, но он ещё не подтвердил запись.\n",
        "🆕 - Новый клиент (не был ещё ни на одном приёме)",
        "➖ - Свободное время",
        "❌ - Заблокированное время (отпуск или по телефону записался новый клиент, у которого нет аккаунта в боте)"
    ]
    await callback.message.answer("\n".join(text))


@router.callback_query(F.data.split(":")[0] == "export_schedule_to_csv")
async def export_schedule_to_csv(callback: CallbackQuery):
    schedule_date = callback.data.split(":")[1]
    schedule_date = dt.strptime(schedule_date, "%Y-%m-%d")
    data = [[f"Расписание на {schedule_date}"], [
        "Время начала", "Время окончания", "Название события"]]
    events = await get_events(schedule_date)
    for event in events:
        pattern = re.compile(r'[^\w\s\d\[\]@:-]')
        event_name = re.sub(pattern, '', event["summary"])
        start_time = event["start"]["dateTime"].split('T')[1][:5]
        end_time = event["end"]["dateTime"].split('T')[1][:5]
        data.append([start_time, end_time, event_name])
    print(data)
    await export_to_csv(callback.from_user.id, data)


@router.callback_query(F.data.split(":")[0] == "block_for_reg")
async def block_for_reg(callback: CallbackQuery, state: FSMContext):
    schedule_date = callback.data.split(":")[1]
    text = "Введите дату и время, с которого вы хотите заблокировать новые записи. Формат: 01.01.2001 09:00"
    cb_data = f"back_to_schedule_date:{schedule_date}"
    kb = inline_kb.back_btn(cb_data)
    await state.set_data({"schedule_date": schedule_date})
    await state.set_state(AdminFSM.block_date1)
    await callback.message.answer(text, reply_markup=kb)


def block_date1_text_and_kb(datetime1, cb_data):
    text = [
        f"Диапазон для блокировки: {datetime1.strftime('%d.%m.%Y %H:%M')} - хх.хх.хххх ХХ:ХХ.",
        "Введите дату и время, до которых вы хотите заблокировать новые записи.",
        "Формат тот же: 01.01.2001 09:00"
    ]
    kb = inline_kb.back_btn(cb_data)
    return text, kb


@router.message(AdminFSM.block_date1)
async def block_date1(message: Message, state: FSMContext):
    format_str = "%d.%m.%Y %H:%M"
    try:
        datetime1 = dt.strptime(message.text, format_str)
        if datetime1 < dt.now():
            await message.answer("Введите время больше чем текущее")
            return

    except ValueError:
        await message.answer("Неверный формат. Введите дату в формате 01.01.2001 09:00")
        return

    state_data = await state.get_data()
    await state.update_data({"datetime1": datetime1})
    await state.set_state(AdminFSM.block_date2)

    cb_data = f"block_for_reg:{state_data['schedule_date']}"
    text, kb = block_date1_text_and_kb(datetime1, cb_data)
    await message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.block_date2)
async def block_date2(message: Message, state: FSMContext):
    state_data = await state.get_data()
    format_str = "%d.%m.%Y %H:%M"
    datetime1 = state_data["datetime1"]
    try:
        datetime2 = dt.strptime(message.text, format_str)
        if datetime2 <= datetime1:
            await message.answer(f"Введите дату больше чем {datetime1.strftime('%d.%m.%Y %H:%M')} в формате 01.01.2001 09:00")
            return

        if datetime2 - datetime1 >= timedelta(days=32):
            await message.answer(f"Диапазон дат не должен превышать 32 дня")
            return

    except ValueError:
        await message.answer("Неверный формат. Введите дату в формате 01.01.2001 09:00")
        return

    all_events = []
    current_date = datetime1.date()
    while current_date <= datetime2.date():
        start_time = time(
            0, 0) if current_date != datetime1.date() else datetime1.time()
        finish_time = time(
            23, 59) if current_date != datetime2.date() else datetime2.time()

        events = await get_events(current_date, start_time, finish_time)
        all_events.extend(events)

        current_date += timedelta(days=1)

    if len(all_events) == 0:
        text = f"В диапазоне: {datetime1.strftime('%d.%m.%Y %H:%M')} - {datetime2.strftime('%d.%m.%Y %H:%M')} произведена блокировка времени для записи."
        await message.answer(text)
        await state.clear()
        await create_block_events(message, datetime1, datetime2)
    else:
        regs = []
        events_text = []
        for event in all_events:
            event_name = event["summary"]
            date_string = event["start"]["dateTime"].split('T')[0]
            date_object = dt.strptime(date_string, "%Y-%m-%d")
            event_date = date_object.strftime("%d.%m.%Y")
            start_time = event["start"]["dateTime"].split('T')[1][:5]
            end_time = event["end"]["dateTime"].split('T')[1][:5]

            time_start = dt.strptime(start_time, "%H:%M").time()
            time_finish = dt.strptime(end_time, "%H:%M").time()
            reg = await RegistrationsDAO.get_one_or_none(reg_date=date_object, reg_time_start=time_start, reg_time_finish=time_finish)
            regs.append(reg)

            events_text.append(
                f'{event_date} {start_time}-{end_time} {event_name}')

        await state.update_data({"events": all_events, "regs": regs, "datetime2": datetime2, "events_text": events_text})
        text = [
            f"Внимание! В диапазоне: {datetime1.strftime('%d.%m.%Y %H:%M')} - {datetime2.strftime('%d.%m.%Y %H:%M')} имеются записи клиентов:\n",
            "\n".join(events_text),
            "\nЧто будем делать?"
        ]
        kb = inline_kb.block_date2_kb()
        await message.answer("\n".join(text), reply_markup=kb)


async def create_block_events(message, datetime1, datetime2):
    current_date = datetime1.date()
    while current_date <= datetime2.date():
        start_time = time(
            0, 0) if current_date != datetime1.date() else datetime1.time()
        end_time = time(
            23, 59) if current_date != datetime2.date() else datetime2.time()
        await create_event("❌ Заблокировано для записи",
                           current_date, start_time, end_time)

        text, kb = await schedule_date_text_and_kb(current_date)
        if text[1] != "На эту дату нет записей":
            await message.answer("\n".join(text), reply_markup=kb)

        current_date += timedelta(days=1)


@router.callback_query(F.data == "block_without_canceling")
async def block_without_cancelling(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    datetime1 = state_data["datetime1"]
    datetime2 = state_data["datetime2"]
    events = state_data["events"]

    date_str = events[0]["start"]["dateTime"]
    first_event_datetime = dt.fromisoformat(date_str).replace(tzinfo=None)

    if datetime1 < first_event_datetime:
        current_date = datetime1.date()
        while current_date <= first_event_datetime.date():
            start_time = time(
                0, 0) if current_date != datetime1.date() else datetime1.time()
            end_time = time(
                23, 59) if current_date != first_event_datetime.date() else first_event_datetime.time()

            await create_event("❌ Заблокировано для записи",
                               current_date, start_time, end_time)
            current_date += timedelta(days=1)

    date_str = events[-1]["end"]["dateTime"]
    last_event_datetime = dt.fromisoformat(date_str).replace(tzinfo=None)

    if last_event_datetime < datetime2:
        current_date = last_event_datetime.date()
        while current_date <= datetime2.date():
            start_time = time(
                0, 0) if current_date != last_event_datetime.date() else last_event_datetime.time()
            end_time = time(
                23, 59) if current_date != datetime2.date() else datetime2.time()

            await create_event("❌ Заблокировано для записи",
                               current_date, start_time, end_time)
            current_date += timedelta(days=1)

    for event in events[:-1]:
        date_str = event["end"]["dateTime"]
        event1_dt = dt.fromisoformat(date_str)

        event2 = events[events.index(event) + 1]
        date_str = event2["start"]["dateTime"]
        event2_dt = dt.fromisoformat(date_str)

        if event1_dt < event2_dt:
            current_date = event1_dt.date()
            while current_date <= event2_dt.date():
                start_time = time(
                    0, 0) if current_date != event1_dt.date() else event1_dt.time()
                end_time = time(
                    23, 59) if current_date != event2_dt.date() else event2_dt.time()

                await create_event("❌ Заблокировано для записи",
                                   current_date, start_time, end_time)
                current_date += timedelta(days=1)

    text = [
        f'В диапазоне: {datetime1.strftime("%d.%m.%Y %H:%M")} - {datetime2.strftime("%d.%m.%Y %H:%M")} произведена',
        "блокировка времени для записи БЕЗ отмены записей клиентов."
    ]
    await state.clear()
    await callback.message.answer("\n".join(text))

    current_date = datetime1.date()
    while current_date <= datetime2.date():
        text, kb = await schedule_date_text_and_kb(current_date)
        if text[1] != "На эту дату нет записей":
            await callback.message.answer("\n".join(text), reply_markup=kb)

        current_date += timedelta(days=1)


@router.callback_query(F.data == "block_and_cancel")
async def block_and_cancel(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    datetime1 = state_data["datetime1"]
    datetime2 = state_data["datetime2"]
    text = [
        f'В диапазоне: {datetime1.strftime("%d.%m.%Y %H:%M")} - {datetime2.strftime("%d.%m.%Y %H:%M")} будет',
        "произведена блокировка времени С отменой записей клиентов.",
        "Нужно ли отправить клиентам комментарий с причиной отмены",
        'записи? Введите текст причины отмены, либо "0", если',
        "комментария не нужно."
    ]
    await state.set_state(AdminFSM.cancel_reason)
    kb = inline_kb.back_btn(cb_data="back_to_block_date2")
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.cancel_reason)
async def cancel_reason(message: Message, state: FSMContext):
    reason = message.text if message.text != "0" else "Не указана"
    state_data = await state.get_data()
    datetime1 = state_data["datetime1"]
    datetime2 = state_data["datetime2"]
    regs = state_data["regs"]

    for reg in regs:
        reg_id = reg["id"]
        await update_registration(reg_id=reg_id, status="cancelled_by_master")
        text = [
            f'Ваша запись на {reg["reg_date"].strftime("%d.%m.%Y %H:%M")} отменена мастером.',
            f'Причина: {reason}'
        ]
        await bot.send_message(reg["user_id"], "\n".join(text))

    text = [
        f"В диапазоне: {datetime1.strftime('%d.%m.%Y %H:%M')} - {datetime2.strftime('%d.%m.%Y %H:%M')} произведена",
        "блокировка времени для записи С отменой записей клиентов."
    ]
    await message.answer("\n".join(text))
    await state.clear()
    await create_block_events(message, state_data["datetime1"], state_data["datetime2"])


@router.callback_query(F.data == "back_to_block_date1")
async def back_to_block_date1(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    datetime1 = state_data["datetime1"]
    cb_data = f"block_for_reg:{state_data['schedule_date']}"
    text, kb = block_date1_text_and_kb(datetime1, cb_data)
    await state.set_state(AdminFSM.block_date2)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "back_to_block_date2")
async def back_to_block_date2(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    datetime1 = state_data["datetime1"]
    datetime2 = state_data["datetime2"]
    events_text = state_data["events_text"]
    text = [
        f"Внимание! В диапазоне: {datetime1.strftime('%d.%m.%Y %H:%M')} - {datetime2.strftime('%d.%m.%Y %H:%M')} имеются записи клиентов:\n",
        "\n".join(events_text),
        "\nЧто будем делать?"
    ]
    kb = inline_kb.block_date2_kb()
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "unblock")
async def unblock_time(callback: CallbackQuery, state: FSMContext):
    schedule_date = callback.data.split(":")[1]
    text = "Введите дату и время, с которого вы хотите отменить блокировку. Формат: 01.01.2001 09:00"
    cb_data = f"back_to_schedule_date:{schedule_date}"
    kb = inline_kb.back_btn(cb_data)
    await state.set_data({"schedule_date": schedule_date})
    await state.set_state(AdminFSM.unblock_date1)
    await callback.message.answer(text, reply_markup=kb)


@router.message(AdminFSM.unblock_date1)
async def unblock_date1(message: Message, state: FSMContext):
    format_str = "%d.%m.%Y %H:%M"
    try:
        datetime1 = dt.strptime(message.text, format_str)
        if datetime1 < dt.now():
            await message.answer("Введите время больше чем текущее")
            return

    except ValueError:
        await message.answer("Неверный формат. Введите дату в формате 01.01.2001 09:00")
        return

    state_data = await state.get_data()
    await state.update_data({"datetime1": datetime1})
    await state.set_state(AdminFSM.unblock_date2)

    text = [
        f"Диапазон для отмены блокировки: {datetime1.strftime('%d.%m.%Y %H:%M')} - хх.хх.хххх ХХ:ХХ.",
        "Введите дату и время, до которого будет отменена блокировка.",
        "Формат тот же: 01.01.2001 09:00"
    ]
    kb = inline_kb.back_btn(f"unblock:{state_data['schedule_date']}")
    await message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.unblock_date2)
async def unblock_date2(message: Message, state: FSMContext):
    state_data = await state.get_data()
    format_str = "%d.%m.%Y %H:%M"

    schedule_date = state_data["schedule_date"]
    schedule_date = datetime.strptime(schedule_date, '%Y-%m-%d')

    datetime1 = state_data["datetime1"]
    try:
        datetime2 = dt.strptime(message.text, format_str)
        if datetime2 <= datetime1:
            await message.answer(f"Введите дату больше чем {datetime1.strftime('%d.%m.%Y %H:%M')} в формате 01.01.2001 09:00")
            return

        if datetime2 - datetime1 >= timedelta(days=32):
            await message.answer(f"Диапазон дат не должен превышать 32 дня")
            return

    except ValueError:
        await message.answer("Неверный формат. Введите дату в формате 01.01.2001 09:00")
        return

    all_events = []
    current_date = datetime1.date()
    while current_date <= datetime2.date():
        start_time = time(
            0, 0) if current_date != datetime1.date() else datetime1.time()
        finish_time = time(
            23, 59) if current_date != datetime2.date() else datetime2.time()

        events = await get_events(current_date, start_time, finish_time)
        events = [
            event for event in events if event["summary"].startswith("❌")]
        all_events.extend(events)

        current_date += timedelta(days=1)

    if len(all_events) == 0:
        await message.answer("В этом отрезке нет блокировок времени")
        text, kb = await schedule_date_text_and_kb(schedule_date)
        await message.answer("\n".join(text), reply_markup=kb)
        await state.clear()
        return

    events_text = []
    for event in all_events:
        event_name = event["summary"]
        date_string = event["start"]["dateTime"].split('T')[0]
        date_object = dt.strptime(date_string, "%Y-%m-%d")
        event_date = date_object.strftime("%d.%m.%Y")
        start_time = event["start"]["dateTime"].split('T')[1][:5]
        end_time = event["end"]["dateTime"].split('T')[1][:5]

        await delete_event(event_id=event["id"])
        events_text.append(
            f'{event_date} {start_time}-{end_time} {event_name}')

    text = [
        "Была отменена блокировка следующих отрезков:",
        "\n".join(events_text),
    ]
    await message.answer("\n".join(text))
    text, kb = await schedule_date_text_and_kb(schedule_date)
    await message.answer("\n".join(text), reply_markup=kb)
    await state.clear()


@router.callback_query(F.data.split("|")[0] == "back_to_schedule")
async def back_to_schedule(callback: CallbackQuery):
    date = callback.data.split("|")[1]
    schedule_date = dt.strptime(date, "%Y-%m-%d")
    text, kb = await schedule_date_text_and_kb(schedule_date)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "change_reg")
async def schedule_change_reg(callback: CallbackQuery, state: FSMContext):
    cb_data = callback.data.split(":")[1]
    text = "Введите идентификатор записи, которую вы хотите изменить:"
    kb = inline_kb.back_btn(cb_data)
    await state.set_data({"cb_data": callback.data})
    await state.set_state(AdminFSM.change_reg_id)
    await callback.message.answer(text, reply_markup=kb)


@router.message(AdminFSM.change_reg_id)
async def change_reg_id(message: Message, state: FSMContext):
    reg_id = message.text
    if not reg_id.isdigit():
        await message.answer("Это не число. Введите идентификатор записи, которую вы хотите изменить:")
        return

    reg = await RegistrationsDAO.get_one_or_none(id=int(reg_id))
    if not reg:
        await message.answer("Записи с таким id не существует")
        return

    if reg["status"] not in ["no_show", "cancelled", "cancelled_by_master", "finished"]:
        state_data = await state.get_data()
        cb_data = state_data["cb_data"]
        client = await ClientsDAO.get_one_or_none(user_id=reg["user_id"])
        full_name = f'{client["first_name"]} {client["last_name"]}'
        reg_date = reg["reg_date"].strftime("%d.%m.%Y")
        reg_time_start = reg["reg_time_start"].strftime("%H:%M")
        await state.update_data({"client": client, "reg": reg, "reg_date": reg_date, "reg_time_start": reg_time_start})

        text = [
            f'Выбрана запись No {reg["id"]} от клиента {full_name} на {reg_date} {reg_time_start}.',
            "Что с ней нужно сделать?"
        ]
        kb = inline_kb.change_reg_id_kb(cb_data)
        await reset_state(state)
        await message.answer("\n".join(text), reply_markup=kb)
    else:
        text = "Нельзя изменить запись с таким номером"
        await message.answer(text)


@router.callback_query(F.data == "back_to_change_reg_id")
async def back_to_change_reg_id(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    reg = state_data["reg"]
    client = state_data["client"]
    full_name = f'{client["first_name"]} {client["last_name"]}'
    reg_date = state_data["reg_date"]
    reg_time_start = state_data["reg_time_start"]
    cb_data = state_data["cb_data"]
    text = [
        f'Выбрана запись No {reg["id"]} от клиента {full_name} на {reg_date} {reg_time_start}.',
        "Что с ней нужно сделать?"
    ]
    kb = inline_kb.change_reg_id_kb(cb_data)
    await reset_state(state)
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data == "change_reg_time")
async def change_reg_time(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    client = state_data["client"]
    full_name = f'{client["first_name"]} {client["last_name"]}'
    reg = state_data["reg"]
    reg_date = state_data["reg_date"]
    reg_time_start = state_data["reg_time_start"]

    category = None
    duration = 0
    services_text = []
    for service_id in reg["services"]:
        service = await ServicesDAO.get_one_or_none(id=service_id)
        duration += service["duration"]
        services_text.append(service["title"])
        if not category:
            category = category_translation(service["category"])

    text = [
        f'Клиент №{client["id"]} {full_name}.',
        f'Текущая запись {reg["id"]} на {reg_date} {reg_time_start}.',
        f'{category}: {", ".join(services_text)}.',
        f'Время процедур (авто): {duration} минут',
        f'Время процедур (вручную): {client["service_duration"]} минут',
        "\nНапишите новые дату и время для этой записи клиента в формате 05.02.2022 09:00"
    ]
    kb = inline_kb.back_btn(cb_data="back_to_change_reg_id")
    await state.set_state(AdminFSM.new_reg_time)
    await state.update_data({"category": category, "duration": duration, "services_text": services_text})
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.new_reg_time)
async def new_reg_time(message: Message, state: FSMContext):
    format_str = "%d.%m.%Y %H:%M"
    try:
        reg_datetime = dt.strptime(message.text, format_str)
    except ValueError:
        await message.answer("Неверный формат. Введите дату в формате 05.02.2022 09:00")
        return

    state_data = await state.get_data()
    reg = state_data["reg"]
    duration = int(state_data["duration"])
    reg_date = reg_datetime.date()
    start_time = reg_datetime.time()
    finish_time = (reg_datetime + timedelta(minutes=duration)).time()
    free_slot = await check_interval_for_events(reg_date, start_time, finish_time, except_reg_id=reg["id"])
    if free_slot:
        reg = state_data["reg"]
        client = state_data["client"]
        full_name = f'{client["first_name"]} {client["last_name"]}'
        prev_reg_date = state_data["reg_date"]
        prev_time_start = state_data["reg_time_start"]
        category = state_data["category"]
        services_text = state_data["services_text"]

        await update_registration(reg_id=reg["id"], reg_date=reg_date, reg_time_start=start_time, reg_time_finish=finish_time)

        reg_date = reg_date.strftime("%d.%m.%Y")
        start_time = start_time.strftime("%H:%M")

        text = [
            f'Время записи {reg["id"]} успешно изменено с {prev_reg_date} {prev_time_start} на {reg_date} {start_time}',
            f'Клиент №{client["id"]} {full_name}.',
            f'{category}: {", ".join(services_text)}.',
            f'Время процедур (авто): {duration} минут',
            f'Время процедур (вручную): {client["service_duration"]} минут'
        ]
        await message.answer("\n".join(text))

        text = [
            f'Для вашей записи на {prev_reg_date} {prev_time_start} мастером изменено время.',
            f'Новое время записи: {reg_date} {start_time}'
        ]
        await bot.send_message(reg["user_id"], "\n".join(text))
    else:
        text = "Невозможно перенести запись на указанное время"
        await message.answer(text)


@router.callback_query(F.data == "cancel_reg_by_master")
async def cancel_reg_by_master(callback: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    reg = state_data["reg"]
    await update_registration(reg_id=reg["id"], status="cancelled_by_master")

    client = state_data["client"]
    full_name = f'{client["first_name"]} {client["last_name"]}'
    reg_date = state_data["reg_date"]
    reg_time_start = state_data["reg_time_start"]

    text = f'Запись No {reg["id"]} от клиента {full_name} на {reg_date} {reg_time_start} отменена.'
    await callback.message.answer(text)

    text = f"Ваша запись на {reg_date} {reg_time_start} отменена мастером."
    await bot.send_message(reg["user_id"], text)

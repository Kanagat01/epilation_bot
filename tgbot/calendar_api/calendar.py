import re
from datetime import datetime as dt
from datetime import time, date, datetime
from typing import Union
from googleapiclient.errors import HttpError
from create_bot import local_tz, local_tz_obj, calendar_id, calendar_service
from tgbot.models.sql_connector import ClientsDAO, RegistrationsDAO, ServicesDAO, category_translation


def async_exception_handler_decorator(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HttpError as e:
            print(f"Произошла ошибка: {e}")
    return wrapper


tz = datetime.now(local_tz_obj).strftime('%z')


@async_exception_handler_decorator
async def get_events(schedule_date: Union[date, dt], start_time=time.min, end_time=time.max):
    start_time = dt.combine(
        schedule_date, start_time).isoformat() + tz
    end_time = dt.combine(
        schedule_date, end_time).isoformat() + tz

    events_result = (
        calendar_service.events()
        .list(
            calendarId=calendar_id,
            timeMin=start_time,
            timeMax=end_time,
            maxResults=1000,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])
    for event in events:
        event_name = event["summary"]
        if event_name.startswith("❌"):
            continue

        first_name, last_name = re.sub(
            r'[^\w\s]', '', event_name).split(" ")

        client = await ClientsDAO.get_one_or_none(first_name=first_name, last_name=last_name)
        if client:
            reg_date_str = event["start"]["dateTime"].split('T')[0]
            reg_date = dt.strptime(reg_date_str, "%Y-%m-%d").date()

            time_start_str = event["start"]["dateTime"].split('T')[1][:5]
            reg_time_start = dt.strptime(time_start_str, "%H:%M").time()

            time_finish_str = event["end"]["dateTime"].split('T')[1][:5]
            reg_time_finish = dt.strptime(time_finish_str, "%H:%M").time()

            username = client["username"]
            reg = await RegistrationsDAO.get_one_or_none(user_id=client["user_id"], reg_date=reg_date, reg_time_start=reg_time_start, reg_time_finish=reg_time_finish)
            category = None
            services_text = []
            for service_id in reg["services"]:
                service = await ServicesDAO.get_one_or_none(id=service_id)

                if not category:
                    category = category_translation(service["category"])
                services_text.append(service["title"])

            event["summary"] = f'{event_name} {username} - {category}: {", ".join(services_text)} [{reg["id"]}]'
    return events


async def update_event_name(event_name, event_date, start_time, end_time):
    if event_name.startswith("❌"):
        return event_name

    event_name = re.sub(r'[^\w\s]', '', event_name)
    dict1 = {"approved": "✅", "confirmation_sent": "⏳",
             "new_client": "🆕", "advance": "✔️", "not_advance": "❓", "payment_not_work": "❗️"}
    first_name, last_name = event_name.split(" ")
    client = await ClientsDAO.get_one_or_none(first_name=first_name, last_name=last_name)
    if client:
        reg = await RegistrationsDAO.get_one_or_none(user_id=client["user_id"], reg_date=event_date, reg_time_start=start_time, reg_time_finish=end_time)

        client_registrations = await RegistrationsDAO.get_by_user_id(user_id=client["user_id"], finished=True, is_sorted=True)
        is_new_client = len(client_registrations) == 0

        if is_new_client:
            if reg["advance"] == "not_required":
                event_name = dict1["payment_not_work"] + event_name

            elif reg["advance"] == "processing":
                event_name = dict1["not_advance"] + event_name

            elif reg["advance"] == "finished":
                event_name = dict1["advance"] + event_name

            event_name = dict1["new_client"] + event_name

        if reg["status"] in ["approved", "confirmation_sent"]:
            event_name = dict1[reg["status"]] + event_name
    return event_name


@async_exception_handler_decorator
async def create_event(event_name: str, event_date: dt.date, start_time: dt.time, end_time: dt.time):
    event_name = await update_event_name(event_name, event_date, start_time, end_time)
    start_time = dt.combine(event_date, start_time).isoformat()
    end_time = dt.combine(event_date, end_time).isoformat()

    event = {
        'summary': event_name,
        'start': {
            'dateTime': start_time,
            'timeZone': local_tz,
        },
        'end': {
            'dateTime': end_time,
            'timeZone': local_tz,
        },
    }

    event = calendar_service.events().insert(
        calendarId=calendar_id, body=event).execute()
    return event


@async_exception_handler_decorator
async def delete_event(event_id: int):
    calendar_service.events().delete(calendarId=calendar_id, eventId=event_id).execute()


async def delete_event_by_reg_id(reg_id: int):
    reg = await RegistrationsDAO.get_one_or_none(id=reg_id)
    event = await get_events(reg["reg_date"], reg["reg_time_start"], reg["reg_time_finish"])
    await delete_event(event[0]["id"])


async def check_interval_for_events(schedule_date, start_time, end_time, except_event_id=None, except_reg_id=None):
    events = await get_events(schedule_date, start_time, end_time)
    if except_event_id:
        events = [event for event in events if event["id"]
                  != except_event_id]
    if except_reg_id:
        reg = await RegistrationsDAO.get_one_or_none(id=except_reg_id)
        event = await get_events(reg["reg_date"], reg["reg_time_start"], reg["reg_time_finish"])
        if len(event) > 0:
            if event[0] in events:
                events.remove(event[0])
    return len(events) == 0

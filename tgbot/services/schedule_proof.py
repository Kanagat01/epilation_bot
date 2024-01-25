from datetime import datetime, timedelta
from typing import List, Literal

from tgbot.models.sql_connector import RegistrationsDAO
from tgbot.calendar_api.calendar import get_events


async def find_free_slot(events: List[tuple], duration: int, reg_date: datetime,  start_time: datetime, end_time: datetime) -> str:
    sorted_events = sorted(events, key=lambda x: x[0])

    for event in sorted_events:
        if start_time < event[0]:
            time_diff = datetime.combine(
                datetime.today(), event[0]) - datetime.combine(datetime.today(), start_time)
            if time_diff >= timedelta(minutes=duration):
                return start_time.strftime("%H:%M")  # Found a free slot
            else:
                start_time = event[1]
        elif event[0] <= start_time < event[1]:
            start_time = event[1]

    time_diff = datetime.combine(
        datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)
    if time_diff >= timedelta(minutes=duration):
        return start_time.strftime("%H:%M")  # Found a free slot

    return None  # No free slot found


async def date_slots_checker(offset: int, duration: int) -> list:
    result = []
    counter = 0
    for i in range(offset + 1, 32):
        day = datetime.today() + timedelta(days=i)
        day_events = await get_events(schedule_date=day)

        events = []
        for event in day_events:
            start_str, end_str = event["start"]["dateTime"], event["end"]["dateTime"]
            start_time = datetime.fromisoformat(start_str).time()
            end_time = datetime.fromisoformat(end_str).time()
            events.append((start_time, end_time))
        start_time = datetime.strptime("9:00", "%H:%M").time()
        end_time = datetime.strptime("22:00", "%H:%M").time()
        day_slot = await find_free_slot(
            events=events, duration=duration, reg_date=day, start_time=start_time, end_time=end_time)
        if day_slot:
            result.append(day)
            counter += 1
        if counter == 6:
            break
    return result


async def time_three_slots_checker(date: datetime, duration: int) -> list:
    result = []
    day_events = await get_events(schedule_date=date)
    events = []
    for event in day_events:
        start_str, end_str = event["start"]["dateTime"], event["end"]["dateTime"]
        start_time = datetime.fromisoformat(start_str).time()
        end_time = datetime.fromisoformat(end_str).time()
        events.append((start_time, end_time))

    for time_tuple in [("9:00", "12:00", "morning"), ("12:00", "18:00", "day"), ("18:00", "22:00", "evening")]:
        start_time = datetime.strptime(time_tuple[0], "%H:%M").time()
        if time_tuple[2] == "evening":
            end_time = datetime.strptime(time_tuple[1], "%H:%M").time()
        else:
            end_time = (datetime.strptime(
                time_tuple[1], "%H:%M") + timedelta(minutes=duration)).time()
        day_slot = await find_free_slot(
            events=events, duration=duration, reg_date=date, start_time=start_time, end_time=end_time)
        if day_slot:
            result.append(time_tuple[2])
    return result


async def one_slot_checker(date: datetime, day_part: Literal["morning", "day", "evening"], duration: int):
    slots = {
        "morning": ("9:00", "12:00"),
        "day": ("12:00", "18:00"),
        "evening": ("18:00", "22:00"),
    }
    day_events = await get_events(schedule_date=date)
    events = []
    for event in day_events:
        start_str, end_str = event["start"]["dateTime"], event["end"]["dateTime"]
        start_time = datetime.fromisoformat(start_str).time()
        end_time = datetime.fromisoformat(end_str).time()
        events.append((start_time, end_time))

    start_time = datetime.strptime(slots[day_part][0], "%H:%M").time()
    if day_part == "evening":
        end_time = datetime.strptime(slots[day_part][1], "%H:%M").time()
    else:
        end_time = (datetime.strptime(
            slots[day_part][1], "%H:%M") + timedelta(minutes=duration)).time()
    day_slot = await find_free_slot(
        events=events, duration=duration, reg_date=date, start_time=start_time, end_time=end_time)
    day_slot = datetime.strptime(day_slot, "%H:%M").time()
    return day_slot


async def check_free_slot(reg_date: datetime, reg_time: datetime, duration: int) -> str:
    day_events = await get_events(schedule_date=reg_date)
    events = []
    for event in day_events:
        start_str, end_str = event["start"]["dateTime"], event["end"]["dateTime"]
        start_time = datetime.fromisoformat(start_str).time()
        end_time = datetime.fromisoformat(end_str).time()
        events.append((start_time, end_time))

    end_time = (datetime.combine(datetime.today(), reg_time) +
                timedelta(minutes=duration)).time()
    free_slot = await find_free_slot(
        events=events, duration=duration, reg_date=reg_date, start_time=reg_time, end_time=end_time)
    return free_slot

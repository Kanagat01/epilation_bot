from datetime import datetime, timedelta
from create_bot import scheduler, bot, config
from tgbot.models.sql_connector import ClientsDAO, MailingsDAO, RegistrationsDAO, ServicesDAO, TextsDAO


admin_ids = config.tg_bot.admin_ids


class BaseScheduler:
    event_type = None

    @classmethod
    async def delete(cls, job_id: int):
        scheduler.remove_job(job_id=f"{job_id}_{cls.event_type}")


class MailingScheduler(BaseScheduler):
    event_type = "mailing"

    @classmethod
    async def func(cls, mailing_id: int):
        mailing = await MailingsDAO.get_one_or_none(id=mailing_id)
        clients = await MailingsDAO.get_clients_from_client_group(client_group=mailing["client_group"])
        for client in clients:
            if "{{ИМЯ}}" in mailing["text"]:
                text = mailing["text"].replace("{{ИМЯ}}", client["first_name"])
            else:
                text = mailing["text"]

            if mailing["photo"]:
                await bot.send_photo(chat_id=client["user_id"], photo=mailing["photo"], caption=text)
            else:
                await bot.send_message(chat_id=client["user_id"], text=text)
        await MailingsDAO.update(id=mailing_id, status="sent")

    @classmethod
    async def create(cls, mailing_id: int, dtime: datetime):
        scheduler.add_job(
            id=f"{mailing_id}_{cls.event_type}",
            func=cls.func,
            trigger="date",
            run_date=dtime,
            kwargs={
                "mailing_id": mailing_id
            }
        )


class AutoTextScheduler(BaseScheduler):
    event_type = "auto_text"

    @classmethod
    async def func(cls, auto_text: str, user_id: int):
        text_dict = await TextsDAO.get_one_or_none(chapter=f"text|{auto_text}")
        photo_dict = await TextsDAO.get_one_or_none(chapter=f"photo|{auto_text}")

        text = text_dict["text"] if text_dict else None
        if text_dict and "{{ИМЯ}}" in text_dict["text"]:
            client = await ClientsDAO.get_one_or_none(user_id=user_id)
            text = text.replace(
                "{{ИМЯ}}", client["first_name"])

        if photo_dict:
            await bot.send_photo(chat_id=user_id, photo=photo_dict["text"], caption=text)
        elif text:
            await bot.send_message(chat_id=user_id, text=text)

    @classmethod
    async def create(cls, auto_text: str, user_id: int, dtime: datetime):
        scheduler.add_job(
            id=f"{dtime.strftime('%d.%m.%Y %H:%M:%S')}_{auto_text}_{user_id}",
            func=cls.func,
            trigger="date",
            run_date=dtime,
            kwargs={
                "auto_text": auto_text,
                "user_id": user_id
            }
        )


class HolidayScheduler(BaseScheduler):
    event_type = "holiday"

    @classmethod
    async def func(cls, auto_text: str):
        text_dict = await TextsDAO.get_one_or_none(chapter=f"text|{auto_text}")
        photo_dict = await TextsDAO.get_one_or_none(chapter=f"photo|{auto_text}")

        if auto_text in ["new_year", "23_february", "8_march"]:
            clients = await ClientsDAO.get_many()

        elif auto_text == "1week_before_birthday":
            birthday = (datetime.today() + timedelta(days=7)).date()
            clients = await ClientsDAO.get_birthday_people(birth_date=birthday)

        elif auto_text == "at_birthday":
            clients = await ClientsDAO.get_birthday_people(birth_date=datetime.today().date())

        for client in clients:
            text = text_dict["text"] if text_dict else None
            if text and "{{ИМЯ}}" in text:
                text = text.replace("{{ИМЯ}}", client["first_name"])

            if photo_dict:
                await bot.send_photo(chat_id=client["user_id"], photo=photo_dict["text"], caption=text)
            elif text:
                await bot.send_message(chat_id=client["user_id"], text=text)

        dtime = datetime.today()
        dtime = dtime.replace(year=dtime.year + 1)
        await HolidayScheduler.create(auto_text, dtime)

    @classmethod
    async def create(cls, auto_text: str, dtime: datetime):
        job_id = f"{auto_text}_{cls.event_type}_{dtime.strftime('%d.%m.%Y %H:%M:%S')}"

        if not scheduler.get_job(job_id):
            scheduler.add_job(
                id=job_id,
                func=cls.func,
                trigger="date",
                run_date=dtime,
                kwargs={
                    "auto_text": auto_text
                }
            )


async def create_auto_texts(reg_id: int, user_id: str | int):
    auto_texts = await get_auto_texts_list_for_registration(
        reg_id=reg_id)
    for auto_text, dtime in auto_texts:
        if dtime > datetime.now():
            await AutoTextScheduler.create(auto_text, user_id, dtime)
        else:
            await AutoTextScheduler.func(auto_text, user_id)


async def delete_auto_texts(reg_id: int, user_id: int | str):
    auto_texts = await get_auto_texts_list_for_registration(reg_id=reg_id)
    for auto_text, dtime in auto_texts:
        if dtime > datetime.now():
            scheduler.remove_job(
                f"{dtime.strftime('%d.%m.%Y %H:%M:%S')}_{auto_text}_{user_id}")


async def get_auto_texts_list_for_registration(reg_id: int):
    reg = await RegistrationsDAO.get_one_or_none(id=reg_id)
    user_id = str(reg['user_id'])
    reg_start = datetime.combine(reg["reg_date"], reg["reg_time_start"])
    reg_finish = datetime.combine(reg["reg_date"], reg["reg_time_finish"])
    auto_texts = [
        ("before_2h", reg_start - timedelta(hours=2)),
        ("after_5h", reg_finish + timedelta(hours=5)),
        ("after_1m", reg_finish + timedelta(days=30)),
        ("after_3m", reg_finish + timedelta(days=90))
    ]

    finished_regs = await RegistrationsDAO.get_many(user_id=user_id, status="finished")
    auto_texts.append(
        (f"before_24h_{'old' if len(finished_regs) > 0 else 'new'}", reg_start - timedelta(days=1)))

    service = await ServicesDAO.get_one_or_none(id=reg["services"][0])
    auto_texts.append(
        (f"after_3h_{'laser' if service['category'] == 'laser' else 'bio'}", reg_finish + timedelta(hours=3)))

    return auto_texts

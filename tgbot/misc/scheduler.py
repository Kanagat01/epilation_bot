from datetime import datetime, timedelta
from create_bot import scheduler, bot, config
from tgbot.models.sql_connector import ClientsDAO, MailingsDAO, TextsDAO


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
        if text_dict:
            text = text_dict["text"]
            if "{{ИМЯ}}" in text_dict["text"]:
                client = await ClientsDAO.get_one_or_none(user_id=user_id)
                text = text.replace(
                    "{{ИМЯ}}", client["first_name"])
            await bot.send_message(chat_id=user_id, text=text)

    @classmethod
    async def create(cls, auto_text: str, user_id: int, dtime: datetime):
        scheduler.add_job(
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

        if text_dict:
            if auto_text in ["new_year", "23_february", "8_march"]:
                clients = await ClientsDAO.get_many()

            elif auto_text == "1week_before_birthday":
                birthday = (datetime.today() + timedelta(days=7)).date()
                clients = await ClientsDAO.get_many(birthday=birthday)

            elif auto_text == "at_birthday":
                clients = await ClientsDAO.get_many(birthday=datetime.today().date())

            for client in clients:
                if "{{ИМЯ}}" in text_dict["text"]:
                    text = text_dict["text"].replace(
                        "{{ИМЯ}}", client["first_name"])
                else:
                    text = text_dict["text"]
                await bot.send_message(chat_id=client["user_id"], text=text)

        dtime = datetime.today()
        dtime = dtime.replace(year=dtime.year + 1)
        await HolidayScheduler.create(auto_text, dtime)

    @classmethod
    async def create(cls, auto_text: str, dtime: datetime):
        if "birthday" in auto_text:
            prev_text = auto_text + dtime.strftime("%d.%m.%Y")
        else:
            prev_text = auto_text

        scheduler.add_job(
            id=f"{prev_text}_{cls.event_type}_{dtime.strftime('%d.%m.%Y %H:%M:%S')}",
            func=cls.func,
            trigger="date",
            run_date=dtime,
            kwargs={
                "auto_text": auto_text
            }
        )

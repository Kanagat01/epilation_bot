from datetime import datetime, timedelta

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from create_bot import scheduler, bot, config, dp
from tgbot.handlers.user.registration_block import UserMainMenu
from tgbot.keyboards.inline import UserSignUpInline
from tgbot.models.sql_connector import ClientsDAO, MailingsDAO, TextsDAO, RegistrationsDAO


admin_ids = config.tg_bot.admin_ids


class BaseScheduler:
    event_type = None

    @classmethod
    async def delete(cls, job_id: int):
        scheduler.remove_job(job_id=f"{job_id}_{cls.event_type}")


class PayRegistration2HoursScheduler(BaseScheduler):
    event_type = "reg2hours"

    @classmethod
    async def func(cls, user_id: str | int, reg_id: int):
        reg = await RegistrationsDAO.get_one_or_none(id=reg_id, advance="processing")
        if reg:
            text = 'К сожалению, не удалось подтвердить оплату.\nЕсли вы уверены, что оплата прошла, то пожалуйста срочно ' \
                'свяжитесь с Оксаной. Либо нажмите "Написать Оксане", либо позвоните по номеру +79117737477.\nЕсли вы ' \
                'передумали, то прошу нажать "Отменить запись ❌" или запись через 1 час отменится автоматически.'
            kb = UserSignUpInline.pay_advance_kb(reg_id=reg_id)
            await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)
            await PayRegistration1HourScheduler.create(user_id=user_id)

    @classmethod
    async def create(cls, user_id: str | int, reg_id: int):
        dtime = datetime.utcnow() + timedelta(hours=2)
        scheduler.add_job(
            id=f"{reg_id}_{cls.event_type}",
            func=cls.func,
            trigger="date",
            run_date=dtime,
            kwargs={
                "user_id": user_id,
                "reg_id": reg_id
            }
        )


class PayRegistration1HourScheduler(BaseScheduler):
    event_type = "reg1hour"

    @classmethod
    async def func(cls, user_id: str | int, reg_id: int):
        reg = await RegistrationsDAO.get_one_or_none(id=reg_id, advance="processing")
        if reg:
            state_with: FSMContext = FSMContext(
                bot=bot,
                storage=dp.storage,
                key=StorageKey(
                    chat_id=user_id,
                    user_id=user_id,
                    bot_id=bot.id
                )
            )
            state = await state_with.get_state()
            await UserMainMenu.menu_type(user_id, state)

    @classmethod
    async def create(cls, user_id: str | int, reg_id: int):
        dtime = datetime.utcnow() + timedelta(hours=1)
        scheduler.add_job(
            id=f"{reg_id}_{cls.event_type}",
            func=cls.func,
            trigger="date",
            run_date=dtime,
            kwargs={
                "user_id": user_id,
                "reg_id": reg_id
            }
        )


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
            if "{{ИМЯ}}" in text_dict["text"]:
                client = await ClientsDAO.get_one_or_none(user_id=user_id)
                text = text_dict["text"].replace(
                    "{{ИМЯ}}", client["first_name"])
            else:
                text = text_dict["text"]
            await bot.send_message(chat_id=user_id, text=text)

    @classmethod
    async def create(cls, auto_text: str, user_id: int, dtime: datetime):
        scheduler.add_job(
            id=f"{user_id}_{auto_text}_{cls.event_type}_{dtime.strftime('%d.%m.%Y %H:%M:%S')}",
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

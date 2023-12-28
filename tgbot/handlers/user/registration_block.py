from datetime import datetime

from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram import F, Router
from aiogram.fsm.context import FSMContext

from create_bot import bot, config
from tgbot.keyboards.inline import UserInlineKeyboard as inline_kb
from tgbot.keyboards.reply import UserReplyKeyboard as reply_kb
from tgbot.misc.states import UserFSM
from tgbot.models.sql_connector import ClientsDAO, RegistrationsDAO

router = Router()

admin_id = config.tg_bot.admin_ids[0]


class UserMainMenu:

    @staticmethod
    async def new_clients_menu(user_id: str | int, name: str):
        text = f"🌼Добро пожаловать, {name}!\nПознакомимся?🤗\nМеня зовут Оксана, буду рада стать вашим мастером " \
               f"эпиляции.\nЗдесь вы узнаете обо мне и эпиляции больше, также я помогу Вам записаться.\nВыберите, " \
               f"пожалуйста, с чего начнем❓"
        kb = reply_kb.new_menu_kb()
        await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)

    @staticmethod
    async def current_clients_menu(user_id: str | int, name: str):
        text = f"Приветики, {name}!\n😊Рада Вас видеть в моем боте!\nЗдесь Вы можете в несколько кликов " \
               f"записаться на повторный прием ✅"
        kb = reply_kb.current_menu_kb()
        await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)

    @classmethod
    async def menu_type(cls, user_id: str, state: FSMContext):
        user = await ClientsDAO.get_one_or_none(user_id=user_id)
        name = user["full_name"] if user else ""
        if user:
            finished_registrations = await RegistrationsDAO.get_many(user_id=user_id, status="finished")
            if len(finished_registrations) > 0:
                await cls.current_clients_menu(user_id=user_id, name=name)
            else:
                await cls.new_clients_menu(user_id=user_id, name=name)
        else:
            await cls.new_clients_menu(user_id=user_id, name=name)
        await state.set_state(UserFSM.main_menu)


@router.message(Command("start"))
async def user_start(message: Message, command: CommandObject, state: FSMContext):
    user = await ClientsDAO.get_one_or_none(user_id=str(message.from_user.id))
    if user:
        await UserMainMenu.menu_type(
            user_id=str(message.from_user.id),
            state=state
        )
        return
    arg = command.args
    if arg == "office":
        text = "🌼Добро пожаловать!\nНажмите, пожалуйста, на кнопку 🤗\nПосле необходимо будет ввести ФИ, " \
               "номер телефона и дату рождения.\nВсе данные собираются единожды! Бот запомнит вас  😍\nВ последующем " \
               "вы сможете записываться в несколько кликов 💚"
        kb = reply_kb.start_kb(is_office=True)
        await state.update_data(entry_point="office")
    else:  # world
        text = "Приветики! Нажмите старт, что бы мы смогли начать  🤩"
        kb = reply_kb.start_kb(is_office=False)
        await state.update_data(entry_point="world")
    await state.set_state(UserFSM.home)
    await message.answer(text, reply_markup=kb)


###############
#  Регистрация из внешнего мира


@router.message(F.contact, UserFSM.home)
async def phone_record(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    user = await ClientsDAO.get_one_or_none(phone=phone)
    name = user["full_name"] if user else ""
    username = f"@{message.from_user.username}" if message.from_user.username else ""
    state_data = await state.get_data()
    await ClientsDAO.create(
        user_id=str(message.from_user.id),
        username=username,
        phone=phone,
        full_name=name,
        gender="unknown",
        entry_point=state_data["entry_point"]
    )
    await UserMainMenu.menu_type(user_id=str(message.contact.user_id), state=state)


###############
#  Регистрация из офиса


@router.message(F.text, UserFSM.home)
async def phone_record(message: Message, state: FSMContext):
    text = "Пожалуйста введите ваш номер телефона.\nОн нужен для последующих онлайн-записей.\nФормат: +79117737477"
    await state.set_state(UserFSM.manual_phone)
    await message.answer(text)


@router.message(F.text, UserFSM.manual_phone)
async def phone_record(message: Message, state: FSMContext):
    if len(message.text) == 12 and message.text[0:3] == "+79":
        user = await ClientsDAO.get_one_or_none(phone=message.text)
        if user:
            text = "Этот номер телефона уже есть в списке клиентов. Пожалуйста напишите Оксане в личку, чтобы она " \
                   "связала ваш номер телефона с этим ботом. Это позволит записываться 📝онлайн и получать важные " \
                   "уведомления 💌"
            kb = inline_kb.phone_in_base_kb(phone=message.text)
        else:
            text = "Напишите, пожалуйста, свою Фамилию и Имя.\nФормат: Иванова Светлана"
            kb = None
            await state.set_state(UserFSM.full_name_reg)
            await state.update_data(phone=message.text)
    else:
        text = "К сожалению, не удалось введённое сообщение определить как номер телефона. Пожалуйста, напишите " \
               "телефон в формате +79ххххххххх"
        kb = None
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "msg_to_admin")
async def msg_to_admin(callback: CallbackQuery):
    phone = callback.data.split(":")[1]
    user = await ClientsDAO.get_one_or_none(phone=phone)
    cur_username = f"@{callback.from_user.username}" if callback.from_user.username else ""
    admin_text = f"Пользователь {cur_username} указал номер телефона {phone}, но он уже есть в базе у " \
                 f"клиента {user['username']}. Нужно связаться с ним и убедиться, что это он и подтвердить телефон."
    admin_kb = inline_kb.answer_to_user_kb(user_id=callback.from_user.id)
    user_text = "Уведомление отправлено. Оксана с вами свяжется."
    user_kb = inline_kb.msg_to_admin_kb()
    await bot.send_message(chat_id=admin_id, text=admin_text, reply_markup=admin_kb)
    await callback.message.answer(user_text, reply_markup=user_kb)
    await bot.answer_callback_query(callback.id)


@router.callback_query(F.data == "correct_phone")
async def correct_phone(callback: CallbackQuery, state: FSMContext):
    text = "Пожалуйста, напишите телефон в формате +79ххххххххх"
    await state.set_state(UserFSM.manual_phone)
    await callback.message.answer(text)
    await bot.answer_callback_query(callback.id)


@router.message(F.text, UserFSM.full_name_reg)
async def get_full_name(message: Message, state: FSMContext):
    text = "Выберите пол:"
    kb = inline_kb.user_gender_kb()
    await state.update_data(full_name=message.text)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "user_gender")
async def get_user_gender(callback: CallbackQuery, state: FSMContext):
    text = "Введите вашу дату рождения. Эти данные позволят мне присылать  вам бонусы в виде поздравления 🎁\nФормат: " \
           "01.01.1980"
    kb = inline_kb.user_birthday_kb()
    await state.update_data(gender=callback.data.split(":")[1])
    await state.set_state(UserFSM.birthday_reg)
    await callback.message.answer(text, reply_markup=kb)
    await bot.answer_callback_query(callback.id)


@router.message(F.text, UserFSM.birthday_reg)
async def get_user_birthday(message: Message, state: FSMContext):
    try:
        birthday = datetime.strptime(message.text, "%d.%m.%Y")
        username = f"@{message.from_user.username}" if message.from_user.username else ""
        state_data = await state.get_data()
        await ClientsDAO.create(
            user_id=str(message.from_user.id),
            full_name=state_data["full_name"],
            username=username,
            phone=state_data["phone"],
            gender=state_data["gender"],
            birthday=birthday,
            entry_point=state_data["entry_point"]
        )
        await UserMainMenu.menu_type(user_id=str(message.from_user.id), state=state)
    except ValueError:
        text = "К сожалению, не удалось введённое сообщение определить как дату рождения. Пожалуйста, напишите дату " \
               "рождения в формате: 07.02.1990"
        kb = inline_kb.user_birthday_kb()
        await state.set_state(UserFSM.birthday_reg)
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "main_menu")
async def main_menu_clb(callback: CallbackQuery, state: FSMContext):
    username = f"@{callback.from_user.username}" if callback.from_user.username else ""
    state_data = await state.get_data()
    birthday = datetime.strptime("01.01.1900", "%d.%m.%Y")
    await ClientsDAO.create(
        user_id=str(callback.from_user.id),
        full_name=state_data["full_name"],
        username=username,
        phone=state_data["phone"],
        gender=state_data["gender"],
        birthday=birthday,
        entry_point=state_data["entry_point"]
    )
    await UserMainMenu.menu_type(
        user_id=str(callback.from_user.id),
        state=state
    )
    await bot.answer_callback_query(callback.id)

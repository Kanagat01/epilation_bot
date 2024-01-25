from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from tgbot.filters.admin import AdminFilter
from tgbot.models.sql_connector import RegistrationsDAO, ClientsDAO, ServicesDAO, category_translation, status_translation
from tgbot.keyboards.inline import AdminInlineKeyboard as inline_kb
from tgbot.misc.states import AdminFSM

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


async def necessary_routine_text_and_kb():
    regs = await RegistrationsDAO.get_many_created()
    registrations = []
    full_names = []
    if len(regs) > 0:
        for x in regs:
            reg_date = x['reg_date']
            reg_time_start = x['reg_time_start']
            user = await ClientsDAO.get_one_or_none(user_id=x["user_id"])
            full_name = f'{user["first_name"]} {user["last_name"]}'
            full_names.append(full_name)
            registrations.append(f"{reg_date} {reg_time_start} {full_name}")

        text = [
            "События, требуемые ваших действий.\n",
            "Записи, в которых нужно отметить факт приема:\n",
            "\n".join(registrations),
            "\nНажмите на запись для проставления отметки по ней:"
        ]
    else:
        text = [
            "Записей, в которых нужно отметить факт приема, нет"
        ]
    kb = inline_kb.necessary_routine_kb(regs, full_names)
    return text, kb


@router.callback_query(F.data == "necessary_routine")
async def necessary_routine(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text, kb = await necessary_routine_text_and_kb()
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "registration")
async def check_registraion(callback: CallbackQuery, state: FSMContext):
    _, reg_id, full_name = callback.data.split(":")
    reg_id = int(reg_id)
    registration = await RegistrationsDAO.get_one_or_none(id=reg_id)
    reg_date = registration["reg_date"]
    reg_time_start = registration["reg_time_start"]
    text = [
        "<s><b>Выбрана запись</b></s>",
        f"<s><b>Запись #{reg_id} {reg_date} {reg_time_start} {full_name}</b></s>\n",
        "Если клиент не пришел, то нажмите соответствующую кнопку. Если",
        "клиент пришел - напишите цену, которую заплатил клиент. Без",
        'пробелов, знаков "р" и др, например "5000".',
    ]
    text = "\n".join(text)
    kb = inline_kb.check_registration_kb(reg_id, full_name)
    await state.set_state(AdminFSM.routine_reg_price)
    await state.update_data({"registration": registration, "full_name": full_name})
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.split(":")[0] == "no_show")
async def no_show(callback: CallbackQuery):
    reg_id = int(callback.data.split(":")[1])
    full_name = callback.data.split(":")[2]
    registration = await RegistrationsDAO.get_one_or_none(id=reg_id)
    reg_date = registration["reg_date"]
    reg_time_start = registration["reg_time_start"]

    await RegistrationsDAO.update(reg_id=reg_id, status="no_show")
    text = [
        "Для записи",
        f"#{reg_id} {reg_date} {reg_time_start} {full_name}",
        'проставлена отметка "Не пришёл".'
    ]
    await callback.message.answer("\n".join(text))

    text, kb = await necessary_routine_text_and_kb()
    await callback.message.answer("\n".join(text), reply_markup=kb)


@router.message(AdminFSM.routine_reg_price)
async def set_registration_price(message: Message, state: FSMContext):
    state_data = await state.get_data()
    registration = state_data["registration"]
    reg_id = registration["id"]
    status = registration["status"]
    reg_date = registration["reg_date"]
    reg_time_start = registration["reg_time_start"]

    services_text = []
    duration = 0
    category = None
    for service_id in registration["services"]:
        service = await ServicesDAO.get_one_or_none(id=service_id)
        if not category:
            category = category_translation(service["category"])
        duration += service["duration"]
        services_text.append(service["title"])

    services_text = "\n".join(services_text)
    full_name = state_data["full_name"]
    if message.text.isdigit():
        total_price = int(message.text)
        client = await ClientsDAO.get_one_or_none(user_id=registration["user_id"])
        client_duration = client['service_duration']
        await RegistrationsDAO.update(reg_id=reg_id, total_price=total_price, status="finished")
        await state.set_state(AdminFSM.routine_reg_time)
        text = [
            'Для записи',
            f'#{reg_id} {reg_date} {reg_time_start} {full_name}',
            f'Статус: {status_translation(status)}.',
            f'Оплачено: {total_price}.',
            'Процедуры:',
            f'Тип "{category}"',
            f"Перечень: {services_text}.",
            f"Время на приём (авто): {duration} минут.",
            f"Время на приём (вручную): {client_duration} минут.",
            "Напишите время на приём для повторов приёма (число в",
            'минутах) или нажмите кнопку "Назад к списку действий".'
        ]
        kb = inline_kb.back_to_routine()
        await message.answer("\n".join(text), reply_markup=kb)

    else:
        text = [
            "<s><b>Выбрана запись</b></s>",
            f"<s><b>#{reg_id} {reg_date} {reg_time_start} {full_name}</b></s>\n",
            "Если клиент не пришел, то нажмите соответствующую кнопку. Если",
            "клиент пришел - напишите цену, которую заплатил клиент. Без",
            'пробелов, знаков "р" и др, например "5000".',
        ]
        text = "\n".join(text)
        kb = inline_kb.check_registration_kb(reg_id, full_name)
        await message.answer(text, reply_markup=kb)


@router.message(AdminFSM.routine_reg_time)
async def set_registration_time(message: Message, state: FSMContext):
    state_date = await state.get_data()
    if message.text.isdigit():
        registration = state_date["registration"]
        await ClientsDAO.update(user_id=registration["user_id"], service_duration=int(message.text))
        text = [
            "Для клиента",
            f"Было проставлено время приема: {message.text} минут"
        ]
        await message.answer("\n".join(text))
        await state.clear()
        text, kb = await necessary_routine_text_and_kb()
        await message.answer("\n".join(text), reply_markup=kb)
    else:
        text = [
            "Напишите время на приём для повторов приёма (число в",
            'минутах) или нажмите кнопку "Назад к списку действий".'
        ]
        kb = inline_kb.back_to_routine()
        await message.answer("\n".join(text), reply_markup=kb)

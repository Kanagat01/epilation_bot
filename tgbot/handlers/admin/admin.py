from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command
from aiogram import Router, F
from aiogram.utils.markdown import hcode

from tgbot.filters.admin import AdminFilter
from tgbot.handlers.admin.mass_message import mass_message_text_and_kb
from tgbot.handlers.admin.necessary_routine import necessary_routine_text_and_kb
from tgbot.handlers.admin.schedule_block import schedule_text_and_kb
from tgbot.keyboards.reply import AdminReplyKeyboard as reply_kb
from tgbot.keyboards.inline import AdminInlineKeyboard as inline_kb
from tgbot.misc.states import AdminFSM


router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.message(F.sticker)
async def sticker(message: Message):
    await message.answer(f"sticker_id: {hcode(message.sticker.file_id)}")


@router.message(Command("start"))
async def admin_start(message: Message, state: FSMContext):
    text = "Выберите категорию:"
    kb = reply_kb.main_menu_kb()
    await state.set_state(AdminFSM.home)
    await message.answer(text, reply_markup=kb)


@router.message(F.text == "Необходимая рутина")
async def necessary_routine(message: Message, state: FSMContext):
    await state.clear()
    text, kb = await necessary_routine_text_and_kb()
    await message.answer("\n".join(text), reply_markup=kb)


@router.message(F.text == "Управлять контентом")
async def content_management(message: Message, state: FSMContext):
    await state.clear()
    text = 'Раздел "Управление контентом".\nВыберите, что вы хотите сделать:'
    kb = inline_kb.content_management_kb()
    await message.answer(text, reply_markup=kb)


@router.message(F.text == "Расписание")
async def schedule(message: Message, state: FSMContext):
    await state.clear()
    text, kb = schedule_text_and_kb()
    await state.set_state(AdminFSM.schedule_date)
    await message.answer("\n".join(text), reply_markup=kb)


@router.message(F.text == "Клиенты")
async def clients(message: Message, state: FSMContext):
    await state.clear()
    text = [
        "Введите ФИО или номер телефона (формат +79871234567)",
        'клиента. Или нажмите кнопку "Все клиенты"'
    ]
    kb = inline_kb.all_clients_btn_kb()
    await state.set_state(AdminFSM.find_client)
    await message.answer("\n".join(text), reply_markup=kb)


@router.message(F.text == "Массовое сообщение")
async def mass_message(message: Message, state: FSMContext):
    await state.clear()
    text, kb = await mass_message_text_and_kb()
    await message.answer("\n".join(text), reply_markup=kb)

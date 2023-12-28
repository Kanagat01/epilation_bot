from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


class AdminReplyKeyboard:
    """Клавиатура админа (реплай)"""

    @classmethod
    def main_menu_kb(cls):
        kb = [
            [KeyboardButton(text="Необходимая рутина")],
            [KeyboardButton(text="Управлять контентом")],
            [KeyboardButton(text="Расписание")],
            [KeyboardButton(text="Клиенты")],
            [KeyboardButton(text="Массовое сообщение")],
        ]
        keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=False)
        return keyboard


class UserReplyKeyboard:
    """Клавиатура юзера для передачи телефона"""

    @classmethod
    def start_kb(cls, is_office):
        if is_office:
            kb = [[KeyboardButton(text="Старт")]]
        else:
            kb = [[KeyboardButton(text="Старт", request_contact=True)]]
        return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

    @classmethod
    def new_menu_kb(cls):
        kb = [
            [
                KeyboardButton(text="Записаться с бонусом 🎁"),
                KeyboardButton(text="Адрес"),
            ],
            [
                KeyboardButton(text="Обо мне и отзывы"),
                KeyboardButton(text="Прайс"),
            ],
            [KeyboardButton(text="Коротко о видах эпиляции")],
            [KeyboardButton(text="Написать Оксане в личку")],
        ]
        keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=False)
        return keyboard

    @classmethod
    def current_menu_kb(cls):
        kb = [
            [KeyboardButton(text="Записаться / Информация о ближайшей записи")],
            [
                KeyboardButton(text="Написать отзыв"),
                KeyboardButton(text="Прайс"),
            ],
            [KeyboardButton(text="Написать Оксане в личку")],
        ]
        keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=False)
        return keyboard

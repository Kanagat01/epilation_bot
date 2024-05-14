from datetime import datetime
from typing import Literal, List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class AdminInlineKeyboard:
    """Клавиатура админа"""

    @classmethod
    def content_management_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Изменить тексты автоматических рассылок", callback_data='edit_auto_texts')],
            [InlineKeyboardButton(text="Изменить цены услуг",
                                  callback_data='edit_prices')],
            [InlineKeyboardButton(
                text="Изменить информационные блоки", callback_data='edit_info_blocks')],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_auto_texts_kb(cls):
        kb_data = [
            {"kb_title": "На Новый год", "clb_data": "new_year"},
            {"kb_title": "На 23 февраля", "clb_data": "23_february"},
            {"kb_title": "На 8 марта", "clb_data": "8_march"},
            {"kb_title": "На день рождения - за неделю",
                "clb_data": "1week_before_birthday"},
            {"kb_title": "На день рождения - в день рождения",
                "clb_data": "at_birthday"},
            {"kb_title": "За 24 часа до приёма - новым клиентам",
                "clb_data": "before_24h_new"},
            {"kb_title": "За 24 часа до приёма - текущим клиентам",
                "clb_data": "before_24h_old"},
            {"kb_title": "За 2 часа до приёма", "clb_data": "before_2h"},
            {"kb_title": "После первого приёма", "clb_data": "first_finished_reg"},
            {"kb_title": "Через 3 часа после процедуры - Био",
                "clb_data": "after_3h_bio"},
            {"kb_title": "Через 3 часа после процедуры - Лазер",
                "clb_data": "after_3h_laser"},
            {"kb_title": "Через 3+2 часа после процедуры", "clb_data": "after_5h"},
            {"kb_title": "Через 1 месяц после приёма", "clb_data": "after_1m"},
            {"kb_title": "Через 3 месяца после приёма", "clb_data": "after_3m"},
        ]
        keyboard = []
        for button in kb_data:
            keyboard.append([InlineKeyboardButton(text=button["kb_title"],
                                                  callback_data=f"auto_text:{button['clb_data']}")])
        keyboard.append([InlineKeyboardButton(
            text="⬅️ Назад", callback_data="content_management")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def epil_gender_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Биоэпиляция - девушки", callback_data="epil_gender:bio|girls")],
            [InlineKeyboardButton(
                text="Биоэпиляция - мужчины", callback_data="epil_gender:bio|boys")],
            [InlineKeyboardButton(
                text="Лазерная эпиляция - девушки", callback_data="epil_gender:laser|girls")],
            [InlineKeyboardButton(
                text="Лазерная эпиляция - мужчины", callback_data="epil_gender:laser|boys")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="content_management")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def services_kb(cls, services: list, category: str, gender: str):
        keyboard = []
        for service in services:
            enable_dict = {"enabled": "", "disabled": "🚫"}
            category_dict = {"bio": "Био", "laser": "Лазер"}
            gender_dict = {"boys": "Мужчины", "girls": "Девушки"}
            duration_int = service["duration"]
            duration_str = f"{duration_int // 60}ч {duration_int % 60}мин"
            text_button = f"{enable_dict[service['status']]} {service['ordering']} {gender_dict[gender]} - " \
                          f"{category_dict[category]} - {service['title']} - {service['price']}₽ - {duration_str}"
            keyboard.append([InlineKeyboardButton(
                text=text_button, callback_data=f"service_profile:{service['id']}")])
        keyboard.append([InlineKeyboardButton(text="🆕 Создать услугу",
                                              callback_data=f"new_service:{category}|{gender}")])
        keyboard.append([InlineKeyboardButton(
            text="⬅️ Назад", callback_data="edit_prices")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_service_kb(cls, service_id: int, status: str, gender: str, category: str):
        status_dict = {"enabled": "🚫 Скрыть", "disabled": "Показать"}
        keyboard = [
            [
                InlineKeyboardButton(
                    text="📄 Название", callback_data=f"edit_service:{service_id}|title"),
                InlineKeyboardButton(
                    text="💰 Цена", callback_data=f"edit_service:{service_id}|price"),
            ],
            [
                InlineKeyboardButton(
                    text="⏳ Длительность", callback_data=f"edit_service:{service_id}|duration"),
                InlineKeyboardButton(
                    text="↗️ Порядок в списке", callback_data=f"edit_service:{service_id}|ordering"),
            ],
            [InlineKeyboardButton(text=status_dict[status],
                                  callback_data=f"edit_service_status:{service_id}|{status_dict[status]}")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"epil_gender:{category}|{gender}")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_info_block_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Адрес", callback_data="edit_info_block:address"),
                InlineKeyboardButton(
                    text="Обо мне", callback_data="edit_info_block:about_me"),
            ],
            [
                InlineKeyboardButton(
                    text="Отзывы", callback_data="edit_feedbacks"),
                InlineKeyboardButton(
                    text="Прайс лист", callback_data="edit_info_block:price_list"),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="content_management"),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_address_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Видео 1", callback_data="edit_address:video_1")],
            [InlineKeyboardButton(
                text="Видео 2", callback_data="edit_address:video_2")],
            [InlineKeyboardButton(
                text="Геометка", callback_data="edit_address:location")],
            [InlineKeyboardButton(text='Текст "Адрес"',
                                  callback_data="edit_address:text")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="edit_info_blocks")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_about_me_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Приветственное видео", callback_data="edit_about_me:video")],
            [InlineKeyboardButton(text="Фото мастера",
                                  callback_data="edit_about_me:photo")],
            [InlineKeyboardButton(text='Текст "Обо мне"',
                                  callback_data="edit_about_me:text")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="edit_info_blocks")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_feedbacks_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Девушки - Био", callback_data="edit_feedbacks:feedback_girls_bio:1")],
            [InlineKeyboardButton(
                text="Девушки - Лазер", callback_data="edit_feedbacks:feedback_girls_laser:1")],
            [InlineKeyboardButton(
                text="Мужчины", callback_data="edit_feedbacks:feedback_boys:1")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="edit_info_blocks")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_feedbacks_category_kb(cls, page: int, category: str, file_list: list, next_page: int):
        keyboard = []
        if file_list != []:
            def create_button(x, file_list, page):
                return InlineKeyboardButton(
                    text=x,
                    callback_data=f"edit_feedback:{file_list[x-1]['id']}"
                )

            def create_buttons(start, end, file_list, page):
                return [create_button(x, file_list, page) for x in range(start, end)]

            if len(file_list) >= 8:
                mid = len(file_list) // 2 + 1
                first = create_buttons(1, mid, file_list, page)
                second = create_buttons(
                    mid, len(file_list) + 1, file_list, page)
                keyboard.extend([first, second])
            else:
                pages = create_buttons(1, len(file_list) + 1, file_list, page)
                keyboard.append(pages)

        if page - 1 > 0 or next_page != 0:
            pagination = []
            if page - 1 > 0:
                pagination.append(
                    InlineKeyboardButton(
                        text="⬅️", callback_data=f"edit_feedbacks:{category}:{page-1}")
                )
            if next_page != 0:
                pagination.append(
                    InlineKeyboardButton(
                        text="➡️", callback_data=f"edit_feedbacks:{category}:{next_page}")
                )
            keyboard.append(pagination)

        keyboard.append([
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"edit_feedbacks"),
            InlineKeyboardButton(
                text="🆕 Добавить отзыв", callback_data=f"create_feedback:{category}"),
        ])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_feedback_kb(cls, id: int, category: str, content_type: str, page: int):
        keyboard = [
            [
                InlineKeyboardButton(
                    text=f"Изменить {content_type}", callback_data=f"change_feedback_media:{id}"),
                InlineKeyboardButton(
                    text="Изменить порядок", callback_data=f"change_feedback_order:{id}"),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"edit_feedbacks:{category}:{page}"),
                InlineKeyboardButton(
                    text="❌ Удалить", callback_data=f"delete_feedback:{id}"),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_price_list_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Картинка для новых клиентов", callback_data="edit_price:new_clients")],
            [InlineKeyboardButton(
                text="Картинка-прайс - Био - Мужчины", callback_data="edit_price:bio_boys")],
            [InlineKeyboardButton(
                text="Картинка-прайс - Био - Девушки", callback_data="edit_price:bio_girls")],
            [InlineKeyboardButton(
                text="Картинка-прайс - Лазер - Мужчины", callback_data="edit_price:laser_boys")],
            [InlineKeyboardButton(
                text="Картинка-прайс - Лазер - Девушки", callback_data="edit_price:laser_girls")],
            [InlineKeyboardButton(text="Картинка-прайс - Био - Абонементы",
                                  callback_data="edit_price:bio_abonements")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="edit_info_blocks")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def necessary_routine_kb(cls, registrations: list, full_names: list):
        def inline_btn(full_name, reg_id):
            return InlineKeyboardButton(
                text=full_name, callback_data=f"registration:{reg_id}:{full_name}")

        keyboard = []
        for i in range(0, len(registrations) - 1, 2):
            reg_id1 = registrations[i]["id"]
            reg_id2 = registrations[i+1]["id"]
            keyboard.append([
                inline_btn(full_names[i], reg_id1),
                inline_btn(full_names[i+1], reg_id2)
            ])
        if len(registrations) % 2 == 1:
            full_name = full_names[len(registrations)-1]
            reg_id = registrations[len(registrations)-1]["id"]
            keyboard.append([
                inline_btn(full_name, reg_id)
            ])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def check_registration_kb(cls, reg_id: int, full_name: str):
        keyboard = [
            [InlineKeyboardButton(
                text="Клиент не пришел", callback_data=f"no_show:{reg_id}:{full_name}")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="necessary_routine")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def back_to_routine(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="⬅️ Назад к списку действий", callback_data="necessary_routine")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def all_clients_btn_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Все клиенты", callback_data="all_clients")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def clients_kb(cls, page: int, prev_ten=False, next_ten=False):
        keyboard = [
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="clients")
            ],
            [
                InlineKeyboardButton(
                    text="Выгрузить в CSV (min)", callback_data="export_to_csv_min"),
                InlineKeyboardButton(
                    text="Выгрузить в CSV (max)", callback_data="export_to_csv_max"),
            ]
        ]
        if prev_ten:
            keyboard[0][0] = InlineKeyboardButton(
                text="Предыдущие 10", callback_data=f"prev:{page-1}")
        if next_ten:
            keyboard[0].append(
                InlineKeyboardButton(text="Следующие 10",
                                     callback_data=f"next:{page+1}")
            )
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def client_kb(cls, client_id: int, page: int, have_regs: bool, prev: bool, next: bool):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="all_clients")
            ],
            [
                InlineKeyboardButton(
                    text="Редактировать клиента", callback_data="edit_client"),
                InlineKeyboardButton(text="Добавить запись",
                                     callback_data="add_reg")
            ],
            [
                InlineKeyboardButton(text="Выгрузить в CSV",
                                     callback_data="export_client_to_csv")
            ]
        ]
        if have_regs:
            keyboard[2].append(InlineKeyboardButton(
                text="Изменить запись на процедуру", callback_data=f"change_reg:back_to_client|{client_id}"))
        if prev:
            keyboard[0][0] = InlineKeyboardButton(
                text="Предыдущие 10", callback_data=f"prev_regs:{page-1}")
        if next:
            keyboard[0].append(
                InlineKeyboardButton(text="Следующие 10",
                                     callback_data=f"next_regs:{page+1}")
            )
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def add_reg_1_kb(cls, client_id: int):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Повторить запись 🔁", callback_data="repeat_reg")
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"back_to_client|{client_id}"),
                InlineKeyboardButton(
                    text="Выбрать другие услуги", callback_data=f"create_reg|{client_id}")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def choose_gender_kb(cls, client_id: int):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Девушка", callback_data=f"reg_gender:girls"),
                InlineKeyboardButton(
                    text="Мужчина", callback_data=f"reg_gender:boys")
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"back_to_client|{client_id}")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def choose_epilation_type_kb(cls, client_id, gender):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Лазерная", callback_data=f"epilation_type:laser:{gender}"),
                InlineKeyboardButton(
                    text="Био (воск или шугаринг)", callback_data=f"epilation_type:bio:{gender}")
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"create_reg|{client_id}")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def choose_services(cls, services, gender, selected_services=[]):
        def inline_btn(service, idx):
            sign = '✅ ' if services[idx] in selected_services else ''
            return InlineKeyboardButton(text=f"{sign}{service['title']}",
                                        callback_data=f"select_service:{idx}")

        keyboard = []
        for i in range(0, len(services) - 1, 2):
            keyboard.append([
                inline_btn(services[i], i),
                inline_btn(services[i+1], i+1)
            ])
        if len(services) % 2 == 1:
            idx = len(services) - 1
            keyboard.append([inline_btn(services[idx], idx)])
        keyboard.append([
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"reg_gender:{gender}")
        ])
        if len(selected_services) > 0:
            keyboard[len(keyboard) - 1].append(
                InlineKeyboardButton(
                    text="Далее ➡️", callback_data=f"set_reg_date")
            )
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def edit_client_kb(cls, user_id, client_id):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"back_to_client|{client_id}"),
                InlineKeyboardButton(
                    text="Изменить Фамилию и имя", callback_data=f"change_full_name")
            ],
            [
                InlineKeyboardButton(text="Изменить пол",
                                     callback_data=f"change_gender:{user_id}"),
                InlineKeyboardButton(
                    text="Изменить время на процедуру", callback_data=f"change_service_duration")
            ],
            [
                InlineKeyboardButton(
                    text="Изменить телефон", callback_data=f"change_phone"),
                InlineKeyboardButton(
                    text="Изменить дату рождения", callback_data=f"change_birthday")
            ],
            [
                InlineKeyboardButton(
                    text="Изменить комментарий", callback_data=f"change_note")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def set_client_gender_kb(cls, user_id):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Мужчина", callback_data=f"set_client_gender:{user_id}:boys"),
                InlineKeyboardButton(
                    text="Девушка", callback_data=f"set_client_gender:{user_id}:girls")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def msg_to_personal_kb(cls):
        keyboard = [[InlineKeyboardButton(
            text="Написать Оксане", url="https://t.me/neprostowaxing")]]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def mass_message_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(text="Новая рассылка",
                                     callback_data="new_mailing"),
                InlineKeyboardButton(text="Список рассылок",
                                     callback_data="mailings_list")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def mailing_info_kb(cls, mailing_id, cancel=False):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="mailings_list")
            ],
        ]
        if cancel:
            keyboard.append([
                InlineKeyboardButton(
                    text="Отменить рассылку", callback_data=f"cancel_mailing:{mailing_id}")
            ])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def new_mailing_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="mass_message"),
                InlineKeyboardButton(
                    text="По дате", callback_data="group_by_date")
            ],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def mailing_for_group(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="new_mailing"),
                InlineKeyboardButton(text="Отмена 🙅", callback_data="cancel")
            ],
            [
                InlineKeyboardButton(
                    text="Отправить сейчас ✉", callback_data="send_now")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def mailing_dtime_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="mailing_client_group"),
                InlineKeyboardButton(text="Отмена 🙅", callback_data="cancel")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def mailing_text_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="mailing_dtime"),
                InlineKeyboardButton(text="Отмена 🙅", callback_data="cancel")
            ],
            [
                InlineKeyboardButton(
                    text="Отправить👍", callback_data="send_mailing")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def schedule_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Сегодня", callback_data="schedule_for_today"),
                InlineKeyboardButton(
                    text="Завтра", callback_data="schedule_for_tomorrow"),
            ],
            [
                InlineKeyboardButton(text="Диапазон дат",
                                     callback_data="date_range")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def schedule_date_kb(cls, schedule_date, page: int, prev_page=False, next_page=False):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Условные обозначения", callback_data="symbols"),
            ],
            [
                InlineKeyboardButton(text="Другая дата",
                                     callback_data="schedule"),
                InlineKeyboardButton(text="Диапазон дат",
                                     callback_data="date_range")
            ],
            [
                InlineKeyboardButton(text="Изменить запись",
                                     callback_data=f"change_reg:back_to_schedule|{schedule_date}"),
                InlineKeyboardButton(text="Добавить запись",
                                     callback_data="clients"),
            ],
            [
                InlineKeyboardButton(
                    text="Заблокировать для записи", callback_data=f"block_for_reg:{schedule_date}"),
                InlineKeyboardButton(
                    text="Отменить блокировку", callback_data=f"unblock:{schedule_date}")
            ],
            [
                InlineKeyboardButton(
                    text="Открыть календарь", url="https://calendar.google.com/"),
                InlineKeyboardButton(text="Выгрузить в CSV",
                                     callback_data=f"export_schedule_to_csv:{schedule_date}")
            ],
        ]
        if prev_page:
            keyboard.append([
                InlineKeyboardButton(
                    text="Предыдущие 10", callback_data=f"schedule_prev_regs:{schedule_date}:{page - 1}")
            ])
        if next_page:
            btn = InlineKeyboardButton(
                text="Следующие 10", callback_data=f"schedule_next_regs:{schedule_date}:{page + 1}")
            if len(keyboard) == 5:
                keyboard[4].append(btn)
            else:
                keyboard.append([btn])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def block_date2_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Записи оставить, остальное заблокировать", callback_data="block_without_canceling")],
            [InlineKeyboardButton(
                text="Заблокировать с отменой записей", callback_data="block_and_cancel")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="back_to_block_date1")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def change_reg_id_kb(cls, cb_data):
        keyboard = [
            [
                InlineKeyboardButton(text="Изменить время",
                                     callback_data="change_reg_time"),
                InlineKeyboardButton(text="Отменить запись",
                                     callback_data="cancel_reg_by_master"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=cb_data),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def back_btn(cls, cb_data):
        keyboard = [[
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=cb_data)
        ]]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class UserInlineKeyboard:
    """Клавиатура пользователя"""

    @classmethod
    def phone_in_base_kb(cls, phone: str):
        keyboard = [
            [InlineKeyboardButton(
                text="Отправить Оксане уведомление", callback_data=f"msg_to_admin|{phone}")],
            [InlineKeyboardButton(
                text="Хочу ввести другой телефон", callback_data="correct_phone")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def answer_to_user_kb(cls, user_id: str | int):
        keyboard = [[InlineKeyboardButton(
            text="↩️ Ответить", callback_data=f"answer:{user_id}")]]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def msg_to_admin_kb(cls):
        keyboard = [[InlineKeyboardButton(
            text="Написать Оксане в ЛС", url="https://t.me/neprostowaxing")]]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def user_gender_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Мужчина", callback_data="user_gender:boys")],
            [InlineKeyboardButton(
                text="Девушка", callback_data="user_gender:girls")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def user_birthday_kb(cls):
        keyboard = [[InlineKeyboardButton(
            text="Не хочу вводить дату рождения", callback_data="main_menu")]]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def price_gender_kb(cls, gender: Literal["boys", "girls"]):
        if gender == "boys":
            keyboard = [[InlineKeyboardButton(text="Посмотреть прайс для девушек 👩‍🦰",
                                              callback_data="price_gender:girls")]]
        else:
            keyboard = [[InlineKeyboardButton(text="Посмотреть прайс для мужчин 👨",
                                              callback_data="price_gender:boys")]]
        keyboard.append([InlineKeyboardButton(
            text="Посмотреть сравнение видов эпиляции", callback_data="epil_diff")])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def about_epilation_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Подробнее о лазерной эпиляции", callback_data="about_epil:laser")],
            [InlineKeyboardButton(
                text="Подробнее о биоэпиляции (шугаринг/воск)", callback_data="about_epil:bio")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def about_me_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Посмотреть приветственное видео", callback_data="about_me_video")],
            [InlineKeyboardButton(text="Читать отзывы",
                                  callback_data="read_feedbacks")],
            [InlineKeyboardButton(
                text="Написать Оксане в личку", url="https://t.me/neprostowaxing")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def feedbacks_categories_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Отзывы о лазерной эпиляции", callback_data="feedback_girls_laser:1")],
            [InlineKeyboardButton(
                text="Отзывы о биоэпиляции (воск/шугаринг)", callback_data="feedback_girls_bio:1")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def feedbacks_gender_kb(cls):
        keyboard = [
            [InlineKeyboardButton(text="Отзывы от мужчин",
                                  callback_data="feedbacks_boys|page:start")],
            [InlineKeyboardButton(text="Отзывы от девушек",
                                  callback_data="feedbacks_girls")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def feedbacks_boys_kb(cls, page: str | int):
        keyboard = [
            [InlineKeyboardButton(
                text="Отзывы от девушек 👩‍🦰", callback_data="feedbacks_girls")]
        ]
        if page != 0:
            keyboard.insert(0, [
                InlineKeyboardButton(
                    text="Читать ещё", callback_data=f"feedbacks_boys|page:{page}")
            ])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def feedbacks_girls_kb(cls, page, category):
        category_text = "биоэпиляции" if category == "feedback_girls_laser" else "лазерной эпиляции"
        other_category = "feedback_girls_bio" if category == "feedback_girls_laser" else "feedback_girls_laser"
        keyboard = [
            [InlineKeyboardButton(
                text=f"Смотреть отзывы о {category_text}", callback_data=f"{other_category}:1")],
            [InlineKeyboardButton(
                text="Отзывы от мужчин 👨", callback_data="feedbacks_boys|page:start")],
        ]
        if page != 0:
            keyboard.insert(0, [
                InlineKeyboardButton(
                    text="Читать ещё", callback_data=f"{category}:{page}")
            ])
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class UserAboutEpilationInline:

    @classmethod
    def laser_boys_1_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(text="Для девушки 👩‍🦰",
                                     callback_data="about_epil:laser:girls:1"),
                InlineKeyboardButton(
                    text="Далее ➡️", callback_data="about_epil:laser:boys:2"),

            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def laser_boys_2_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Часто задаваемые вопросы от мужчин ❔", callback_data="about_epil:laser:boys:3")],
            [InlineKeyboardButton(text="Отзывы от мужчин",
                                  callback_data="feedbacks_boys|page:start")],
            [InlineKeyboardButton(
                text="Хочу записаться на процедуру", callback_data="sign_up")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def laser_boys_3_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Хочу записаться на процедуру 📝", callback_data="sign_up")],
            [InlineKeyboardButton(text="Ок. С лазерной понятно, хочу почитать про биоэпиляцию",
                                  callback_data="about_epil:bio")],
            [InlineKeyboardButton(
                text="Написать Оксане в личку", url="https://t.me/neprostowaxing")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def bio_boys_1_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Часто задаваемые вопросы от мужчин ❔", callback_data="about_epil:bio:boys:2")],
            [InlineKeyboardButton(
                text="Читать про биоэпиляцию для девушки", callback_data="about_epil:bio:girls:1")],
            [
                InlineKeyboardButton(
                    text="Отзывы", callback_data="feedbacks_boys|page:start"),
                InlineKeyboardButton(text="Записаться 📝",
                                     callback_data="sign_up"),
            ],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def bio_boys_2_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Отзывы", callback_data="feedbacks_boys|page:start"),
                InlineKeyboardButton(text="Записаться 📝",
                                     callback_data="sign_up"),
            ],
            [InlineKeyboardButton(text="Ок. С биоэпиляцией понятно, хочу почитать про лазерную",
                                  callback_data="about_epil:laser:boys:1")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def laser_girls_1_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(text="Для мужчины 🧑",
                                     callback_data="about_epil:laser:boys:1"),
                InlineKeyboardButton(
                    text="Далее ➡️", callback_data="about_epil:laser:girls:2"),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def laser_girls_2_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Отзывы", callback_data="feedbacks_girls"),
                InlineKeyboardButton(text="Записаться 📝",
                                     callback_data="sign_up"),
            ],
            [InlineKeyboardButton(
                text="Часто задаваемые вопросы ❔", callback_data="about_epil:laser:girls:3")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def laser_girls_3_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Хочу записаться на процедуру 📝", callback_data="sign_up")],
            [InlineKeyboardButton(text="Ок. С лазерной понятно, хочу почитать про биоэпиляцию",
                                  callback_data="about_epil:bio")],
            [InlineKeyboardButton(
                text="Написать Оксане в личку", url="https://t.me/neprostowaxing")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def bio_girls_1_kb(cls):
        keyboard = [
            [InlineKeyboardButton(
                text="Часто задаваемые вопросы от девушек ❔", callback_data="about_epil:bio:girls:2")],
            [InlineKeyboardButton(
                text="Читать про биоэпиляцию для мужчин", callback_data="about_epil:bio:boys:1")],
            [
                # todo Исправить коллбек дату
                InlineKeyboardButton(
                    text="Отзывы", callback_data="feedbacks_boys|page:start"),
                InlineKeyboardButton(text="Записаться 📝",
                                     callback_data="sign_up"),
            ],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def bio_girls_2_kb(cls):
        keyboard = [
            [
                # todo Исправить коллбек дату
                InlineKeyboardButton(
                    text="Отзывы", callback_data="feedbacks_boys|page:start"),
                InlineKeyboardButton(text="Записаться 📝",
                                     callback_data="sign_up"),
            ],
            [InlineKeyboardButton(text="Ок. С биоэпиляцией понятно, хочу почитать про лазерную",
                                  callback_data="about_epil:laser:girls:1")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class UserSignUpInline:

    @classmethod
    def msg_to_admin_kb(cls):
        keyboard = [[InlineKeyboardButton(
            text="Написать Оксане в личку", url="https://t.me/neprostowaxing")]]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def create_reg_gender_kb(cls):
        keyboard = [
            [InlineKeyboardButton(text="Для девушки 👱‍♀️",
                                  callback_data="create_reg|gender:girls")],
            [InlineKeyboardButton(text="Для мужчины 👱‍♂️",
                                  callback_data="create_reg|gender:boys")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def create_reg_category_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Лазерная", callback_data="create_reg|category:laser"),
                InlineKeyboardButton(
                    text="Био (воск или шугаринг)", callback_data="create_reg|category:bio"),
            ],
            [InlineKeyboardButton(
                text="Посмотреть сравнение видов эпиляции", callback_data="epil_diff")],
            [InlineKeyboardButton(text="Посмотреть цены",
                                  callback_data="price")],
            [InlineKeyboardButton(
                text="⬅️ Назад", callback_data="back_to_block_c")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def menu_services_kb(cls, services: list, ok_services: list, gender: Literal["girls", "boys"]):
        keyboard = []
        for i in range((len(services) + 1) // 2):
            if 2 * i + 1 >= len(services):
                text = services[2 * i]["title"]
                service_id = services[2 * i]["id"]
                sign = "✅ " if service_id in ok_services else ""
                keyboard.append([InlineKeyboardButton(
                    text=f"{sign}{text}", callback_data=f"switch_service:{service_id}")])
            else:
                text_1, text_2 = services[2 *
                                          i]["title"], services[2 * i + 1]["title"]
                service_id_1, service_id_2 = services[2 *
                                                      i]["id"], services[2 * i + 1]["id"]
                sign_1 = "✅ " if service_id_1 in ok_services else ""
                sign_2 = "✅ " if service_id_2 in ok_services else ""
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text=f"{sign_1}{text_1}", callback_data=f"switch_service:{service_id_1}"),
                        InlineKeyboardButton(
                            text=f"{sign_2}{text_2}", callback_data=f"switch_service:{service_id_2}"),
                    ]
                )
        back_and_forth = [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"create_reg|gender:{gender}")
        ]
        if len(ok_services) > 0:
            back_and_forth.append(
                InlineKeyboardButton(
                    text="Далее ➡️", callback_data="main_menu_c_accept")
            )
        keyboard.append(back_and_forth)
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def create_reg_accept_kb(cls, category: Literal["bio", "laser"]):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"create_reg|category:{category}"),
                InlineKeyboardButton(text="Подтвердить 👍",
                                     callback_data="choose_date"),
            ],
            [InlineKeyboardButton(text="Связаться с Оксаной",
                                  url="https://t.me/neprostowaxing")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def choose_date_kb(cls, date_list: List[datetime], back_data: str, offset: Optional[int]):
        date_row = []
        for date in date_list[:5]:
            date_row.append(InlineKeyboardButton(text=date.strftime("%d.%m"),
                                                 callback_data=f"select_date:{date.strftime('%d.%m.%Y')}"))
        second_row = [InlineKeyboardButton(
            text="⬅️ Назад", callback_data=back_data)]
        if offset is not None:
            second_row.append(InlineKeyboardButton(
                text="Ещё варианты 🔄", callback_data=f"date_offset:{offset}"))
        keyboard = [
            date_row,
            second_row,
            [InlineKeyboardButton(text="Связаться с Оксаной",
                                  url="https://t.me/neprostowaxing")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def choose_time_kb(cls, slots: list):
        slots_text = {
            "morning": "Утро (9:00-12:00)",
            "day": "День (12:00-18:00)",
            "evening": "Вечер (18:00-22:00)",
        }
        date_row = []
        for slot in slots:
            date_row.append(InlineKeyboardButton(
                text=slots_text[slot], callback_data=f"select_time:{slot}"))
        keyboard = [
            date_row,
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data="choose_date"),
                InlineKeyboardButton(
                    text="Связаться с Оксаной", url="https://t.me/neprostowaxing"),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def finish_reg_accept_kb(cls, date: datetime):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"select_date:{date.strftime('%d.%m.%Y')}"),
                InlineKeyboardButton(text="Подтвердить 👍",
                                     callback_data="finish_reg"),
            ],
            [InlineKeyboardButton(text="Связаться с Оксаной",
                                  url="https://t.me/neprostowaxing")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def no_birthday_kb(cls):
        keyboard = [[InlineKeyboardButton(
            text="Написать Оксане в личку", url="https://t.me/neprostowaxing")]]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def resource_menu_kb(cls):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Яндекс", callback_data="resource:Яндекс"),
                InlineKeyboardButton(text="VK", callback_data="resource:VK"),
                InlineKeyboardButton(
                    text="2ГИС", callback_data="resource:2ГИС"),
            ],
            [
                InlineKeyboardButton(
                    text="Instagram", callback_data="resource:Instagram"),
                InlineKeyboardButton(text="Рекомендация",
                                     callback_data="resource:Рекомендация"),
                InlineKeyboardButton(
                    text="Другое", callback_data="resource:Другое"),
            ],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def finished_reg_kb(cls, user_id, reg_type):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Повторить запись 🔁", callback_data=f"repeat_reg_user:{user_id}:{reg_type}"),
                InlineKeyboardButton(
                    text="Выбрать другие услуги", callback_data="create_reg_user")
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def created_reg_kb(cls, reg_id):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Хочу отменить ❌ или перенести запись ⏩", callback_data=f"cancel_or_move_reg:{reg_id}"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def cancel_or_move_reg_kb(cls, reg_id):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Отменить запись ❌", callback_data=f"cancel_reg:{reg_id}"
                ),
                InlineKeyboardButton(
                    text="Перенести запись ⏭", callback_data=f"move_reg:{reg_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Связаться с Оксаной", url="https://t.me/neprostowaxing"),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @classmethod
    def after_reg_kb(cls, reg_id: int):
        keyboard = [
            [
                InlineKeyboardButton(
                    text="Отменить запись ❌", callback_data=f"cancel_reg:{reg_id}"),
                InlineKeyboardButton(
                    text="Связаться с Оксаной", url="https://t.me/neprostowaxing"),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

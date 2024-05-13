from aiogram.fsm.state import State, StatesGroup


class AdminFSM(StatesGroup):
    home = State()
    auto_texts = State()
    new_service = State()
    edit_service = State()

    # info block
    address_video = State()
    address_location = State()
    address_text = State()

    about_me_video = State()
    about_me_photo = State()
    about_me_text = State()

    price_list_photo = State()

    update_feedback_media = State()
    update_feedback_order = State()
    create_feedback = State()

    # necessary routine
    routine_reg_price = State()
    routine_reg_time = State()

    # schedule
    schedule_date = State()
    first_date_of_range = State()
    second_date_of_range = State()

    block_date1 = State()
    block_date2 = State()
    cancel_reason = State()

    unblock_date1 = State()
    unblock_date2 = State()

    change_reg_id = State()
    new_reg_time = State()

    # clients
    find_client = State()
    clients_reg_date = State()
    clients_reg_time = State()
    client_first_name = State()
    client_last_name = State()
    client_phone = State()
    client_birthday = State()
    client_note = State()
    client_service_duration = State()

    # mass_message
    mailing_id = State()
    mailing_client_group = State()
    group_by_date = State()
    mailing_dtime = State()
    mailing_text = State()


class UserFSM(StatesGroup):
    home = State()
    manual_phone = State()
    first_name_reg = State()
    last_name_reg = State()
    birthday_reg = State()

    main_menu = State()

    reg_date = State()
    reg_time = State()
    first_name_sign = State()
    last_name_sign = State()
    birthday_sign = State()

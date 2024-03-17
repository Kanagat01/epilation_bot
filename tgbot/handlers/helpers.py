from aiogram.fsm.context import FSMContext
from create_bot import bot
from tgbot.models.sql_connector import StaticsDAO


def sort_feedbacks(file_list: list):
    new_file_list = sorted(file_list, key=lambda x: int(
        x["title"].replace("video", "")
    ))
    return new_file_list


async def feedbacks_media_group(page: int, category: str, user_id: str | int, is_admin=False):
    file_list = await StaticsDAO.get_order_list(category=category, like="")
    file_list = sort_feedbacks(file_list)

    first_file = (page - 1) * 10
    if len(file_list) - first_file < 11:
        last_file = len(file_list)
        next_page = 0
    else:
        last_file = first_file + 10
        next_page = page + 1
    media_group = []
    for file in file_list[first_file:last_file]:
        file_id = file["file_id"]
        media_type = "video" if "video" in file["title"] else "photo"
        media_group.append({"media": file_id, "type": media_type})

    if len(media_group) == 0:
        if not is_admin:
            await bot.send_message(chat_id=user_id, text="В этой категории пока нет отзывов")
    else:
        await bot.send_media_group(chat_id=user_id, media=media_group)

    if is_admin:
        return next_page, file_list[first_file:last_file]
    else:
        return next_page


async def reset_state(state: FSMContext):
    state_data = await state.get_data()
    await state.clear()
    await state.set_data(state_data)

import asyncio
from datetime import datetime

from tgbot.handlers.admin.admin import router as admin_router
from tgbot.handlers.admin.content_management import router as content_router
from tgbot.handlers.admin.necessary_routine import router as routine_router
from tgbot.handlers.admin.clients import router as clients_router
from tgbot.handlers.admin.mass_message import router as mass_message_router
from tgbot.handlers.admin.schedule_block import router as schedule_router
from tgbot.handlers.user.sign_up_block import router as sign_up_block
from tgbot.handlers.user.registration_block import router as registration_block
from tgbot.handlers.user.price_block import router as price_block
from tgbot.handlers.user.about_epilation_block import router as about_epilation_block
from tgbot.handlers.user.address_block import router as address_block
from tgbot.handlers.user.about_me_block import router as about_me_block
from tgbot.handlers.user.write_to_personal import router as write_to_personal
from tgbot.handlers.echo import router as echo_router
from tgbot.misc.scheduler import HolidayScheduler

from create_bot import bot, dp, scheduler, logger, register_global_middlewares, config

admin_routers = [
    admin_router,
    routine_router,
    content_router,
    schedule_router,
    clients_router,
    mass_message_router
]

user_routers = [
    registration_block,
    price_block,
    about_epilation_block,
    address_block,
    about_me_block,
    sign_up_block,
    write_to_personal
]


async def main():
    logger.info("Starting bot")
    dp.include_routers(
        *admin_routers,
        *user_routers,
        echo_router)

    try:
        scheduler.start()
        next_year = datetime.now().year + 1
        hour = 11
        holidays = [("new_year", datetime(next_year, 1, 1, hour)), ("23_february", datetime(
            next_year, 2, 23, hour)), ("8_march", datetime(next_year, 3, 8, hour))]
        for auto_text, dtime in holidays:
            try:
                await HolidayScheduler.create(auto_text, dtime)
            except:
                pass

        register_global_middlewares(dp, config)
        await dp.start_polling(bot)
    finally:
        await dp.storage.close()
        await bot.session.close()
        scheduler.shutdown(True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")

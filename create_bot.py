import os.path
import logging
import redis
import betterlogging as bl
from pytz import timezone

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from tgbot.config import load_config
from tgbot.middlewares.config import ConfigMiddleware


config = load_config(".env")
r = redis.Redis(host=config.rds.host, port=config.rds.port, db=config.rds.db)
storage = RedisStorage(redis=r) if config.tg_bot.use_redis else MemoryStorage()

bot = Bot(token=config.tg_bot.token, parse_mode='HTML')
dp = Dispatcher()

calendar_id = config.tg_bot.calendar_id
local_tz = 'Europe/Moscow'
local_tz_obj = timezone(local_tz)
scheduler = AsyncIOScheduler(timezone=local_tz_obj)
scheduler.add_jobstore('redis', jobs_key='example.jobs',
                       run_times_key='example.run_times')

logger = logging.getLogger(__name__)
log_level = logging.INFO
bl.basic_colorized_config(level=log_level)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
token_path = "tgbot/calendar_api/token.json"
creds_path = "tgbot/calendar_api/credentials.json"
# token_path = "tgbot/calendar_api/oxana_token.json"
# creds_path = "tgbot/calendar_api/oxana_creds.json"

creds = None
if os.path.exists(token_path):
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            creds_path, SCOPES
        )
        creds = flow.run_local_server(port=0)

    with open(token_path, "w") as token:
        token.write(creds.to_json())

calendar_service = build("calendar", "v3", credentials=creds)

DATABASE_URL = f'postgresql+asyncpg://{config.db.user}:{config.db.password}@{config.db.host}:5432/{config.db.database}'


def register_global_middlewares(dp: Dispatcher, config):
    dp.message.outer_middleware(ConfigMiddleware(config))
    dp.callback_query.outer_middleware(ConfigMiddleware(config))

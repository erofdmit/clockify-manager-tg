import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
from dotenv import load_dotenv
from db.engine import create_connection, create_table
from db.methods import get_user_by_tg_username
from clockify_api import ClockifyAPI
import start_commands
import time_entry_commands

# Загрузка токена Telegram из .env
load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Настройки логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

# Инициализация Clockify API и базы данных
clockify_api = ClockifyAPI()
db_conn = create_connection()

# Регистрация роутеров и запуск
async def main():
    create_table(db_conn)
    dp.include_router(start_commands.router)
    dp.include_router(time_entry_commands.router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from db.engine import create_connection
from db.methods import get_user_by_tg_username, get_user_by_email, update_api_key_by_tg_username, update_user_by_email
from clockify_api import ClockifyAPI, UserManager
from aiogram.fsm.state import State, StatesGroup

router = Router()

clockify_api = ClockifyAPI()
db_conn = create_connection()
user_manager = UserManager(db_conn)

# Состояния для FSM
class Form(StatesGroup):
    email = State()
    api_key = State()

@router.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    user_manager.add_new_users_to_db(clockify_api)
    tg_username = message.from_user.username
    user = get_user_by_tg_username(db_conn, tg_username)

    if user and user[1]:  # Проверяем, что api_key уже установлен
        await message.answer("Вы уже зарегистрированы. Используйте команды:\n"
                             "/create_time_entry\n/start_time_entry\n/end_time_entry\n/change_api_key")
        await state.clear()
    else:
        await message.answer("Пожалуйста, отправьте вашу электронную почту для идентификации.")
        await state.set_state(Form.email)

@router.message(Form.email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text
    user = get_user_by_email(db_conn, email)
    if user:
        tg_username = message.from_user.username
        await state.update_data(email=email, tg_username=tg_username)
        update_user_by_email(db_conn, email, 'placeholder_api_key', tg_username)
        await message.answer("Пользователь найден. Пожалуйста, отправьте ваш Clockify API ключ.")
        await state.set_state(Form.api_key)
    else:
        await message.answer("Электронная почта не найдена. Попробуйте снова.")
        await state.clear()

@router.message(Form.api_key)
async def process_api_key(message: types.Message, state: FSMContext):
    api_key = message.text
    user_data = await state.get_data()
    tg_username = message.from_user.username
    update_api_key_by_tg_username(db_conn, tg_username, api_key)
    await message.answer("Ваш API ключ обновлен. Теперь используйте команды:\n"
                         "/create_time_entry\n/start_time_entry\n/end_time_entry\n/change_api_key")
    await state.clear()

@router.message(Command('change_api_key'))
async def cmd_change_api_key(message: types.Message, state: FSMContext):
    await message.answer("Отправьте новый API ключ:")
    await state.set_state(Form.api_key)

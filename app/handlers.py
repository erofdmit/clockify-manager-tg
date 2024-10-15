import requests
from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.utils import get_current_time_in_moscow
from states import Form  # Импортируем состояния
from db.methods import get_user_by_email, update_user_by_email, get_user_by_tg_username

# Обработчик команды /start
async def cmd_start(message: types.Message, state: FSMContext, user_manager, clockify_api, db_conn):
    user_manager.add_new_users_to_db(clockify_api)
    tg_username = message.from_user.username
    user = get_user_by_tg_username(db_conn, tg_username)
    if user and user[1]:
        await message.answer("Вы уже зарегистрированы. Используйте команды:\n"
                             "/create_time_entry\n/start_time_entry\n/end_time_entry\n/change_api_key")
        await state.clear()
    else:
        await message.answer("Пожалуйста, отправьте вашу электронную почту для идентификации.")
        await state.set_state(Form.email)

# Обработчик команды /create_time_entry
async def cmd_create_time_entry(message: types.Message, state: FSMContext, user_manager, clockify_api):
    projects = user_manager.get_user_projects(clockify_api, message.from_user.username)
    if projects:
        buttons = [[KeyboardButton(text=project)] for project in projects]
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
        await message.answer("Выберите проект:", reply_markup=markup)
        await state.set_state(Form.project_choice)
    else:
        await message.answer("Проекты не найдены.")

# Обработка выбора проекта
async def process_project_choice(message: types.Message, state: FSMContext):
    await state.update_data(project=message.text)
    await message.answer("Введите описание:")
    await state.set_state(Form.description)

# Обработка описания
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите дату начала в формате YYYY-MM-DD:")
    await state.set_state(Form.start_date)

# Обработка времени окончания
async def process_end_time(message: types.Message, state: FSMContext, time_entry_manager, clockify_api):
    user_data = await state.get_data()
    
    start_time = f"{user_data['start_date']}T{user_data['start_time']}:00Z"
    end_time = f"{user_data['end_date']}T{user_data['end_time']}:00Z"
    
    await state.update_data(start_time=start_time, end_time=end_time)

    # Подтверждение перед созданием записи
    await message.answer(f"Проект: {user_data['project']}\nОписание: {user_data['description']}\n"
                         f"Начало: {start_time}\nОкончание: {end_time}\nПодтвердите создание записи.")
    await state.set_state(Form.confirm_entry)

# Подтверждение создания записи времени
async def process_confirm_entry(message: types.Message, state: FSMContext, time_entry_manager, clockify_api):
    user_data = await state.get_data()
    if message.text.lower() == 'да':
        time_entry_manager.create_time_entry(
            clockify_api, message.from_user.username, user_data['start_time'], user_data['end_time'], 
            user_data['project'], user_data['description']
        )
        await message.answer("Запись времени успешно создана.")
    else:
        await message.answer("Создание записи отменено.")
    await state.clear()

# Команда /start_time_entry
async def cmd_start_time_entry(message: types.Message, state: FSMContext, user_manager, clockify_api):
    projects = user_manager.get_user_projects(clockify_api, message.from_user.username)
    if projects:
        buttons = [[KeyboardButton(text=project)] for project in projects]
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
        await message.answer("Выберите проект:", reply_markup=markup)
        await state.set_state(Form.project_choice_start)

# Обработка описания для start_time_entry и старт записи
async def process_description_start(message: types.Message, state: FSMContext, time_entry_manager, clockify_api):
    user_data = await state.get_data()
    description = message.text
    project_name = user_data.get('project')

    # Используем текущее время для начала записи
    start_time = get_current_time_in_moscow()

    time_entry_manager.start_time_entry(
        clockify_api, message.from_user.username, project_name, description
    )
    await message.answer("Запись времени успешно начата.")
    await state.clear()

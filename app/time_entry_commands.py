import requests
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from db.engine import create_connection
from db.methods import get_user_by_tg_username
from clockify_api import ClockifyAPI, TimeEntryManager, UserManager
from utils import get_current_time_in_moscow

router = Router()

clockify_api = ClockifyAPI()
db_conn = create_connection()
time_entry_manager = TimeEntryManager(db_conn)
user_manager = UserManager(db_conn)

# Состояния для FSM
class CreateTimeEntryForm(StatesGroup):
    project_choice = State()
    description = State()
    start_date = State()
    start_time = State()
    end_date = State()
    end_time = State()
    confirmation = State()

class StartTimeEntryForm(StatesGroup):
    project_choice = State()
    description = State()

# Функция для создания клавиатуры с датами (от сегодня до 5 дней назад)
def get_date_keyboard():
    buttons = []
    for i in range(6):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        buttons.append([KeyboardButton(text=date)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# Функция для создания клавиатуры с временем (с шагом в 30 минут)
def get_time_keyboard(start_time_limit=None):
    buttons = []
    times = []
    for hour in range(24):
        for minute in [0, 30]:
            time_str = f"{hour:02}:{minute:02}"
            if start_time_limit and datetime.strptime(time_str, "%H:%M") < start_time_limit:
                continue
            times.append(time_str)
    for i in range(0, len(times), 2):
        buttons.append([KeyboardButton(text=times[i]), KeyboardButton(text=times[i+1])])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# Функция для создания клавиатуры с датой окончания
def get_end_date_keyboard(start_date):
    buttons = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    if start_date == today:
        # Если дата начала — сегодня, добавляем только "сегодня" и "завтра"
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        buttons = [[KeyboardButton(text=today)], [KeyboardButton(text=tomorrow)]]
    else:
        # Добавляем даты от сегодня до даты начала включительно
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
        days_diff = (datetime.now() - start_date_obj).days
        for i in range(days_diff + 1):
            date = (start_date_obj + timedelta(days=i)).strftime('%Y-%m-%d')
            buttons.append([KeyboardButton(text=date)])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

# Команда для создания полной записи времени
@router.message(Command('create_time_entry'))
async def cmd_create_time_entry(message: types.Message, state: FSMContext):
    try:
        projects = user_manager.get_user_projects(clockify_api, message.from_user.username)
        if projects:
            buttons = [[KeyboardButton(text=project)] for project in projects]
            markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
            await message.answer("Выберите проект:", reply_markup=markup)
            await state.set_state(CreateTimeEntryForm.project_choice)
        else:
            await message.answer("Проекты не найдены.")
    except Exception as e:
        await message.answer(f"Ошибка при получении проектов: {str(e)}")

@router.message(CreateTimeEntryForm.project_choice)
async def process_project_choice(message: types.Message, state: FSMContext):
    await state.update_data(project=message.text)
    await message.answer("Введите описание:")
    await state.set_state(CreateTimeEntryForm.description)

@router.message(CreateTimeEntryForm.description)
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    markup = get_date_keyboard()
    await message.answer("Выберите дату начала:", reply_markup=markup)
    await state.set_state(CreateTimeEntryForm.start_date)

@router.message(CreateTimeEntryForm.start_date)
async def process_start_date(message: types.Message, state: FSMContext):
    await state.update_data(start_date=message.text)
    markup = get_time_keyboard()
    await message.answer("Выберите время начала:", reply_markup=markup)
    await state.set_state(CreateTimeEntryForm.start_time)

@router.message(CreateTimeEntryForm.start_time)
async def process_start_time(message: types.Message, state: FSMContext):
    await state.update_data(start_time=message.text)
    
    # Получаем дату начала
    user_data = await state.get_data()
    start_date = user_data['start_date']
    
    # Формируем клавиатуру для выбора даты окончания
    markup = get_end_date_keyboard(start_date)
    await message.answer("Выберите дату окончания:", reply_markup=markup)
    await state.set_state(CreateTimeEntryForm.end_date)

@router.message(CreateTimeEntryForm.end_date)
async def process_end_date(message: types.Message, state: FSMContext):
    await state.update_data(end_date=message.text)
    
    # Если дата окончания совпадает с началом, то время окончания не может быть раньше начала
    user_data = await state.get_data()
    start_date = user_data['start_date']
    start_time = datetime.strptime(user_data['start_time'], "%H:%M")
    
    # Ограничиваем выбор времени окончания только если дата совпадает
    time_limit = start_time if start_date == message.text else None
    markup = get_time_keyboard(start_time_limit=time_limit)
    await message.answer("Выберите время окончания:", reply_markup=markup)
    await state.set_state(CreateTimeEntryForm.end_time)

@router.message(CreateTimeEntryForm.end_time)
async def process_end_time(message: types.Message, state: FSMContext):
    await state.update_data(end_time=message.text)
    user_data = await state.get_data()
    
    # Формируем сообщение с подтверждением
    start_time = f"{user_data['start_date']} {user_data['start_time']}"
    end_time = f"{user_data['end_date']} {user_data['end_time']}"
    project = user_data['project']
    description = user_data['description']
    
    buttons = [[KeyboardButton(text=project)] for project in ['да', 'нет']]
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    await message.answer(f"Подтвердите запись времени:\n\n"
                         f"Проект: {project}\n"
                         f"Описание: {description}\n"
                         f"Дата и время начала: {start_time}\n"
                         f"Дата и время окончания: {end_time}", reply_markup=markup)
    await state.set_state(CreateTimeEntryForm.confirmation)

@router.message(CreateTimeEntryForm.confirmation)
async def process_confirmation(message: types.Message, state: FSMContext):
    if message.text.lower() == 'да':
        try:
            user_data = await state.get_data()
            start_time = f"{user_data['start_date']}T{user_data['start_time']}:00Z"
            end_time = f"{user_data['end_date']}T{user_data['end_time']}:00Z"
            time_entry_manager.create_time_entry(
                clockify_api, message.from_user.username, start_time, end_time,
                user_data['project'], user_data['description']
            )
            await message.answer("Запись времени успешно создана.")
        except Exception as e:
            await message.answer(f"Ошибка при создании записи времени: {str(e)}")
    else:
        await message.answer("Запись времени отменена.")
    await state.clear()


# Команда для начала записи времени
@router.message(Command('start_time_entry'))
async def cmd_start_time_entry(message: types.Message, state: FSMContext):
    try:
        projects = user_manager.get_user_projects(clockify_api, message.from_user.username)
        if projects:
            buttons = [[KeyboardButton(text=project)] for project in projects]
            markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
            await message.answer("Выберите проект:", reply_markup=markup)
            await state.set_state(StartTimeEntryForm.project_choice)
        else:
            await message.answer("Проекты не найдены.")
    except Exception as e:
        await message.answer(f"Ошибка при получении проектов: {str(e)}")

@router.message(StartTimeEntryForm.project_choice)
async def process_project_choice_start(message: types.Message, state: FSMContext):
    await state.update_data(project=message.text)
    await message.answer("Введите описание:")
    await state.set_state(StartTimeEntryForm.description)

@router.message(StartTimeEntryForm.description)
async def process_description_start(message: types.Message, state: FSMContext):
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

@router.message(Command('end_time_entry'))
async def cmd_end_time_entry(message: types.Message):
    try:
        time_entry_manager.end_time_entry(clockify_api, message.from_user.username)
        await message.answer("Запись времени успешно завершена.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            await message.answer("Ошибка: Тайм-запись не найдена.")
        else:
            await message.answer(f"Произошла ошибка при завершении записи времени: {e.response.status_code} {e.response.text}")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {str(e)}")

from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    # Состояния для create_time_entry
    email = State()
    api_key = State()
    project_choice = State()
    description = State()
    start_date = State()
    start_time = State()
    end_date = State()
    end_time = State()
    confirm_entry = State()  # Добавлено состояние для подтверждения
    
    # Состояния для start_time_entry
    project_choice_start = State()
    description_start = State()

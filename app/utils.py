from datetime import datetime
import pytz


def convert_to_clockify_format(date_str, time_str):
    # Объединяем DATE и TIME в единый формат
    datetime_str = f"{date_str} {time_str}"
    
    # Преобразуем в объект datetime, формат DD-MM-YYYY HH:MM
    datetime_obj = datetime.strptime(datetime_str, '%d-%m-%Y %H:%M')
    
    # Устанавливаем часовой пояс МСК (Москва)
    moscow_tz = pytz.timezone('Europe/Moscow')
    datetime_obj_msk = moscow_tz.localize(datetime_obj)
    
    # Преобразуем в строку формата ISO 8601, который используется в запросах Clockify
    clockify_format = datetime_obj_msk.isoformat()

    return clockify_format

# Получение текущего времени в формате ISO для Clockify
def get_current_time_in_moscow():
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz)
    return now.isoformat()
# Используем базовый образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml poetry.lock ./

# Устанавливаем Poetry
RUN pip install poetry

# Устанавливаем зависимости через Poetry
RUN poetry install --no-dev

# Копируем все остальные файлы приложения
COPY ./app /app

# Открываем порт, если потребуется взаимодействие через сеть
EXPOSE 8081

# Команда для запуска приложения
CMD ["poetry", "run", "python", "main.py"]

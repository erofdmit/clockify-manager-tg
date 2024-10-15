import sqlite3
import os

# Получаем путь к базе данных из переменной окружения, если она установлена
DATABASE_PATH = os.getenv('DATABASE', 'users.db')

# Создание или подключение к базе данных
def create_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    return conn

# Создание таблицы, если она не существует
def create_table(conn):
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                clockify_userid TEXT PRIMARY KEY,
                clockify_apikey TEXT NOT NULL,
                tg_username TEXT NOT NULL,
                email TEXT NOT NULL
            );
        ''')
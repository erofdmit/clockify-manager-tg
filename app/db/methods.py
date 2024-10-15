# Добавление новой записи
def add_user(conn, clockify_userid, clockify_apikey, tg_username, email):
    with conn:
        conn.execute('''
            INSERT INTO users (clockify_userid, clockify_apikey, tg_username, email)
            VALUES (?, ?, ?, ?)
        ''', (clockify_userid, clockify_apikey, tg_username, email))

# Получение данных по clockify_userid
def get_user_by_clockify_userid(conn, clockify_userid):
    with conn:
        cursor = conn.execute('SELECT * FROM users WHERE clockify_userid = ?', (clockify_userid,))
        return cursor.fetchone()

# Получение данных по clockify_apikey
def get_user_by_clockify_apikey(conn, clockify_apikey):
    with conn:
        cursor = conn.execute('SELECT * FROM users WHERE clockify_apikey = ?', (clockify_apikey,))
        return cursor.fetchone()

# Получение данных по tg_username
def get_user_by_tg_username(conn, tg_username):
    with conn:
        cursor = conn.execute('SELECT * FROM users WHERE tg_username = ?', (tg_username,))
        return cursor.fetchone()

# Получение данных по email
def get_user_by_email(conn, email):
    with conn:
        cursor = conn.execute('SELECT * FROM users WHERE email = ?', (email,))
        return cursor.fetchone()

# Проверка, существует ли пользователь по clockify_userid
def user_exists(conn, clockify_userid):
    with conn:
        cursor = conn.execute('SELECT * FROM users WHERE clockify_userid = ?', (clockify_userid,))
        return cursor.fetchone() is not None
    
 
# Проверка, существует ли пользователь по email
def user_exists_by_email(conn, email):
    with conn:
        cursor = conn.execute('SELECT * FROM users WHERE email = ?', (email,))
        return cursor.fetchone() is not None   
    
# Обновление API-ключа и Telegram-юзернейма по email
def update_user_by_email(conn, email, clockify_apikey, tg_username):
    with conn:
        if user_exists_by_email(conn, email):
            conn.execute('''
                UPDATE users
                SET clockify_apikey = ?, tg_username = ?
                WHERE email = ?
            ''', (clockify_apikey, tg_username, email))
            print(f"Updated user with email: {email}")
        else:
            print(f"User with email {email} does not exist in the database.")
            

# Обновление API-ключа по Telegram-юзернейму
def update_api_key_by_tg_username(conn, tg_username, clockify_apikey):
    with conn:
        cursor = conn.execute('SELECT * FROM users WHERE tg_username = ?', (tg_username,))
        if cursor.fetchone():
            conn.execute('''
                UPDATE users
                SET clockify_apikey = ?
                WHERE tg_username = ?
            ''', (clockify_apikey, tg_username))
            print(f"Updated API key for user with tg_username: {tg_username}")
        else:
            print(f"User with tg_username {tg_username} does not exist in the database.")

            

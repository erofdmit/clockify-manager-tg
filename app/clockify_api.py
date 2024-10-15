import os
import requests
from dotenv import load_dotenv
from utils import get_current_time_in_moscow
from db.engine import create_connection
from db.methods import get_user_by_tg_username, user_exists, add_user
from typing import Optional, List, Dict, Any

# Загрузка API-ключа из файла .env
load_dotenv()

class ClockifyAPI:
    def __init__(self):
        self.api_key: str = os.getenv('CLOCKIFY_API_KEY')
        self.workspace_id: str = os.getenv('WORKSPACE_ID')
        self.base_url: str = f'https://api.clockify.me/api/v1/workspaces/{self.workspace_id}'
        self.headers: Dict[str, str] = {'X-Api-Key': self.api_key}

    def _make_request(self, method: str, endpoint: str, **kwargs: Any) -> Optional[Dict]:
        """Унифицированный метод для выполнения запросов к Clockify API с отладкой."""
        url: str = f'{self.base_url}/{endpoint}'
        try:
            if 'headers' not in kwargs.keys():
                response = requests.request(method, url, headers=self.headers, **kwargs)
            else:
                response = requests.request(method, url, **kwargs)
            if response.status_code in [200, 201]:
                return response.json() if response.content else {}
            else:
                raise requests.exceptions.HTTPError(f"Error {response.status_code}: {response.text}", response=response)
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {str(e)}")
            raise

    def get_workspace_users(self) -> Optional[List[Dict]]:
        """Получение списка пользователей рабочего пространства."""
        return self._make_request('GET', 'users')

    def get_all_projects(self) -> Optional[List[Dict]]:
        """Получение списка всех проектов рабочего пространства."""
        return self._make_request('GET', 'projects')

    def get_project_id_by_name(self, project_name: str) -> Optional[str]:
        """Получение ID проекта по его имени."""
        projects = self.get_all_projects()
        if projects:
            for project in projects:
                if project['name'] == project_name:
                    return project['id']
        print(f"Project {project_name} not found.")
        return None

    def create_time_entry(self, user_api_key: str, clockify_userid: str, start_time: str, 
                          end_time: str, project_id: str, description: str) -> Optional[Dict]:
        """Создание записи времени."""
        url = f'user/{clockify_userid}/time-entries'
        headers = {'X-Api-Key': user_api_key}
        body = {
            "description": description,
            "start": start_time,
            "end": end_time,
            "projectId": project_id
        }
        return self._make_request('POST', url, json=body, headers=headers)

    def start_time_entry(self, user_api_key: str, clockify_userid: str, start_time: str, 
                         project_id: str, description: str) -> Optional[Dict]:
        """Начало новой записи времени."""
        url = f'user/{clockify_userid}/time-entries'
        headers = {'X-Api-Key': user_api_key}
        body = {
            "description": description,
            "start": start_time,
            "projectId": project_id,
            "billable": True
        }
        return self._make_request('POST', url, json=body, headers=headers)

    def end_time_entry(self, user_api_key: str, clockify_userid: str, end_time: str) -> Optional[Dict]:
        """Завершение текущей записи времени."""
        url = f'user/{clockify_userid}/time-entries'
        headers = {'X-Api-Key': user_api_key}
        body = {"end": end_time}
        return self._make_request('PATCH', url, json=body, headers=headers)


class UserManager:
    def __init__(self, db_connection):
        self.conn = db_connection

    def add_new_users_to_db(self, api: ClockifyAPI) -> None:
        """Добавление новых пользователей в базу данных."""
        users = api.get_workspace_users()
        if users:
            for user in users:
                clockify_userid = user['id']
                email = user['email']
                if not user_exists(self.conn, clockify_userid):
                    add_user(self.conn, clockify_userid, 'clockify_apikey_placeholder', 'tg_username_placeholder', email)
                    print(f"Added new user: {email}")
                else:
                    print(f"User {email} already exists in the database.")

    def get_user_projects(self, api: ClockifyAPI, tg_username: str) -> List[str]:
        """Получение списка проектов, в которых участвует пользователь."""
        user = get_user_by_tg_username(self.conn, tg_username)
        if not user:
            print(f"User with tg_username {tg_username} not found.")
            return []

        clockify_userid = user[0]
        projects = api.get_all_projects()
        if projects:
            user_projects = [
                project['name'] for project in projects 
                for membership in project['memberships'] if membership['userId'] == clockify_userid
            ]
            return user_projects
        return []


class TimeEntryManager:
    def __init__(self, db_connection):
        self.conn = db_connection

    def create_time_entry(self, api: ClockifyAPI, tg_username: str, start_time: str, 
                          end_time: str, project_name: str, description: str) -> None:
        """Создание новой записи времени с обработкой ошибок."""
        try:
            user = get_user_by_tg_username(self.conn, tg_username)
            if not user:
                raise ValueError(f"User with tg_username {tg_username} not found.")

            clockify_userid, user_api_key = user[0], user[1]
            project_id = api.get_project_id_by_name(project_name)
            if project_id:
                result = api.create_time_entry(user_api_key, clockify_userid, start_time, end_time, project_id, description)
                if result is None:
                    raise Exception("Ошибка при создании записи времени на Clockify.")
        except Exception as e:
            print(f"Ошибка при создании записи времени: {str(e)}")
            raise

    def start_time_entry(self, api: ClockifyAPI, tg_username: str, project_name: str, description: str) -> None:
        """Начало новой записи времени с обработкой ошибок."""
        try:
            user = get_user_by_tg_username(self.conn, tg_username)
            if not user:
                raise ValueError(f"User with tg_username {tg_username} not found.")

            clockify_userid, user_api_key = user[0], user[1]
            project_id = api.get_project_id_by_name(project_name)
            if project_id:
                start_time = get_current_time_in_moscow()
                result = api.start_time_entry(user_api_key, clockify_userid, start_time, project_id, description)
                if result is None:
                    raise Exception("Ошибка при запуске записи времени на Clockify.")
        except Exception as e:
            print(f"Ошибка при начале записи времени: {str(e)}")
            raise

    def end_time_entry(self, api: ClockifyAPI, tg_username: str) -> None:
        """Завершение записи времени с отладкой ошибок."""
        try:
            user = get_user_by_tg_username(self.conn, tg_username)
            if not user:
                raise ValueError(f"User with tg_username {tg_username} not found.")

            clockify_userid, user_api_key = user[0], user[1]
            end_time = get_current_time_in_moscow()
            result = api.end_time_entry(user_api_key, clockify_userid, end_time)
            if result is None:
                raise Exception("Ошибка при завершении записи времени на Clockify.")
        except Exception as e:
            print(f"Ошибка при завершении записи времени: {str(e)}")
            raise
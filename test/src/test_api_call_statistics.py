from create_application import create_application
import unittest
from src.services.auth_server import AuthServer
import os
from unittest.mock import MagicMock
import requests
from typing import NamedTuple, Dict
from src.services.exceptions.user_already_registered_error import UserAlreadyRegisteredError
from src.database.notifications.postgres_expo_notification_database import PostgresExpoNotificationDatabase
from src.services.media_server import MediaServer
import json
from io import BytesIO

class MockResponse(NamedTuple):
    json_dict: Dict
    status_code: int

    def json(self):
        return self.json_dict

    def raise_for_status(self):
        return None

class TestAppServerStatistics(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["AUTH_ENDPOINT_URL"] = "google.com"
        os.environ["AUTH_SERVER_SECRET"] = "secret"
        os.environ["SERVER_ALIAS"] = "Jenny"
        os.environ["SERVER_HEALTH_ENDPOINT"] = "google.com"
        requests.post = MagicMock(return_value=MockResponse({"api_key": "dummy"}, 200))
        self.notification_database_init = PostgresExpoNotificationDatabase.__init__
        PostgresExpoNotificationDatabase.__init__ = lambda *args, **kwargs: None
        self.app = create_application()
        self.app.testing = True
        self.user_register = AuthServer.user_register
        self.user_login = AuthServer.user_login
        self.profile_query = AuthServer.profile_query
        self.get_logged_email = AuthServer.get_logged_email
        self.send_recovery_email = AuthServer.send_recovery_email
        self.recover_password = AuthServer.recover_password
        self.profile_update = AuthServer.profile_update
        self.delete_video = MediaServer.delete_video
        self.upload_video = MediaServer.upload_video

    def tearDown(self):
        AuthServer.user_register = self.user_register
        AuthServer.user_login = self.user_login
        AuthServer.profile_query = self.profile_query
        AuthServer.get_logged_email = self.get_logged_email
        AuthServer.send_recovery_email = self.send_recovery_email
        AuthServer.recover_password = self.recover_password
        AuthServer.profile_update = self.profile_update
        MediaServer.upload_video = self.upload_video
        MediaServer.delete_video = self.delete_video
        PostgresExpoNotificationDatabase.__init__ = self.notification_database_init

    def test_login_and_get_statistics(self):
        AuthServer.user_login = MagicMock(return_value={"login_token": "asd123"})
        with self.app.test_client() as c:
            response = c.post('/user/login', json={"email": "giancafferata@hotmail.com", "password": "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data)["login_token"], "asd123")
            response = c.post('/user/login', json={"email": "giancafferata@hotmail.com", "password": "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data)["login_token"], "asd123")

            response = c.get('/api_call_statistics')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(sum(json.loads(response.data)["last_30_days_users_logins"].values()), 2)
            self.assertEqual(sum(json.loads(response.data)["last_30_days_api_call_amount"].values()), 2)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_path"]["/user/login"], 2)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_status"]['200'], 2)
            self.assertEqual(len(json.loads(response.data)["last_30_days_api_calls_response_times"]), 2)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_method"]["POST"], 2)
            self.assertEqual(list(json.loads(response.data)["last_30_day_mean_api_call_time"].values())[0],
                             sum(json.loads(response.data)["last_30_days_api_calls_response_times"])/2)

    def test_user_upload_two_videos_and_get_statistics(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo 2", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            response = c.get('/api_call_statistics')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(sum(json.loads(response.data)["last_30_days_uploaded_videos"].values()), 2)
            self.assertEqual(sum(json.loads(response.data)["last_30_days_api_call_amount"].values()), 2)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_path"]["/user/video"], 2)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_status"]['200'], 2)
            self.assertEqual(len(json.loads(response.data)["last_30_days_api_calls_response_times"]), 2)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_method"]["POST"], 2)
            self.assertEqual(list(json.loads(response.data)["last_30_day_mean_api_call_time"].values())[0],
                             sum(json.loads(response.data)["last_30_days_api_calls_response_times"])/2)

    def test_register_and_get_statistics(self):
        AuthServer.user_register = MagicMock(return_value=None)
        with self.app.test_client() as c:
            response = c.post('/user', data={"email": "giancafferata@hotmail.com", "fullname": "Gianmarco Cafferata",
                                             "phone_number": "11 1111-1111", "password": "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user', data={"email": "giancafferata2@hotmail.com", "fullname": "Gianmarco Cafferata",
                                             "phone_number": "11 1111-1111", "password": "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.user_register = MagicMock(return_value=None, side_effect=UserAlreadyRegisteredError)
            response = c.post('/user', data={"email": "giancafferata2@hotmail.com", "fullname": "Gianmarco Cafferata",
                                             "phone_number": "11 1111-1111", "password": "asd123"})
            self.assertEqual(response.status_code, 400)

            response = c.get('/api_call_statistics')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(sum(json.loads(response.data)["last_30_days_user_registrations"].values()), 2)
            self.assertEqual(sum(json.loads(response.data)["last_30_days_api_call_amount"].values()), 3)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_path"]["/user"], 3)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_status"]['200'], 2)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_status"]['400'], 1)
            self.assertEqual(len(json.loads(response.data)["last_30_days_api_calls_response_times"]), 3)
            self.assertEqual(json.loads(response.data)["last_30_days_api_calls_by_method"]["POST"], 3)
            self.assertEqual(list(json.loads(response.data)["last_30_day_mean_api_call_time"].values())[0],
                             sum(json.loads(response.data)["last_30_days_api_calls_response_times"])/3)
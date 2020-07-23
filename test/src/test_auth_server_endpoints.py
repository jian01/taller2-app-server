from create_application import create_application
import unittest
from src.services.auth_server import AuthServer
from src.services.media_server import MediaServer
from src.database.videos.video_database import VideoData
from src.database.videos.video_ram_database import RamVideoDatabase
import os
from unittest.mock import MagicMock
from datetime import datetime
import requests
from typing import NamedTuple, Dict
from src.services.exceptions.invalid_credentials_error import InvalidCredentialsError
from src.services.exceptions.user_already_registered_error import UserAlreadyRegisteredError
from src.services.exceptions.invalid_login_token_error import InvalidLoginTokenError
from src.services.exceptions.unexistent_user_error import UnexistentUserError
from src.services.exceptions.invalid_register_field_error import InvalidRegisterFieldError
from src.services.exceptions.invalid_recovery_token_error import InvalidRecoveryTokenError
from src.services.exceptions.unauthorized_user_error import UnauthorizedUserError
from src.services.exceptions.unexistent_video_error import UnexistentVideoError
from src.services.exceptions.no_more_pages_error import NoMorePagesError
from src.database.notifications.postgres_expo_notification_database import PostgresExpoNotificationDatabase
import json


class MockResponse(NamedTuple):
    json_dict: Dict
    status_code: int

    def json(self):
        return self.json_dict

    def raise_for_status(self):
        return None


class TestAuthServerEndpoints(unittest.TestCase):
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
        self.user_delete = AuthServer.user_delete
        self.delete_video = MediaServer.delete_video
        self.get_registered_users = AuthServer.get_registered_users
        self.list_user_videos = RamVideoDatabase.list_user_videos
        self.set_notification_token = PostgresExpoNotificationDatabase.set_notification_token

    def tearDown(self):
        AuthServer.user_register = self.user_register
        AuthServer.user_login = self.user_login
        AuthServer.profile_query = self.profile_query
        AuthServer.get_logged_email = self.get_logged_email
        AuthServer.send_recovery_email = self.send_recovery_email
        AuthServer.recover_password = self.recover_password
        AuthServer.profile_update = self.profile_update
        AuthServer.user_delete = self.user_delete
        MediaServer.delete_video = self.delete_video
        RamVideoDatabase.list_user_videos = self.list_user_videos
        AuthServer.get_registered_users = self.get_registered_users
        PostgresExpoNotificationDatabase.__init__ = self.notification_database_init
        PostgresExpoNotificationDatabase.set_notification_token = self.set_notification_token

    def test_register_mandatory_fields(self):
        AuthServer.user_register = MagicMock(return_value=None)
        with self.app.test_client() as c:
            response = c.post('/user', data={"email": "giancafferata@hotmail.com", "fullname": "Gianmarco Cafferata",
                                             "password": "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_normal_register(self):
        AuthServer.user_register = MagicMock(return_value=None)
        with self.app.test_client() as c:
            response = c.post('/user', data={"email": "giancafferata@hotmail.com", "fullname": "Gianmarco Cafferata",
                                             "phone_number": "11 1111-1111", "password": "asd123"})
            self.assertEqual(response.status_code, 200)

    def test_already_registered(self):
        AuthServer.user_register = MagicMock(return_value=None, side_effect=UserAlreadyRegisteredError)
        with self.app.test_client() as c:
            response = c.post('/user', data={"email": "giancafferata@hotmail.com", "fullname": "Gianmarco Cafferata",
                                             "phone_number": "11 1111-1111", "password": "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_register_invalid_field(self):
        AuthServer.user_register = MagicMock(return_value=None, side_effect=InvalidRegisterFieldError)
        with self.app.test_client() as c:
            response = c.post('/user', data={"email": "giancafferata@hotmail.com", "fullname": "Gianmarco Cafferata",
                                             "phone_number": "11 1111-1111", "password": "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_login_not_json(self):
        with self.app.test_client() as c:
            response = c.post('/user/login', data={"email": "giancafferata@hotmail.com", "password": "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_login_mandatory_fields(self):
        with self.app.test_client() as c:
            response = c.post('/user/login', json={"password": "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_login_unexistent_user(self):
        AuthServer.user_login = MagicMock(return_value=None, side_effect=UnexistentUserError)
        with self.app.test_client() as c:
            response = c.post('/user/login', json={"email": "giancafferata@hotmail.com", "password": "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_login_ok(self):
        AuthServer.user_login = MagicMock(return_value={"login_token": "asd123"})
        with self.app.test_client() as c:
            response = c.post('/user/login', json={"email": "giancafferata@hotmail.com", "password": "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data)["login_token"], "asd123")

    def test_login_ok_w_notification_token(self):
        AuthServer.user_login = MagicMock(return_value={"login_token": "asd123"})
        mock_set_notification = MagicMock(return_value=None)
        PostgresExpoNotificationDatabase.set_notification_token = mock_set_notification
        with self.app.test_client() as c:
            response = c.post('/user/login', json={"email": "giancafferata@hotmail.com", "password": "asd123",
                                                   "notification_token": "dummy token"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data)["login_token"], "asd123")
            self.assertTrue(mock_set_notification.called)

    def test_login_invalid_credentials(self):
        AuthServer.user_login = MagicMock(return_value=None, side_effect=InvalidCredentialsError)
        with self.app.test_client() as c:
            response = c.post('/user/login', json={"email": "giancafferata@hotmail.com", "password": "asd123"})
            self.assertEqual(response.status_code, 403)

    def test_profile_query_ok(self):
        AuthServer.profile_query = MagicMock(return_value=None)
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.get('/user', query_string={"email": "asd@asd.com"})
            self.assertEqual(response.status_code, 200)

    def test_profile_query_missing_email(self):
        AuthServer.profile_query = MagicMock(return_value=None)
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.get('/user')
            self.assertEqual(response.status_code, 400)

    def test_profile_query_unexistant_user(self):
        AuthServer.profile_query = MagicMock(return_value=None, side_effect=UnexistentUserError)
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.get('/user', query_string={"email": "asd@asd.com"})
            self.assertEqual(response.status_code, 404)

    def test_send_recovery_email_not_json(self):
        with self.app.test_client() as c:
            response = c.post('/user/recover_password', data={"email": "giancafferata@hotmail.com"})
            self.assertEqual(response.status_code, 400)

    def test_send_recovery_email_missing_field(self):
        with self.app.test_client() as c:
            response = c.post('/user/recover_password', json={})
            self.assertEqual(response.status_code, 400)

    def test_send_recovery_email_unexistent_user(self):
        AuthServer.send_recovery_email = MagicMock(return_value=None, side_effect=UnexistentUserError)
        with self.app.test_client() as c:
            response = c.post('/user/recover_password', json={"email": "giancafferata@hotmail.com"})
            self.assertEqual(response.status_code, 404)

    def test_send_recovery_email_ok(self):
        AuthServer.send_recovery_email = MagicMock(return_value=None)
        with self.app.test_client() as c:
            response = c.post('/user/recover_password', json={"email": "giancafferata@hotmail.com"})
            self.assertEqual(response.status_code, 200)

    def test_users_recover_password_not_json(self):
        with self.app.test_client() as c:
            response = c.post('/user/new_password', data={"email": "giancafferata@hotmail.com"})
            self.assertEqual(response.status_code, 400)

    def test_users_recover_password_missing_field(self):
        with self.app.test_client() as c:
            response = c.post('/user/new_password', json={})
            self.assertEqual(response.status_code, 400)

    def test_users_recover_password_unexistent_user(self):
        AuthServer.recover_password = MagicMock(return_value=None, side_effect=UnexistentUserError)
        with self.app.test_client() as c:
            response = c.post('/user/new_password', json={"email": "giancafferata@hotmail.com",
                                                          "token": "dummy", "new_password": "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_users_recover_password_invalid_token(self):
        AuthServer.recover_password = MagicMock(return_value=None, side_effect=InvalidRecoveryTokenError)
        with self.app.test_client() as c:
            response = c.post('/user/new_password', json={"email": "giancafferata@hotmail.com",
                                                          "token": "dummy", "new_password": "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_users_recover_password_ok(self):
        AuthServer.recover_password = MagicMock(return_value=None)
        with self.app.test_client() as c:
            response = c.post('/user/new_password', json={"email": "giancafferata@hotmail.com",
                                                          "token": "dummy", "new_password": "asd123"})
            self.assertEqual(response.status_code, 200)

    def test_user_update_without_authentication(self):
        with self.app.test_client() as c:
            response = c.put('/user', query_string={"email": "caropistillo@gmail.com"}, data='')
            self.assertEqual(response.status_code, 401)

    def test_user_update_for_missing_fields_error(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.put('/user', query_string={"fullname": "Carolina"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_update_for_unauthorized_auth_server(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.profile_update = MagicMock(return_value=None, side_effect=UnauthorizedUserError)
        with self.app.test_client() as c:
            response = c.put('/user', query_string={"email": "asd@asd.com"},
                             data={"fullname": "Carolina Pistillo", "phone_number": "11 1111-1111",
                                   "password": "carolina"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 403)

    def test_user_update_for_non_existing_user_error(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.profile_update = MagicMock(return_value=None, side_effect=UnexistentUserError)
        with self.app.test_client() as c:
            response = c.put('/user', query_string={"email": "asd@asd.com"},
                             data={"fullname":"Carolina Pistillo", "phone_number":"11 1111-1111",
                                "password":"carolina"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_user_update_success(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.profile_update = MagicMock(return_value=None)
        with self.app.test_client() as c:
            response = c.put('/user', query_string={"email": "asd@asd.com"},
                             data={"fullname": "Carolina Pistillo", "phone_number": "11 3263-7625",
                                   "password": "carolina"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

    def test_user_delete_invalid_login_token(self):
        AuthServer.get_logged_email = MagicMock(return_value=None, side_effect=InvalidLoginTokenError)
        AuthServer.user_delete = MagicMock(return_value=None)
        MediaServer.delete_video = MagicMock(return_value=None, side_effect=UnexistentVideoError)
        RamVideoDatabase.list_user_videos = MagicMock(return_value=[])
        with self.app.test_client() as c:
            response = c.delete('/user', query_string={"email": "asd@asd.com"},
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 401)

    def test_user_delete_missing_params(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.user_delete = MagicMock(return_value=None)
        MediaServer.delete_video = MagicMock(return_value=None, side_effect=UnexistentVideoError)
        RamVideoDatabase.list_user_videos = MagicMock(return_value=[])
        with self.app.test_client() as c:
            response = c.delete('/user', headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_delete_unauthorized(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.user_delete = MagicMock(return_value=None, side_effect=UnauthorizedUserError)
        MediaServer.delete_video = MagicMock(return_value=None, side_effect=UnexistentVideoError)
        RamVideoDatabase.list_user_videos = MagicMock(return_value=[])
        with self.app.test_client() as c:
            response = c.delete('/user', query_string={"email": "asd@asd.com"},
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 403)

    def test_user_delete_unexistent(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.user_delete = MagicMock(return_value=None, side_effect=UnexistentUserError)
        delete_video_mock = MagicMock(return_value=None, side_effect=UnexistentVideoError)
        MediaServer.delete_video = delete_video_mock
        RamVideoDatabase.list_user_videos = MagicMock(return_value=[])
        with self.app.test_client() as c:
            response = c.delete('/user', query_string={"email": "asd@asd.com"},
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_user_delete_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.user_delete = MagicMock(return_value=None)
        delete_video_mock = MagicMock(return_value=None, side_effect=UnexistentVideoError)
        MediaServer.delete_video = delete_video_mock
        RamVideoDatabase.list_user_videos = MagicMock(
            return_value=[(VideoData(title="Titulo", description="Descripcion coso",
                                     creation_time=datetime.now(), visible=True,
                                     location="Buenos Aires", file_location="file_location"), {})])
        with self.app.test_client() as c:
            response = c.delete('/user', query_string={"email": "asd@asd.com"},
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(delete_video_mock.called)

    def test_user_delete_no_videos(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.user_delete = MagicMock(return_value=None)
        delete_video_mock = MagicMock(return_value=None)
        MediaServer.delete_video = delete_video_mock
        RamVideoDatabase.list_user_videos = MagicMock(return_value=[])
        with self.app.test_client() as c:
            response = c.delete('/user', query_string={"email": "asd@asd.com"},
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertFalse(delete_video_mock.called)

    def test_get_registered_users_missing_params(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.get_registered_users = MagicMock(return_value=None)
        with self.app.test_client() as c:
            response = c.get('/users', query_string={"page": 1},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_get_registered_users_unauthorized(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.get_registered_users = MagicMock(return_value=None, side_effect=UnauthorizedUserError)
        with self.app.test_client() as c:
            response = c.get('/users', query_string={"page": 1, "users_per_page":2},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 403)

    def test_get_registered_users_no_more_pages(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.get_registered_users = MagicMock(return_value=None, side_effect=NoMorePagesError)
        with self.app.test_client() as c:
            response = c.get('/users', query_string={"page": 1, "users_per_page":2},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_get_registered_users_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.get_registered_users = MagicMock(return_value=None)
        with self.app.test_client() as c:
            response = c.get('/users', query_string={"page": 1, "users_per_page":2},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
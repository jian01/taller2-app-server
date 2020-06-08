from src.services.auth_server import AuthServer
import unittest
import os
from unittest.mock import MagicMock
import requests
from requests import Response
from typing import NamedTuple, Dict
from src.services.exceptions.invalid_credentials_error import InvalidCredentialsError
from src.services.exceptions.user_already_registered_error import UserAlreadyRegisteredError
from src.services.exceptions.invalid_login_token_error import InvalidLoginTokenError
from src.services.exceptions.unexistent_user_error import UnexistentUserError
from src.services.exceptions.invalid_register_field_error import InvalidRegisterFieldError
from src.model.photo import Photo

class MockResponse(NamedTuple):
    json_dict: Dict
    status_code: int

    def json(self):
        return self.json_dict

    def raise_for_status(self):
        return None

class TestAuthServer(unittest.TestCase):
    def setUp(self):
        os.environ["AUTH_ENDPOINT_URL"] = "google.com"
        os.environ["AUTH_SERVER_SECRET"] = "secret"
        os.environ["SERVER_ALIAS"] = "Jenny"
        os.environ["SERVER_HEALTH_ENDPOINT"] = "google.com"
        self.post = requests.post
        self.get = requests.get
        requests.post = MagicMock(return_value=MockResponse({"api_key": "dummy"}, 200))
        self.auth_server = AuthServer(auth_server_url_env_name="AUTH_ENDPOINT_URL",
                                      auth_server_secret_env_name="AUTH_SERVER_SECRET",
                                      server_alias_env_name="SERVER_ALIAS",
                                      server_health_endpoint_url_env_name="SERVER_HEALTH_ENDPOINT")

    def tearDown(self):
        requests.post = self.post
        requests.get = self.get

    def test_valid_login(self):
        requests.post = MagicMock(return_value=MockResponse({"login_token": "dummy"}, 200))
        self.assertEqual(self.auth_server.user_login("email@email.com", "asd123"), "dummy")

    def test_invalid_login(self):
        requests.post = MagicMock(return_value=MockResponse({"login_token": "dummy"}, 403))
        with self.assertRaises(InvalidCredentialsError):
            self.auth_server.user_login("email@email.com", "asd123")

    def test_get_logged_user(self):
        requests.get = MagicMock(return_value=MockResponse({"email": "asd@asd.com"}, 200))
        self.assertEqual(self.auth_server.get_logged_email("dummy token"), "asd@asd.com")

    def test_get_logged_user_invalid_token(self):
        requests.get = MagicMock(return_value=MockResponse({"email": "asd@asd.com"}, 401))
        with self.assertRaises(InvalidLoginTokenError):
            self.auth_server.get_logged_email("dummy token")

    def test_user_registration(self):
        requests.post = MagicMock(return_value=MockResponse({}, 200))
        self.auth_server.user_register(email="asd@asd.com", fullname="Jorge", plain_password="asd123",
                                       phone_number="1111", photo=Photo())

    def test_user_registration_user_already_registered(self):
        requests.post = MagicMock(return_value=MockResponse({"message": "User with email asd@asd.com is already registered"}, 400))
        with self.assertRaises(UserAlreadyRegisteredError):
            self.auth_server.user_register(email="asd@asd.com", fullname="Jorge", plain_password="asd123",
                                           phone_number="1111", photo=Photo())

    def test_user_registration_invalid_register_field(self):
        requests.post = MagicMock(return_value=MockResponse({"message": "Invalid phone number"}, 400))
        with self.assertRaises(InvalidRegisterFieldError):
            self.auth_server.user_register(email="asd@asd.com", fullname="Jorge", plain_password="asd123",
                                           phone_number="1111", photo=Photo())



from create_application import create_application
import unittest
from src.services.auth_server import AuthServer
from src.database.friends.friend_database import FriendDatabase
from src.database.friends.ram_friend_database import RamFriendDatabase
from src.database.friends.exceptions.unexistent_requestor_user_error import UnexistentRequestorUserError
from src.database.friends.exceptions.unexistent_target_user_error import UnexistentTargetUserError
from src.database.friends.exceptions.unexistent_friend_requests import UnexistentFriendRequest
import os
from unittest.mock import MagicMock
import requests
from typing import NamedTuple, Dict
import json
import time

class MockResponse(NamedTuple):
    json_dict: Dict
    status_code: int

    def json(self):
        return self.json_dict

    def raise_for_status(self):
        return None

class TestMessagesEndpoints(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["AUTH_ENDPOINT_URL"] = "google.com"
        os.environ["AUTH_SERVER_SECRET"] = "secret"
        os.environ["SERVER_ALIAS"] = "Jenny"
        os.environ["SERVER_HEALTH_ENDPOINT"] = "google.com"
        os.environ["MEDIA_ENDPOINT_URL"] = "google.com"
        requests.post = MagicMock(return_value=MockResponse({"api_key": "dummy"}, 200))
        self.app = create_application()
        self.app.testing = True
        self.get_logged_email = AuthServer.get_logged_email
        self.profile_query = AuthServer.profile_query
        self.create_friend_request = RamFriendDatabase.create_friend_request
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/user/friend_request/accept', json={"other_user_email": "asd@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
            response = c.post('/user/friend_request', json={"other_user_email": "gian2@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="gian2@asd.com")
            response = c.post('/user/friend_request/accept', json={"other_user_email": "asd@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

    def tearDown(self):
        AuthServer.get_logged_email = self.get_logged_email
        AuthServer.profile_query = self.profile_query
        RamFriendDatabase.create_friend_request = self.create_friend_request

    def test_send_message_not_json(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/message', data={"other_user_email": "gian@asd.com",
                                                     "message": "Hola"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_send_message_missing_params(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/message', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_send_message_not_friends_forbidden(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/message', json={"other_user_email": "piba_random@asd.com",
                                                     "message": "ola chikitah me gusto mucho tu video"
                                                                "haces algo hoy?"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 403)

    def test_get_messages_missing_params(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.get('/user/messages_with', query_string={"other_user_email": "gian@asd.com",
                                                                  "page": 0},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_get_messages_no_more_pages(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.get('/user/messages_with', query_string={"other_user_email": "gian@asd.com",
                                                                  "page": 2, "per_page":10},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_get_messages_no_messages_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.get('/user/messages_with', query_string={"other_user_email": "gian@asd.com",
                                                                  "page": 0, "per_page":10},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

    def test_send_and_get_messages(self):
        with self.app.test_client() as c:
            AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
            response = c.post('/user/message', json={"other_user_email": "gian@asd.com",
                                                     "message": "hola"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/user/message', json={"other_user_email": "asd@asd.com",
                                                     "message": "hola"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
            response = c.post('/user/message', json={"other_user_email": "gian@asd.com",
                                                     "message": "ke ondis, salen esas ricardas nudes?"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/user/message', json={"other_user_email": "asd@asd.com",
                                                     "message": "dale"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            response = c.get('/user/messages_with', query_string={"other_user_email": "asd@asd.com",
                                                                  "page": 1, "per_page":2},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            messages = json.loads(response.data)
            self.assertEqual(len(messages["messages"]), 2)
            self.assertEqual(messages["pages"], 2)
            self.assertEqual(messages["messages"][0]["message"], "dale")
            self.assertEqual(messages["messages"][1]["message"], "ke ondis, salen esas ricardas nudes?")

            response = c.get('/user/messages_with', query_string={"other_user_email": "asd@asd.com",
                                                                  "page": 2, "per_page":2},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            messages = json.loads(response.data)
            self.assertEqual(len(messages["messages"]), 2)
            self.assertEqual(messages["pages"], 2)
            self.assertEqual(messages["messages"][0]["message"], "hola")
            self.assertEqual(messages["messages"][0]["from_user"], "gian@asd.com")
            self.assertEqual(messages["messages"][1]["message"], "hola")

    def test_send_and_get_conversations(self):
        with self.app.test_client() as c:
            # Conversacion 1
            AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
            response = c.post('/user/message', json={"other_user_email": "gian@asd.com",
                                                     "message": "hola"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/user/message', json={"other_user_email": "asd@asd.com",
                                                     "message": "hola"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
            response = c.post('/user/message', json={"other_user_email": "gian@asd.com",
                                                     "message": "ke ondis, salen esas ricardas nudes?"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/user/message', json={"other_user_email": "asd@asd.com",
                                                     "message": "dale"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            # Conversacion 2
            AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
            response = c.post('/user/message', json={"other_user_email": "gian2@asd.com",
                                                     "message": "keres venir a jugar al uno?"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/message', json={"other_user_email": "gian2@asd.com",
                                                     "message": "pero uno encima del otro"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)


            response = c.get('/user/last_conversations',
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            last_conv = json.loads(response.data)
            self.assertEqual(last_conv[0]["user"]["email"], "gian2@asd.com")
            self.assertEqual(last_conv[0]["last_message"]["message"], "pero uno encima del otro")
            self.assertEqual(last_conv[1]["user"]["email"], "gian@asd.com")
            self.assertEqual(last_conv[1]["last_message"]["message"], "dale")





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

class TestAuthServerEndpoints(unittest.TestCase):
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

    def tearDown(self):
        AuthServer.get_logged_email = self.get_logged_email
        AuthServer.profile_query = self.profile_query
        RamFriendDatabase.create_friend_request = self.create_friend_request

    def test_user_friend_request_without_authentication(self):
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', data={})
            self.assertEqual(response.status_code, 401)

    def test_user_friend_request_not_json(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', data={"other_user_email": "asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_friend_request_missing_target_email(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', json={"user_email": "asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_friend_request_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

    def test_user_friend_request_unexistent_requestor(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        RamFriendDatabase.create_friend_request = MagicMock(return_value="",side_effect=UnexistentRequestorUserError)
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 500)

    def test_user_friend_request_unexistent_target(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        RamFriendDatabase.create_friend_request = MagicMock(return_value="",side_effect=UnexistentTargetUserError)
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_user_friend_request_and_query_requests(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.profile_query = MagicMock(return_value={"email": "gian@asd.com",
                                                           "fullname": "Gianmarco",
                                                           "password": "asd123",
                                                           "phone_number": "1111",
                                                           "photo": ""})
        with self.app.test_client() as c:
            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.get('/user/friend_requests',
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)),0)
            AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
            response = c.post('/user/friend_request', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.get('/user/friend_requests',
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)),1)

    def test_user_accept_friend_request_without_authentication(self):
        with self.app.test_client() as c:
            response = c.post('/user/friend_request/accept', data={})
            self.assertEqual(response.status_code, 401)

    def test_user_accept_friend_request_not_json(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request/accept', data={"other_user_email": "asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_accept_friend_request_missing_target_email(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request/accept', json={"user_email": "asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_accept_friend_request_unexistent_friend_request(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request/accept', json={"other_user_email": "asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_user_reject_friend_request_without_authentication(self):
        with self.app.test_client() as c:
            response = c.post('/user/friend_request/reject', data={})
            self.assertEqual(response.status_code, 401)

    def test_user_reject_friend_request_not_json(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request/reject', data={"other_user_email": "asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_reject_friend_request_missing_target_email(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request/reject', json={"user_email": "asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_reject_friend_request_unexistent_friend_request(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/friend_request/reject', json={"other_user_email": "asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_user_accept_friend_request_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.profile_query = MagicMock(return_value={"email": "gian@asd.com",
                                                           "fullname": "Gianmarco",
                                                           "password": "asd123",
                                                           "phone_number": "1111",
                                                           "photo": ""})
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/user/friend_request/accept', json={"other_user_email": "asd@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.get('/user/friend_requests',
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)),0)
            response = c.get('/user/friends', query_string={"email": "asd@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)),1)
            response = c.get('/user/friends', query_string={"email": "gian@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)),1)

    def test_user_reject_friend_request_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.profile_query = MagicMock(return_value={"email": "gian@asd.com",
                                                           "fullname": "Gianmarco",
                                                           "password": "asd123",
                                                           "phone_number": "1111",
                                                           "photo": ""})
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/user/friend_request/reject', json={"other_user_email": "asd@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.get('/user/friend_requests',
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)),0)

    def test_user_list_friends_missing_fields(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.get('/user/friends', query_string={},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_list_friends_not_authorized(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.get('/user/friends', query_string={"email": "gian@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 403)

    def test_user_friend_request_users_already_friends(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        AuthServer.profile_query = MagicMock(return_value={"email": "gian@asd.com",
                                                           "fullname": "Gianmarco",
                                                           "password": "asd123",
                                                           "phone_number": "1111",
                                                           "photo": ""})
        with self.app.test_client() as c:
            response = c.post('/user/friend_request', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/user/friend_request/accept', json={"other_user_email": "asd@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/friend_request', json={"other_user_email": "asd@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)
            AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
            response = c.post('/user/friend_request', json={"other_user_email": "gian@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

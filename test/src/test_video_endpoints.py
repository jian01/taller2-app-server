from create_application import create_application
import unittest
from src.services.media_server import MediaServer
from src.services.auth_server import AuthServer
from src.services.exceptions.invalid_video_format_error import InvalidVideoFormatError
import os
from unittest.mock import MagicMock
import requests
from typing import NamedTuple, Dict
from io import BytesIO
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
        os.environ["MEDIA_ENDPOINT_URL"] = "google.com"
        requests.post = MagicMock(return_value=MockResponse({"api_key": "dummy"}, 200))
        self.app = create_application()
        self.app.testing = True
        self.get_logged_email = AuthServer.get_logged_email
        self.upload_video = MediaServer.upload_video

    def tearDown(self):
        MediaServer.upload_video = self.upload_video
        AuthServer.get_logged_email = self.get_logged_email

    def test_user_upload_video_without_authentication(self):
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "caropistillo@gmail.com"}, data={})
            self.assertEqual(response.status_code, 401)

    def test_user_upload_video_missing_fields_error(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "file": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_upload_video_unauthorized_token(self):
        AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","file": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 403)

    def test_user_upload_video_invalid_format(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="", side_effects=InvalidVideoFormatError)
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","file": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_upload_video_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

    def test_user_upload_two_videos_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            id1 = json.loads(response.data)["id"]
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo 2", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            id2 = json.loads(response.data)["id"]
            self.assertLess(id1, id2)
            self.assertTrue(id1 != id2)
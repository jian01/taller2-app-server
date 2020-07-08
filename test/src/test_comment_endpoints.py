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
import time

class MockResponse(NamedTuple):
    json_dict: Dict
    status_code: int

    def json(self):
        return self.json_dict

    def raise_for_status(self):
        return None

class TestCommentEndpoints(unittest.TestCase):
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
        self.profile_query = AuthServer.profile_query

    def tearDown(self):
        MediaServer.upload_video = self.upload_video
        AuthServer.get_logged_email = self.get_logged_email
        AuthServer.profile_query = self.profile_query

    def test_comment_video_not_json(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/videos/comment', data={"target_email": "asd@asd.com",
                                                       "video_title": "Hola",
                                                       "comment": "Asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_comment_video_missing_fields(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/videos/comment', json={"target_email": "asd@asd.com",
                                                       "video_title": "Hola"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_get_video_comments_missing_fields(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.get('/videos/comments', query_string={"other_user_email": "asd@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_comment_video_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/videos/comment', json={"target_email": "asd@asd.com",
                                                       "video_title": "Hola",
                                                       "comment": "Asd"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/videos/comment', json={"target_email": "asd@asd.com",
                                                       "video_title": "Hola",
                                                       "comment": "Asd2"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.get('/videos/comments', query_string={"other_user_email": "asd@asd.com",
                                                               "video_title": "Hola"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            comments_data = json.loads(response.data)
            assert len(comments_data) == 2
            assert comments_data[0]["user"]["email"] == "asd@asd.com"
            assert comments_data[0]["comment"]["content"] == "Asd2"
            assert comments_data[1]["user"]["email"] == "asd@asd.com"
            assert comments_data[1]["comment"]["content"] == "Asd"
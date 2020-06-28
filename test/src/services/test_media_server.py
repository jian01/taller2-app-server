from src.services.media_server import MediaServer
import unittest
import os
from unittest.mock import MagicMock
import requests
from typing import NamedTuple, Dict
from io import BytesIO

from src.services.exceptions.unexistent_video_error import UnexistentVideoError
from src.services.exceptions.invalid_video_format_error import InvalidVideoFormatError

class MockResponse(NamedTuple):
    json_dict: Dict
    status_code: int

    def json(self):
        return self.json_dict

    def raise_for_status(self):
        return None

class TestAuthServer(unittest.TestCase):
    def setUp(self):
        os.environ["MEDIA_ENDPOINT_URL"] = "google.com"
        self.post = requests.post
        self.delete = requests.delete
        requests.post = MagicMock(return_value=MockResponse({"api_key": "dummy"}, 200))
        self.media_server = MediaServer(media_server_url_env_name="MEDIA_ENDPOINT_URL")

    def tearDown(self):
        requests.post = self.post
        requests.delete = self.delete

    def test_upload_video_invalid_format(self):
        requests.post = MagicMock(return_value=MockResponse({}, 400))
        with self.assertRaises(InvalidVideoFormatError):
            self.media_server.upload_video(user_email="asd@asd.com",
                                           title="dummy",
                                           video=BytesIO())

    def test_upload_video_ok(self):
        requests.post = MagicMock(return_value=MockResponse({}, 200))
        self.media_server.upload_video(user_email="asd@asd.com",title="dummy",video=BytesIO())

    def test_delete_video_unexistent(self):
        requests.delete = MagicMock(return_value=MockResponse({}, 404))
        with self.assertRaises(UnexistentVideoError):
            self.media_server.delete_video(user_email="asd@asd.com", title="dummy")

    def test_delete_video_ok(self):
        requests.delete = MagicMock(return_value=MockResponse({}, 200))
        self.media_server.delete_video(user_email="asd@asd.com", title="dummy")

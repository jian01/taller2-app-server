from create_application import create_application
import unittest
from src.services.media_server import MediaServer
from src.services.auth_server import AuthServer
from src.services.exceptions.invalid_video_format_error import InvalidVideoFormatError
from src.services.exceptions.unexistent_video_error import UnexistentVideoError
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

class TestVideoEndpoints(unittest.TestCase):
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
        self.delete_video = MediaServer.delete_video

    def tearDown(self):
        MediaServer.upload_video = self.upload_video
        AuthServer.get_logged_email = self.get_logged_email
        AuthServer.profile_query = self.profile_query
        MediaServer.delete_video = self.delete_video

    def test_user_upload_video_without_authentication(self):
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "caropistillo@gmail.com"}, data={})
            self.assertEqual(response.status_code, 401)

    def test_user_upload_video_missing_email_error(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/video',
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_upload_video_missing_fields_error(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_upload_video_invalid_format(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="", side_effect=InvalidVideoFormatError)
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
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
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo 2", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

    def test_user_list_videos_without_authentication(self):
        with self.app.test_client() as c:
            response = c.get('/user/videos', query_string={"email": "asd@asd.com"})
            self.assertEqual(response.status_code, 401)

    def test_user_list_videos_missing_email(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        with self.app.test_client() as c:
            response = c.get('/user/videos', headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_upload_two_videos_and_list(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            time.sleep(0.5)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo 2", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.get('/user/videos', query_string={"email": "asd@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)), 2)
            self.assertEqual(json.loads(response.data)[0]["video"]["title"], "Titulo 2")
            self.assertEqual(json.loads(response.data)[1]["video"]["title"], "Titulo")

    def test_video_delete_missing_params(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            time.sleep(0.5)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo 2", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.delete('/user/video',
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_video_delete_unexistent_video(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            time.sleep(0.5)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo 2", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            MediaServer.delete_video = MagicMock(return_value=None, side_effect=UnexistentVideoError)
            response = c.delete('/user/video', query_string={"video_title": "asd"},
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 404)

    def test_video_delete_video_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        MediaServer.delete_video = MagicMock(return_value=None)
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            time.sleep(0.5)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo 2", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.delete('/user/video', query_string={"video_title": "Titulo 2"},
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.get('/user/videos', query_string={"email": "asd@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)), 1)
            self.assertEqual(json.loads(response.data)[0]["video"]["title"], "Titulo")

    def test_user_upload_two_videos_one_private(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            time.sleep(0.5)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Titulo 2", "location": "Buenos Aires",
                                    "visible":"false","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.get('/user/videos', query_string={"email": "asd@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)), 1)
            self.assertEqual(json.loads(response.data)[0]["video"]["title"], "Titulo")
            AuthServer.profile_query = MagicMock(return_value={"Name": "Gianmarco"})
            response = c.get('/videos/top')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)), 1)

    def test_user_search_missing_params(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.get('/videos/search',
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_user_upload_videos_and_search(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola como", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola como estas", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola estas como", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Nada", "location": "Buenos Aires",
                                    "visible":"true", "description": "Hola",
                              "video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.get('/videos/search', query_string={"query": "hola como estas"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(len(data), 5)
            self.assertEqual(data[0]["video"]["title"], "Hola como estas")
            self.assertEqual(data[1]["video"]["title"], "Hola como")
            self.assertEqual(data[2]["video"]["title"], "Hola estas como")
            self.assertEqual(data[3]["video"]["title"], "Hola")
            self.assertEqual(data[4]["video"]["title"], "Nada")

    def test_video_reaction_not_json(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola como", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/videos/reaction', data={"target_email": "asd@asd.com"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_video_reaction_not_all_fields(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola como", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/videos/reaction', json={"target_email": "asd@asd.com",
                                                   "video_title": "Hola"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_video_reaction_invalid(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola como", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/videos/reaction', json={"target_email": "asd@asd.com",
                                                   "video_title": "Hola",
                                                   "reaction": "love"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_get_video_reaction_missing_params(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.get('/videos/reaction', query_string={"target_email": "asd@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_video_reaction_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/videos/reaction', json={"target_email": "asd@asd.com",
                                                   "video_title": "Hola",
                                                   "reaction": "dislike"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            response = c.get('/user/videos', query_string={"email": "asd@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)), 1)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["like"], 0)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["dislike"], 1)

            response = c.post('/videos/reaction', json={"target_email": "asd@asd.com",
                                                   "video_title": "Hola",
                                                   "reaction": "like"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            AuthServer.get_logged_email = MagicMock(return_value="gian2@asd.com")

            response = c.get('/videos/reaction', query_string={"target_email": "asd@asd.com",
                                                               "video_title": "Hola"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data)["reaction"], None)

            response = c.post('/videos/reaction', json={"target_email": "asd@asd.com",
                                                   "video_title": "Hola",
                                                   "reaction": "like"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            response = c.get('/videos/reaction', query_string={"target_email": "asd@asd.com",
                                                               "video_title": "Hola"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data)["reaction"], "like")

            response = c.get('/user/videos', query_string={"email": "asd@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)), 1)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["like"], 2)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["dislike"], 0)
            response = c.get('/videos/top')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["like"], 2)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["dislike"], 0)
            response = c.get('/videos/search', query_string={"query": "hola"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["like"], 2)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["dislike"], 0)

    def test_video_reaction_delete_not_json(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola como", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.delete('/videos/reaction', data={"target_email": "asd@asd.com"},
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_video_reaction_delete_not_all_fields(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola como", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            response = c.delete('/videos/reaction', json={"target_email": "asd@asd.com"},
                                headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 400)

    def test_video_reaction_delete_ok(self):
        AuthServer.get_logged_email = MagicMock(return_value="asd@asd.com")
        MediaServer.upload_video = MagicMock(return_value="")
        with self.app.test_client() as c:
            response = c.post('/user/video', query_string={"email": "asd@asd.com"},
                              data={"title": "Hola", "location": "Buenos Aires",
                                    "visible":"true","video": (BytesIO(), 'video')},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            AuthServer.get_logged_email = MagicMock(return_value="gian@asd.com")
            response = c.post('/videos/reaction', json={"target_email": "asd@asd.com",
                                                   "video_title": "Hola",
                                                   "reaction": "dislike"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            response = c.delete('/videos/reaction', json={"target_email": "asd@asd.com",
                                                       "video_title": "Hola"},
                              headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)

            response = c.get('/user/videos', query_string={"email": "asd@asd.com"},
                             headers={"Authorization": "Bearer %s" % "asd123"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(json.loads(response.data)), 1)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["like"], 0)
            self.assertEqual(json.loads(response.data)[0]["reactions"]["dislike"], 0)
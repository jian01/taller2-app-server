from create_application import create_application
import unittest
import os
from unittest.mock import MagicMock
import requests
from typing import NamedTuple, Dict
from src.database.notifications.postgres_expo_notification_database import PostgresExpoNotificationDatabase

class MockResponse(NamedTuple):
    json_dict: Dict
    status_code: int

    def json(self):
        return self.json_dict

    def raise_for_status(self):
        return None

class TestFlaskDummy(unittest.TestCase):
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

    def tearDown(self) -> None:
        PostgresExpoNotificationDatabase.__init__ = self.notification_database_init

    def test_api_health(self):
        with self.app.test_client() as c:
            response = c.get('/health')
            self.assertEqual(response.status_code, 200)

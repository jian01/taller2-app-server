from src.database.notifications.postgres_expo_notification_database import PostgresExpoNotificationDatabase
from src.database.statistics.statistics_database import ApiCall
from datetime import datetime
import pytest
import psycopg2
from typing import NamedTuple
import requests
import os
from io import BytesIO
from src.database.utils.postgres_connection import PostgresUtils

class FakePostgres(NamedTuple):
    closed: int

class MockResponse:
    def __init__(self, response):
        self.response = response

    def json(self):
        return self.response

    def raise_for_status(self):
        return

def create_mock_response(calls, response):
    calls.append(response)
    return MockResponse(response)

@pytest.fixture(scope="function")
def notifications_postgres_database(monkeypatch, postgresql):
    os.environ["DUMB_ENV_NAME"] = "{}"
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(0))
    monkeypatch.setattr(PostgresUtils, "get_postgres_connection",
                        lambda *args, **kwargs: psycopg2.connect(*args, **kwargs))
    database = PostgresExpoNotificationDatabase(*(["DUMB_ENV_NAME"] * 5))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)
    with open("test/src/database/notifications_database/config/initialize_db.sql", "r") as initialize_query:
        cursor = postgresql.cursor()
        cursor.execute(initialize_query.read())
        postgresql.commit()
        cursor.close()
    database.conn = postgresql
    database.notification_tokens_table_name = "chotuve.user_notification_tokens"
    yield database
    postgresql.close()

def test_postgres_connection_error(monkeypatch, notifications_postgres_database):
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(1))
    with pytest.raises(ConnectionError):
        database = PostgresExpoNotificationDatabase(*(["DUMB_ENV_NAME"] * 5))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)

def test_set_notification_tokens(monkeypatch, notifications_postgres_database):
    notifications_postgres_database.set_notification_token('giancafferata@hotmail.com', "dummy")
    notifications_postgres_database.set_notification_token('giancafferata@hotmail.com', "dummy1")
    notifications_postgres_database.set_notification_token('cafferatagian@hotmail.com', "dummy2")
    notifications_postgres_database.set_notification_token('asd@asd.com', "dummy3")
    monkeypatch.setattr(PostgresExpoNotificationDatabase, "safe_query_run", AttributeError)
    notifications_postgres_database.set_notification_token('giancafferata@hotmail.com', "dummy5")
    cursor = notifications_postgres_database.conn.cursor()
    cursor.execute("SELECT * FROM chotuve.user_notification_tokens")
    results = cursor.fetchall()
    for r in results:
        if r[0] == 'giancafferata@hotmail.com':
            assert r[1] == "dummy1"
            continue
        if r[0] == 'cafferatagian@hotmail.com':
            assert r[1] == "dummy2"
            continue
        if r[0] == 'asd@asd.com':
            assert r[1] == "dummy3"
            continue
        assert False

def test_set_notification_tokens_delete_previous(monkeypatch, notifications_postgres_database):
    notifications_postgres_database.set_notification_token('giancafferata@hotmail.com', "dummy1")
    notifications_postgres_database.set_notification_token('cafferatagian@hotmail.com', "dummy1")
    cursor = notifications_postgres_database.conn.cursor()
    cursor.execute("SELECT * FROM chotuve.user_notification_tokens")
    results = cursor.fetchall()
    for r in results:
        if r[0] == 'cafferatagian@hotmail.com':
            assert r[1] == "dummy1"
            continue
        assert False

def test_send_notification_no_token(monkeypatch, notifications_postgres_database):
    calls = []
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: create_mock_response(calls, {}))
    notifications_postgres_database.notify('giancafferata@hotmail.com', "Hola", "Mundo", {})
    assert len(calls) == 0

def test_send_notification_query_run_exception(monkeypatch, notifications_postgres_database):
    calls = []
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: create_mock_response(calls, {}))
    notifications_postgres_database.set_notification_token('giancafferata@hotmail.com', "dummy1")
    monkeypatch.setattr(PostgresExpoNotificationDatabase, "safe_query_run", AttributeError)
    notifications_postgres_database.notify('giancafferata@hotmail.com', "Hola", "Mundo", {})
    assert len(calls) == 0

def test_send_notification_post_exception(monkeypatch, notifications_postgres_database):
    monkeypatch.setattr(requests, "post", AttributeError)
    notifications_postgres_database.set_notification_token('giancafferata@hotmail.com', "dummy1")
    notifications_postgres_database.notify('giancafferata@hotmail.com', "Hola", "Mundo", {})

def test_send_notification_ok(monkeypatch, notifications_postgres_database):
    calls = []
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: create_mock_response(calls, {}))
    notifications_postgres_database.set_notification_token('giancafferata@hotmail.com', "dummy1")
    notifications_postgres_database.notify('giancafferata@hotmail.com', "Hola", "Mundo", {})
    assert len(calls) == 1
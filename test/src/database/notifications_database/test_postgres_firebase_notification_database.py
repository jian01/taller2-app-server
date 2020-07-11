from src.database.statistics.postgres_statistics_database import PostgresStatisticsDatabase
from src.database.statistics.statistics_database import ApiCall
from datetime import datetime
import pytest
import psycopg2
from typing import NamedTuple
import requests
import os
from io import BytesIO
import firebase_admin
from firebase_admin import messaging

class FakePostgres(NamedTuple):
    closed: int

@pytest.fixture(scope="function")
def statistics_postgres_database(monkeypatch, postgresql):
    os.environ["DUMB_ENV_NAME"] = "{}"
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(0))
    monkeypatch.setattr(firebase_admin, "get_app", lambda *args, **kwargs: True)
    monkeypatch.setattr(firebase_admin, "initialize_app", lambda *args, **kwargs: None)
    monkeypatch.setattr(messaging, "send", lambda *args, **kwargs: None)
    database = PostgresStatisticsDatabase(*(["DUMB_ENV_NAME"]*6))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)
    with open("test/src/database/notifications_database/config/initialize_db.sql", "r") as initialize_query:
        cursor = postgresql.cursor()
        cursor.execute(initialize_query.read())
        postgresql.commit()
        cursor.close()
    database.conn = postgresql
    database.notification_tokens_table_name = "chotuve.user_notification_tokens"
    return database

def test_postgres_connection_error(monkeypatch, statistics_postgres_database):
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(1))
    with pytest.raises(ConnectionError):
        database = PostgresStatisticsDatabase(*(["DUMB_ENV_NAME"] * 6))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)
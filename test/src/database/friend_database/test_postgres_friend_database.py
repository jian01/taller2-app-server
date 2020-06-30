from src.database.friends.postgres_friend_database import PostgresFriendDatabase
import pytest
import psycopg2
from typing import NamedTuple
import os

class FakePostgres(NamedTuple):
    closed: int

@pytest.fixture(scope="function")
def friend_postgres_database(monkeypatch, postgresql):
    os.environ["DUMB_ENV_NAME"] = "dummy"
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(0))
    database = PostgresFriendDatabase(*(["DUMB_ENV_NAME"]*6))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)
    with open("test/src/database/friend_database/config/initialize_db.sql", "r") as initialize_query:
        cursor = postgresql.cursor()
        cursor.execute(initialize_query.read())
        postgresql.commit()
        cursor.close()
    database.conn = postgresql
    database.friends_table_name = "chotuve.friends"
    database.friend_requests_table_name = "chotuve.friend_requests"
    return database

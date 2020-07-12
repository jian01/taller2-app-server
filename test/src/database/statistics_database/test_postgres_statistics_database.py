from src.database.statistics.postgres_statistics_database import PostgresStatisticsDatabase
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

@pytest.fixture(scope="function")
def statistics_postgres_database(monkeypatch, postgresql):
    os.environ["DUMB_ENV_NAME"] = "dummy"
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(0))
    monkeypatch.setattr(PostgresUtils, "get_postgres_connection",
                        lambda *args, **kwargs: psycopg2.connect(*args, **kwargs))
    database = PostgresStatisticsDatabase(*(["DUMB_ENV_NAME"]*6))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)
    with open("test/src/database/statistics_database/config/initialize_db.sql", "r") as initialize_query:
        cursor = postgresql.cursor()
        cursor.execute(initialize_query.read())
        postgresql.commit()
        cursor.close()
    database.conn = postgresql
    database.app_server_api_calls_table = "chotuve.app_server_api_calls"
    database.server_alias = "test"
    yield database
    postgresql.close()

def test_postgres_connection_error(monkeypatch, statistics_postgres_database):
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(1))
    with pytest.raises(ConnectionError):
        database = PostgresStatisticsDatabase(*(["DUMB_ENV_NAME"] * 6))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)

def test_one_api_call_save_and_load(monkeypatch, statistics_postgres_database):
    test_api_call = ApiCall(path="/health",status=200,timestamp=datetime.now(), time=1.0,
                            method="GET")
    statistics_postgres_database.register_api_call(test_api_call)
    api_call_generator = statistics_postgres_database.last_30_days_api_calls()
    for api_calls in api_call_generator:
        assert len(api_calls) == 1
        for api_call in api_calls:
            assert api_call._asdict() == test_api_call._asdict()

def test_multiple_api_calls_save_and_load(monkeypatch, statistics_postgres_database):
    for i in range(1000):
        test_api_call = ApiCall(path="/health",status=200,timestamp=datetime.now(), time=i*1.0,
                                method="GET")
        statistics_postgres_database.register_api_call(test_api_call)
    api_call_generator = statistics_postgres_database.last_30_days_api_calls()
    api_call_count = 0
    times = set()
    for api_calls in api_call_generator:
        for api_call in api_calls:
            api_call_count += 1
            times.update([api_call.time])
    assert api_call_count == 1000
    assert len(times) == 1000
    for i in range(1000):
        assert i*1.0 in times
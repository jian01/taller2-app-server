from src.database.friends.postgres_friend_database import PostgresFriendDatabase
from src.database.friends.exceptions.unexistent_friend_requests import UnexistentFriendRequest
from src.database.friends.exceptions.users_already_friends_error import UsersAlreadyFriendsError
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

def test_postgres_connection_error(monkeypatch, friend_postgres_database):
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(1))
    with pytest.raises(ConnectionError):
        database = PostgresFriendDatabase(*(["DUMB_ENV_NAME"] * 6))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)

def test_create_friend_request_ok(monkeypatch, friend_postgres_database):
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    assert len(friend_postgres_database.get_friend_requests('cafferatagian@hotmail.com')) == 1
    assert friend_postgres_database.get_friend_requests('cafferatagian@hotmail.com') == ['giancafferata@hotmail.com']
    assert len(friend_postgres_database.get_friend_requests('giancafferata@hotmail.com')) == 0
    assert friend_postgres_database.exists_friend_request('giancafferata@hotmail.com',
                                                          'cafferatagian@hotmail.com')

def test_accept_unexistent_friend_request(monkeypatch, friend_postgres_database):
    with pytest.raises(UnexistentFriendRequest):
        friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                       'cafferatagian@hotmail.com')

def test_accept_friend_request_ok(monkeypatch, friend_postgres_database):
    assert not friend_postgres_database.are_friends('giancafferata@hotmail.com',
                                                    'cafferatagian@hotmail.com')
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    assert len(friend_postgres_database.get_friend_requests('cafferatagian@hotmail.com')) == 0
    assert len(friend_postgres_database.get_friends('cafferatagian@hotmail.com')) == 1
    assert len(friend_postgres_database.get_friends('giancafferata@hotmail.com')) == 1
    assert friend_postgres_database.are_friends('giancafferata@hotmail.com',
                                                'cafferatagian@hotmail.com')

def test_reject_unexistent_friend_request(monkeypatch, friend_postgres_database):
    with pytest.raises(UnexistentFriendRequest):
        friend_postgres_database.reject_friend_request('giancafferata@hotmail.com',
                                                       'cafferatagian@hotmail.com')

def test_reject_friend_request_ok(monkeypatch, friend_postgres_database):
    assert not friend_postgres_database.are_friends('giancafferata@hotmail.com',
                                                    'cafferatagian@hotmail.com')
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    assert friend_postgres_database.exists_friend_request('giancafferata@hotmail.com',
                                                          'cafferatagian@hotmail.com')
    assert not friend_postgres_database.exists_friend_request('cafferatagian@hotmail.com',
                                                              'giancafferata@hotmail.com')
    friend_postgres_database.reject_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    assert not friend_postgres_database.exists_friend_request('giancafferata@hotmail.com',
                                                              'cafferatagian@hotmail.com')
    assert not friend_postgres_database.exists_friend_request('cafferatagian@hotmail.com',
                                                              'giancafferata@hotmail.com')
    assert len(friend_postgres_database.get_friend_requests('cafferatagian@hotmail.com')) == 0
    assert len(friend_postgres_database.get_friends('cafferatagian@hotmail.com')) == 0
    assert len(friend_postgres_database.get_friends('giancafferata@hotmail.com')) == 0
    assert not friend_postgres_database.are_friends('giancafferata@hotmail.com',
                                                    'cafferatagian@hotmail.com')

def test_users_already_friends_when_request(monkeypatch, friend_postgres_database):
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    with pytest.raises(UsersAlreadyFriendsError):
        friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                       'cafferatagian@hotmail.com')
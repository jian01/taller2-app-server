from src.database.friends.postgres_friend_database import PostgresFriendDatabase
from src.database.friends.exceptions.unexistent_friend_requests import UnexistentFriendRequest
from src.database.friends.exceptions.users_already_friends_error import UsersAlreadyFriendsError
from src.database.friends.exceptions.users_are_not_friends_error import UsersAreNotFriendsError
import pytest
import psycopg2
from typing import NamedTuple
import os
from src.database.utils.postgres_connection import PostgresUtils

class FakePostgres(NamedTuple):
    closed: int

@pytest.fixture(scope="function")
def friend_postgres_database(monkeypatch, postgresql):
    os.environ["DUMB_ENV_NAME"] = "dummy"
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(0))
    monkeypatch.setattr(PostgresUtils, "get_postgres_connection", lambda *args, **kwargs: psycopg2.connect(*args, **kwargs))
    database = PostgresFriendDatabase(*(["DUMB_ENV_NAME"]*9))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)
    with open("test/src/database/friend_database/config/initialize_db.sql", "r") as initialize_query:
        cursor = postgresql.cursor()
        cursor.execute(initialize_query.read())
        postgresql.commit()
        cursor.close()
    database.conn = postgresql
    database.friends_table_name = "chotuve.friends"
    database.friend_requests_table_name = "chotuve.friend_requests"
    database.user_messages_table_name = "chotuve.user_messages"
    database.users_table_name = "chotuve.users"
    database.user_deleted_messages_table_name = "chotuve.deleted_messages"
    yield database
    postgresql.close()

def test_postgres_connection_error(monkeypatch, friend_postgres_database):
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(1))
    with pytest.raises(ConnectionError):
        database = PostgresFriendDatabase(*(["DUMB_ENV_NAME"] * 9))
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

def test_delete_friendship(monkeypatch, friend_postgres_database):
    assert not friend_postgres_database.are_friends('giancafferata@hotmail.com',
                                                    'cafferatagian@hotmail.com')
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.delete_friendship('giancafferata@hotmail.com',
                                               'cafferatagian@hotmail.com')
    assert len(friend_postgres_database.get_friend_requests('cafferatagian@hotmail.com')) == 0
    assert len(friend_postgres_database.get_friends('cafferatagian@hotmail.com')) == 0
    assert len(friend_postgres_database.get_friends('giancafferata@hotmail.com')) == 0
    assert not friend_postgres_database.are_friends('giancafferata@hotmail.com',
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

def test_send_message_not_friends(monkeypatch, friend_postgres_database):
    with pytest.raises(UsersAreNotFriendsError):
        friend_postgres_database.send_message('giancafferata@hotmail.com','cafferatagian@hotmail.com',
                                              "Hola")

def test_send_one_message_and_get_conversation(monkeypatch, friend_postgres_database):
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.send_message('giancafferata@hotmail.com','cafferatagian@hotmail.com',
                                          "Hola")
    conv, pages = friend_postgres_database.get_conversation('giancafferata@hotmail.com','cafferatagian@hotmail.com', 2, 0)
    assert pages == 1
    assert len(conv) == 1
    assert conv[0].message == "Hola"

def test_send_messages_and_get_conversation(monkeypatch, friend_postgres_database):
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.send_message('giancafferata@hotmail.com','cafferatagian@hotmail.com',
                                          "Hola")
    friend_postgres_database.send_message('giancafferata@hotmail.com', 'cafferatagian@hotmail.com',
                                          "todo bien?")
    friend_postgres_database.send_message('cafferatagian@hotmail.com','giancafferata@hotmail.com',
                                          "see")
    conv, pages = friend_postgres_database.get_conversation('giancafferata@hotmail.com','cafferatagian@hotmail.com', 2, 0)
    assert pages == 2
    assert len(conv) == 2
    assert conv[0].message == "see"
    assert conv[1].message == "todo bien?"
    conv, pages = friend_postgres_database.get_conversation('giancafferata@hotmail.com','cafferatagian@hotmail.com', 2, 1)
    assert pages == 2
    assert len(conv) == 1
    assert conv[0].message == "Hola"

def test_send_messages_and_get_last_conversations(monkeypatch, friend_postgres_database):
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'asd@asd.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'asd@asd.com')
    friend_postgres_database.send_message('giancafferata@hotmail.com','cafferatagian@hotmail.com',
                                          "Hola")
    friend_postgres_database.send_message('giancafferata@hotmail.com', 'cafferatagian@hotmail.com',
                                          "todo bien?")
    friend_postgres_database.send_message('cafferatagian@hotmail.com','giancafferata@hotmail.com',
                                          "see")
    friend_postgres_database.send_message('giancafferata@hotmail.com','asd@asd.com',
                                          "Hola")
    user_data, message_data = friend_postgres_database.get_conversations('giancafferata@hotmail.com')
    assert len(user_data) == 2
    assert len(message_data) == 2
    assert user_data[0]["email"] == 'asd@asd.com'
    assert user_data[1]["email"] == 'cafferatagian@hotmail.com'
    assert message_data[0].message == 'Hola'
    assert message_data[1].message == 'see'
    user_data, message_data = friend_postgres_database.get_conversations('asd@asd.com')
    assert len(user_data) == 1
    assert len(message_data) == 1

def test_send_messages_delete_friend_and_see_no_conversation(monkeypatch, friend_postgres_database):
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'asd@asd.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'asd@asd.com')
    friend_postgres_database.send_message('giancafferata@hotmail.com','cafferatagian@hotmail.com',
                                          "Hola")
    friend_postgres_database.send_message('giancafferata@hotmail.com', 'cafferatagian@hotmail.com',
                                          "todo bien?")
    friend_postgres_database.send_message('cafferatagian@hotmail.com','giancafferata@hotmail.com',
                                          "see")
    friend_postgres_database.send_message('giancafferata@hotmail.com','asd@asd.com',
                                          "Hola")
    friend_postgres_database.delete_friendship('giancafferata@hotmail.com',
                                               'asd@asd.com')
    user_data, message_data = friend_postgres_database.get_conversations('giancafferata@hotmail.com')
    assert len(user_data) == 1
    assert len(message_data) == 1
    assert user_data[0]["email"] == 'cafferatagian@hotmail.com'
    assert message_data[0].message == 'see'
    user_data, message_data = friend_postgres_database.get_conversations('asd@asd.com')
    assert len(user_data) == 0
    assert len(message_data) == 0

def test_delete_conversation(monkeypatch, friend_postgres_database):
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'cafferatagian@hotmail.com')
    friend_postgres_database.create_friend_request('giancafferata@hotmail.com',
                                                   'asd@asd.com')
    friend_postgres_database.accept_friend_request('giancafferata@hotmail.com',
                                                   'asd@asd.com')
    friend_postgres_database.send_message('giancafferata@hotmail.com','cafferatagian@hotmail.com',
                                          "Hola")
    friend_postgres_database.send_message('giancafferata@hotmail.com', 'cafferatagian@hotmail.com',
                                          "todo bien?")
    friend_postgres_database.delete_conversation('giancafferata@hotmail.com', 'cafferatagian@hotmail.com')
    friend_postgres_database.send_message('cafferatagian@hotmail.com','giancafferata@hotmail.com',
                                          "see")
    friend_postgres_database.send_message('giancafferata@hotmail.com','cafferatagian@hotmail.com',
                                          "te felicito master")
    conv, pages = friend_postgres_database.get_conversation('giancafferata@hotmail.com','cafferatagian@hotmail.com', 2, 0)
    assert pages == 1
    assert len(conv) == 2
    assert conv[0].message == "te felicito master"
    assert conv[1].message == "see"

    conv, pages = friend_postgres_database.get_conversation('cafferatagian@hotmail.com','giancafferata@hotmail.com', 4, 0)
    assert pages == 1
    assert len(conv) == 4
    assert conv[0].message == "te felicito master"
    assert conv[1].message == "see"
    assert conv[2].message == "todo bien?"
    assert conv[3].message == "Hola"
    friend_postgres_database.delete_conversation('cafferatagian@hotmail.com', 'giancafferata@hotmail.com')
    conv, pages = friend_postgres_database.get_conversation('cafferatagian@hotmail.com','giancafferata@hotmail.com', 4, 0)
    assert pages == 0
    assert len(conv) == 0
    user_data, message_data = friend_postgres_database.get_conversations('cafferatagian@hotmail.com')
    assert len(user_data) == 0
    assert len(message_data) == 0
    user_data, message_data = friend_postgres_database.get_conversations('giancafferata@hotmail.com')
    assert len(user_data) == 1
    assert len(message_data) == 1
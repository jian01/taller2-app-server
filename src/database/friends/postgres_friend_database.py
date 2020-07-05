import psycopg2
from typing import NoReturn, List, Optional, NamedTuple, Tuple, Dict
from src.database.videos.video_database import VideoData, VideoDatabase
import logging
import os
import json
import requests
import math
import datetime
from typing import NoReturn, List, Dict, Set, Tuple
from abc import abstractmethod
from src.database.friends.exceptions.users_already_friends_error import UsersAlreadyFriendsError
from src.database.friends.exceptions.unexistent_friend_requests import UnexistentFriendRequest
from src.database.friends.friend_database import FriendDatabase

NEW_FRIEND_REQUEST_QUERY = """
INSERT INTO {} ("from", "to", status, timestamp)
VALUES (%s, %s, 'pending', %s)
"""

CHECK_FRIENDS_QUERY = """
SELECT *
FROM {}
WHERE user1 = '%s' AND user2 = '%s'
"""

CHECK_FRIEND_REQUEST_QUERY = """
SELECT *
FROM {}
WHERE "from" = %s AND "to" = %s
"""

ALL_FRIENDS_QUERY = """
SELECT user1, user2
FROM {}
WHERE user1 = '%s' OR user2 = '%s'
"""

FRIEND_REQUEST_QUERY = """
SELECT "from"
FROM {}
WHERE "to" = '%s'
"""

DELETE_FRIEND_REQUEST_QUERY = """
DELETE FROM {}
WHERE "from"=%s AND "to"=%s;
"""

NEW_FRIENDS_QUERY = """
INSERT INTO {} (user1, user2)
VALUES (%s, %s)
"""

class PostgresFriendDatabase(FriendDatabase):
    """
    Postgres implementation of Friend database
    """
    logger = logging.getLogger(__name__)
    def __init__(self, friends_table_name: str, friend_requests_table_name: str, postgr_host_env_name: str,
                 postgr_user_env_name: str, postgr_pass_env_name: str, postgr_database_env_name: str):

        self.friends_table_name = friends_table_name
        self.friend_requests_table_name = friend_requests_table_name
        self.conn = psycopg2.connect(host=os.environ[postgr_host_env_name], user=os.environ[postgr_user_env_name],
                                     password=os.environ[postgr_pass_env_name],
                                     database=os.environ[postgr_database_env_name])
        if self.conn.closed == 0:
            self.logger.info("Connected to postgres database")
        else:
            self.logger.error("Unable to connect to postgres database")
            raise ConnectionError("Unable to connect to postgres database")

    @staticmethod
    def safe_query_run(connection, cursor, query: str, params: Optional[Tuple] = None):
        try:
            cursor.execute(query, params)
        except Exception as err:
            connection.rollback()
            raise err

    def create_friend_request(self, from_user_email: str,
                              to_user_email: str) -> NoReturn:
        """
        Creates a friend request between

        :raises:
            UsersAlreadyFriendsError: raised when the users are already friends
            UnexistentTargetUserError: the target user does not exist
            UnexistentRequestorUserError: the user that requested the friendship does not exist

        :param from_user_email: the user that requests the friendship
        :param to_user_email: the target user of the request
        """
        if self.are_friends(from_user_email, to_user_email):
            raise UsersAlreadyFriendsError
        self.logger.debug("Sending friend request for user with email %s" % from_user_email)
        cursor = self.conn.cursor()
        self.safe_query_run(self.conn, cursor,
                            NEW_FRIEND_REQUEST_QUERY.format(self.friend_requests_table_name),
                           (from_user_email, to_user_email, datetime.datetime.now().isoformat()))
        self.conn.commit()
        cursor.close()

    def accept_friend_request(self, from_user_email: str,
                              to_user_email: str) -> NoReturn:
        """
        Accepts an existing friend request

        :raises:
            UnexistentFriendRequest: the friend request does not exist or is not pending

        :param from_user_email: the user that requested the friendship
        :param to_user_email: the target user of the request
        """
        if from_user_email not in self.get_friend_requests(to_user_email):
            raise UnexistentFriendRequest
        cursor = self.conn.cursor()
        self.safe_query_run(self.conn, cursor,
                            DELETE_FRIEND_REQUEST_QUERY.format(self.friend_requests_table_name),
                            (from_user_email, to_user_email))
        self.conn.commit()

        friend_tuple = list(sorted([from_user_email,to_user_email]))
        friend_tuple = (friend_tuple[0], friend_tuple[1])
        cursor.execute(NEW_FRIENDS_QUERY.format(self.friends_table_name),
                       friend_tuple)
        self.conn.commit()

        cursor.close()

    def reject_friend_request(self, from_user_email: str,
                              to_user_email: str) -> NoReturn:
        """
        Rejects an existing friend request

        :raises:
            UnexistentFriendRequest: the friend request does not exist or is not pending

        :param from_user_email: the user that requested the friendship
        :param to_user_email: the target user of the request
        """
        if from_user_email not in self.get_friend_requests(to_user_email):
            raise UnexistentFriendRequest
        cursor = self.conn.cursor()
        self.safe_query_run(self.conn, cursor,
                            DELETE_FRIEND_REQUEST_QUERY.format(self.friend_requests_table_name),
                            (from_user_email, to_user_email))
        self.conn.commit()
        cursor.close()

    def get_friend_requests(self, user_email: str) -> List[str]:
        """
        Gets all the user emails that have sent a user request to the user

        :param user_email: the user to query for its friend requests
        :return: a list of emails
        """
        self.logger.debug("Getting friend requests for %s" % user_email)
        cursor = self.conn.cursor()
        self.safe_query_run(self.conn, cursor,
                            FRIEND_REQUEST_QUERY.format(self.friend_requests_table_name) % user_email)
        result = cursor.fetchall()
        return [r[0] for r in result]

    def get_friends(self, user_email: str) -> List[str]:
        """
        Gets all the user emails that are friends of the user

        :param user_email: the user to query for its friend
        :return: a list of emails
        """
        self.logger.debug("Getting friends for %s" % user_email)
        cursor = self.conn.cursor()
        self.safe_query_run(self.conn, cursor,
                            ALL_FRIENDS_QUERY.format(self.friends_table_name) % (user_email, user_email))
        result = cursor.fetchall()
        friend_emails = [t[0] for t in result]+[t[1] for t in result]
        return [f for f in friend_emails if f!=user_email]

    def are_friends(self, user_email1: str, user_email2: str) -> bool:
        """
        Check if user1 is friend with user2

        :param user_email1: the first user email
        :param user_email2: the second user email
        :return: a boolean indicating whether user1 is friend user2's friend
        """
        self.logger.debug("Checking whether %s and %s are friends" % (user_email1, user_email2))
        cursor = self.conn.cursor()
        friends_ordered = tuple(list(sorted([user_email1,user_email2])))
        self.safe_query_run(self.conn, cursor,
                            CHECK_FRIENDS_QUERY.format(self.friends_table_name) % friends_ordered)
        result = cursor.fetchone()
        if not result:
            return False
        return True

    def exists_friend_request(self, from_user_email: str, to_user_email: str) -> bool:
        """
        Check if exists friend request from 'requestor' to 'receiver'

        :param from_user_email: the requestor of the friendship
        :param to_user_email: the receiver of the request
        :return: a boolean indicating whether the friend request exists
        """
        self.logger.debug("Checking whether %s sent a friend request to %s" % (from_user_email, to_user_email))
        cursor = self.conn.cursor()
        self.safe_query_run(self.conn, cursor,
                            CHECK_FRIEND_REQUEST_QUERY.format(self.friend_requests_table_name),
                            (from_user_email, to_user_email))
        result = cursor.fetchone()
        if not result:
            return False
        return True
import psycopg2
from typing import NoReturn, List, Optional, NamedTuple, Tuple, Dict
import logging
import os
import json
import requests
import math
from typing import NoReturn, List, Dict, Set, Tuple
from abc import abstractmethod
from src.database.friends.exceptions.users_already_friends_error import UsersAlreadyFriendsError
from src.database.friends.exceptions.unexistent_friend_requests import UnexistentFriendRequest
from src.database.friends.exceptions.users_are_not_friends_error import UsersAreNotFriendsError
from src.database.friends.exceptions.no_more_messages_error import NoMoreMessagesError
from src.database.friends.friend_database import FriendDatabase, PrivateMessage
from datetime import datetime
from src.database.utils.postgres_connection import PostgresUtils

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

DELETE_FRIEND_QUERY = """
DELETE FROM {}
WHERE user1 = %s AND user2 = %s;
"""

SEND_MESSAGE_QUERY = """
INSERT INTO {} (from_user, to_user, message, datetime)
VALUES (%s, %s, %s, %s)
"""

GET_PAGINATED_CONVERSATION_QUERY = """
SELECT from_user, to_user, message, datetime
FROM {user_messages_table_name}
WHERE ((from_user=%s AND to_user=%s) OR (to_user=%s AND from_user=%s))
AND id NOT IN (
SELECT id FROM {user_deleted_messages_table_name} WHERE deletor = %s
)
ORDER BY datetime DESC
LIMIT %s OFFSET %s;
"""

COUNT_ROWS_CONVERSATION_QUERY = """
SELECT COUNT(*) FROM {user_messages_table_name}
WHERE ((from_user=%s AND to_user=%s) OR (to_user=%s AND from_user=%s))
AND id NOT IN (
SELECT id FROM {user_deleted_messages_table_name} WHERE deletor = %s
)
"""

GET_CONVERSATIONS_QUERY = """
SELECT u.email, u.fullname, u.phone_number, u.photo,
messages.from_user, messages.to_user, messages.message, messages.datetime
FROM
(SELECT from_user, to_user, message, datetime,
  CASE
    WHEN from_user=%s THEN to_user
    ELSE from_user
  END 
  AS other_user
FROM {user_messages_table_name}
WHERE from_user=%s OR to_user=%s
ORDER BY datetime DESC) as messages
INNER JOIN (
SELECT max(datetime) as datetime,
  CASE
    WHEN from_user=%s THEN to_user
    ELSE from_user
  END 
  AS other_user
FROM {user_messages_table_name}
WHERE (from_user=%s OR to_user=%s)
AND id NOT IN (
SELECT id FROM {user_deleted_messages_table_name} WHERE deletor = %s
)
GROUP BY 2
) as last_messages
ON messages.other_user=last_messages.other_user AND messages.datetime=last_messages.datetime
INNER JOIN {users_table_name} as u
ON u.email=messages.other_user
WHERE EXISTS (
    SELECT user1, user2
    FROM {friends_table_name}
    WHERE (user1 = %s AND user2 = messages.other_user) OR (user1 = messages.other_user AND user2 = %s)
)
"""

DELETE_CONVERSATION_QUERY = """
INSERT INTO {user_deleted_messages_table_name}(id, deletor)
SELECT ids_values.id, %s
FROM (SELECT id FROM {user_messages_table_name}
WHERE ((from_user=%s AND to_user=%s) OR (to_user=%s AND from_user=%s))
AND id NOT IN (
SELECT id FROM {user_deleted_messages_table_name} WHERE deletor = %s
)) ids_values
"""


class PostgresFriendDatabase(FriendDatabase):
    """
    Postgres implementation of Friend database
    """
    logger = logging.getLogger(__module__)

    def __init__(self, friends_table_name: str, friend_requests_table_name: str,
                 user_messages_table_name: str, users_table_name: str,
                 user_deleted_messages_table_name: str,
                 postgr_host_env_name: str, postgr_user_env_name: str,
                 postgr_pass_env_name: str, postgr_database_env_name: str):

        self.friends_table_name = friends_table_name
        self.friend_requests_table_name = friend_requests_table_name
        self.user_messages_table_name = user_messages_table_name
        self.users_table_name = users_table_name
        self.user_deleted_messages_table_name = user_deleted_messages_table_name
        self.conn = PostgresUtils.get_postgres_connection(host=os.environ[postgr_host_env_name],
                                                          user=os.environ[postgr_user_env_name],
                                                          password=os.environ[postgr_pass_env_name],
                                                          database=os.environ[postgr_database_env_name])
        if self.conn.closed == 0:
            self.logger.info("Connected to postgres database")
        else:
            self.logger.error("Unable to connect to postgres database")
            raise ConnectionError("Unable to connect to postgres database")

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
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     NEW_FRIEND_REQUEST_QUERY.format(self.friend_requests_table_name),
                                     (from_user_email, to_user_email, datetime.now().isoformat()))
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
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     DELETE_FRIEND_REQUEST_QUERY.format(self.friend_requests_table_name),
                                     (from_user_email, to_user_email))
        self.conn.commit()

        friend_tuple = list(sorted([from_user_email, to_user_email]))
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
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
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
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     FRIEND_REQUEST_QUERY.format(self.friend_requests_table_name) % user_email)
        result = cursor.fetchall()
        cursor.close()
        return [r[0] for r in result]

    def get_friends(self, user_email: str) -> List[str]:
        """
        Gets all the user emails that are friends of the user

        :param user_email: the user to query for its friend
        :return: a list of emails
        """
        self.logger.debug("Getting friends for %s" % user_email)
        cursor = self.conn.cursor()
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     ALL_FRIENDS_QUERY.format(self.friends_table_name) % (user_email, user_email))
        result = cursor.fetchall()
        cursor.close()
        friend_emails = [t[0] for t in result] + [t[1] for t in result]
        return [f for f in friend_emails if f != user_email]

    def delete_friendship(self, user_email1: str, user_email2: str) -> NoReturn:
        """
        Delete friendship if exists

        :param user_email1: first user email
        :param user_email2: second user email
        """
        friend_tuple = list(sorted([user_email1, user_email2]))
        friend_tuple = (friend_tuple[0], friend_tuple[1])
        self.logger.debug("Deleting friendship between %s and %s" % (user_email1, user_email2))
        cursor = self.conn.cursor()
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     DELETE_FRIEND_QUERY.format(self.friends_table_name),
                                     friend_tuple)
        cursor.close()
        self.conn.commit()

    def are_friends(self, user_email1: str, user_email2: str) -> bool:
        """
        Check if user1 is friend with user2

        :param user_email1: the first user email
        :param user_email2: the second user email
        :return: a boolean indicating whether user1 is friend user2's friend
        """
        self.logger.debug("Checking whether %s and %s are friends" % (user_email1, user_email2))
        cursor = self.conn.cursor()
        friends_ordered = tuple(list(sorted([user_email1, user_email2])))
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     CHECK_FRIENDS_QUERY.format(self.friends_table_name) % friends_ordered)
        result = cursor.fetchone()
        cursor.close()
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
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     CHECK_FRIEND_REQUEST_QUERY.format(self.friend_requests_table_name),
                                     (from_user_email, to_user_email))
        result = cursor.fetchone()
        cursor.close()
        if not result:
            return False
        return True

    def send_message(self, from_user_email: str, to_user_email: str,
                     message: str) -> NoReturn:
        """
        Sends a private message to a user

        :raises:
            UsersAreNotFriendsError: the users are not friends

        :param from_user_email: the email of the sender
        :param to_user_email: the email of the receiver
        :param message: the message to send
        """
        if not self.are_friends(from_user_email, to_user_email):
            raise UsersAreNotFriendsError
        self.logger.debug("Sending user message")
        cursor = self.conn.cursor()
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     SEND_MESSAGE_QUERY.format(self.user_messages_table_name),
                                     (from_user_email, to_user_email, message, datetime.now().isoformat()))
        self.conn.commit()
        cursor.close()

    def get_conversation(self, requestor_email: str, other_user_email: str,
                         per_page: int, page: int) -> Tuple[List[PrivateMessage], int]:
        """
        Get the paginated conversation between user1 and user2

        :raises:
            NoMoreMessagesError: the page has no messages

        :param requestor_email: the email of user1
        :param other_user_email: the email of user2
        :param per_page: the messages per page
        :param page: the page for the message, starting from 0
        :return: the list of private messages and the number of pages
        """
        self.logger.debug("Geting conversation between %s and %s" % (requestor_email, other_user_email))

        cursor = self.conn.cursor()

        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     COUNT_ROWS_CONVERSATION_QUERY.format(
                                         user_messages_table_name=self.user_messages_table_name,
                                         user_deleted_messages_table_name=self.user_deleted_messages_table_name),
                                     (requestor_email, other_user_email, requestor_email, other_user_email,
                                      requestor_email))
        result = cursor.fetchone()

        pages = int(math.ceil(result[0] / per_page))
        if not page < pages and page != 0:
            raise NoMoreMessagesError()

        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     GET_PAGINATED_CONVERSATION_QUERY.format(
                                         user_messages_table_name=self.user_messages_table_name,
                                         user_deleted_messages_table_name=self.user_deleted_messages_table_name),
                                     (requestor_email, other_user_email, requestor_email, other_user_email,
                                      requestor_email,
                                      per_page, page * per_page))
        result = cursor.fetchall()
        self.conn.commit()
        cursor.close()
        # from_user, to_user, message, datetime
        result = [PrivateMessage(from_user=r[0], to_user=r[1], message=r[2], timestamp=r[3]) for r in result]
        return result, pages

    def get_conversations(self, user_email: str) -> Tuple[List[Dict], List[PrivateMessage]]:
        """
        Get all the conversations ordered by recent activity

        :param user_email: the email of the user for getting the conversations
        :return: a tuple (list of user data, list of last private message)
        """
        self.logger.debug("Geting last conversations with %s" % user_email)

        cursor = self.conn.cursor()
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     GET_CONVERSATIONS_QUERY.format(
                                         friends_table_name=self.friends_table_name,
                                         user_messages_table_name=self.user_messages_table_name,
                                         users_table_name=self.users_table_name,
                                         user_deleted_messages_table_name=self.user_deleted_messages_table_name),
                                     (user_email,) * 9)
        '''
        u.email, u.fullname, u.phone_number, u.photo
        messages.from_user, messages.to_user, messages.message, messages.datetime
        '''
        result = cursor.fetchall()
        user_data = [{"email": r[0], "fullname": r[1],
                      "phone_number": r[2], "photo": r[3]} for r in result]
        videos_data = [PrivateMessage(from_user=r[4], to_user=r[5], message=r[6], timestamp=r[7]) for r in result]
        self.conn.commit()
        cursor.close()
        return user_data, videos_data

    def delete_conversation(self, deletor_email: str, deleted_email: str) -> NoReturn:
        """
        Deletes the conversation between two users but just for the deletor

        :param deletor_email: the email of the one that deletes the conversation
        :param deleted_email: the email of the other user of the conversation
        """
        self.logger.debug("%s deleting conversation with %s" % (deletor_email, deleted_email))
        cursor = self.conn.cursor()
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     DELETE_CONVERSATION_QUERY.format(
                                         user_messages_table_name=self.user_messages_table_name,
                                         user_deleted_messages_table_name=self.user_deleted_messages_table_name),
                                     (deletor_email, deletor_email, deleted_email, deletor_email, deleted_email,
                                      deletor_email))
        self.conn.commit()
        cursor.close()

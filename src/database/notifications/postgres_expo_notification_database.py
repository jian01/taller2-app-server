from typing import NoReturn, Tuple, Dict, Optional
from abc import abstractmethod
import json
import psycopg2
import os
import logging
import requests

NOTIFICATION_TOKEN_SAVE = """
DELETE FROM {notification_tokens_table_name}
WHERE token=%s;

INSERT INTO {notification_tokens_table_name} (user_email, token)
VALUES (%s, %s)
ON CONFLICT (user_email) DO UPDATE 
  SET token = excluded.token;
"""

SEARCH_NOTIFICATION_TOKEN = """
SELECT token
FROM {notification_tokens_table_name}
WHERE user_email = %s
"""

EXPO_SEND_NOTIFICATION_ENDPOINT = "https://exp.host/--/api/v2/push/send"

NOTIFICATION_SEND_TIMEOUT = 5

class PostgresExpoNotificationDatabase:
    """
    Notifications database
    """
    logger = logging.getLogger(__name__)

    def __init__(self, notification_tokens_table_name: str,
                 postgr_host_env_name: str, postgr_user_env_name: str,
                 postgr_pass_env_name: str, postgr_database_env_name: str):
        self.notification_tokens_table_name = notification_tokens_table_name
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

    def set_notification_token(self, user_email: str, token: str) -> NoReturn:
        """
        Sets the notification token for a user email

        :param user_email: the user email for setting the notification token
        :param token: the token to set
        """
        self.logger.debug("Setting notification token for %s" % user_email)
        cursor = self.conn.cursor()
        try:
            self.safe_query_run(self.conn, cursor,
                                NOTIFICATION_TOKEN_SAVE.format(notification_tokens_table_name=self.notification_tokens_table_name),
                                (token, user_email, token))
        except Exception:
            self.logger.exception("Couldn't register notification token")
            pass
        self.conn.commit()
        cursor.close()

    def notify(self, user_email: str, title: str, body: str, payload: Dict) -> NoReturn:
        """
        Sends the payload a notification the the user if has registered an app token for that user

        :param user_email: the user email for sending the payload
        :param title: the title of the notification
        :param body: the body of the notification
        :param payload: the payload to send
        """
        self.logger.debug("Sending notification to %s" % user_email)
        cursor = self.conn.cursor()
        try:
            self.safe_query_run(self.conn, cursor,
                                SEARCH_NOTIFICATION_TOKEN.format(notification_tokens_table_name=self.notification_tokens_table_name),
                                (user_email,))
            result = cursor.fetchone()
        except Exception:
            self.logger.exception("Couldn't send notification")
            cursor.close()
            return
        if result:
            token = result[0][0]
            cursor.close()
        else:
            cursor.close()
            return
        try:
            requests.post(EXPO_SEND_NOTIFICATION_ENDPOINT, json={"to": token,
                                                                 "title": title,
                                                                 "body": body,
                                                                 "data": payload},
                          timeout=NOTIFICATION_SEND_TIMEOUT)
        except Exception:
            self.logger.exception("Couldn't send notification")
            return



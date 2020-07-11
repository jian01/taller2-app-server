from typing import NoReturn, Tuple, Dict, Optional
from abc import abstractmethod
import json
import psycopg2
import os
import logging
import firebase_admin
from firebase_admin import credentials, messaging

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

class PostgresFirebaseNotificationDatabase:
    """
    Notifications database
    """
    logger = logging.getLogger(__name__)

    def __init__(self, notification_tokens_table_name: str,
                 firebase_credentials_json_env_name: str,
                 postgr_host_env_name: str, postgr_user_env_name: str,
                 postgr_pass_env_name: str, postgr_database_env_name: str):

        creds = credentials.Certificate(json.loads(os.environ[firebase_credentials_json_env_name]))
        firebase_admin.initialize_app(creds)
        if firebase_admin.get_app():
            self.logger.info("Connected to firebase")
        else:
            self.logger.error("Unable to connect to firebase")
            raise ConnectionError("Unable to connect to firebase")
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
        self.safe_query_run(self.conn, cursor,
                            NOTIFICATION_TOKEN_SAVE.format(notification_tokens_table_name=self.notification_tokens_table_name),
                            (user_email, token))
        self.conn.commit()
        cursor.close()

    def notify(self, user_email: str, payload: Dict) -> NoReturn:
        """
        Sends the payload a notification the the user if has registered an app token for that user

        :param user_email: the user email for sending the payload
        :param payload: the payload to send
        """
        self.logger.debug("Sending notification to %s" % user_email)
        cursor = self.conn.cursor()
        self.safe_query_run(self.conn, cursor,
                            SEARCH_NOTIFICATION_TOKEN.format(notification_tokens_table_name=self.notification_tokens_table_name),
                            (user_email,))
        result = cursor.fetchone()
        if result:
            token = result[0][0]
            cursor.close()
        else:
            cursor.close()
            return

        message = messaging.Message(
            data=payload,
            token=token,
        )
        try:
            response = messaging.send(message)
            self.logger.debug("Notification sent, id: %s" % response)
        except Exception as err:
            self.logger.exception("Notification couldn't be sent")
            return
from typing import NamedTuple, NoReturn, List, Tuple, Dict, Generator
from abc import abstractmethod
from datetime import datetime, date

class NotificationDatabase:
    """
    Notifications database
    """

    @abstractmethod
    def set_notification_token(self, user_email: str, token: str) -> NoReturn:
        """
        Sets the notification token for a user email

        :param user_email: the user email for setting the notification token
        :param token: the token to set
        """

    @abstractmethod
    def notify(self, user_email: str, title: str, body: str, payload: Dict) -> NoReturn:
        """
        Sends the payload a notification the the user if has registered an app token for that user

        :param user_email: the user email for sending the payload
        :param title: the title of the notification
        :param body: the body of the notification
        :param payload: the payload to send
        """

    @classmethod
    def factory(cls, name: str, *args, **kwargs) -> 'NotificationDatabase':
        """
        Factory pattern for database

        :param name: the name of the database to create in the factory
        :return: a database object
        """
        database_types = {cls.__name__:cls for cls in NotificationDatabase.__subclasses__()}
        return database_types[name](*args, **kwargs)
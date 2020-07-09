from typing import NoReturn, List, NamedTuple, Tuple, Dict
from abc import abstractmethod
from datetime import datetime


class PrivateMessage(NamedTuple):
    """
    A user private message
    """
    from_user: str
    to_user: str
    timestamp: datetime
    message: str


class FriendDatabase:
    """
    Friend database abstraction
    """

    @abstractmethod
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

    @abstractmethod
    def accept_friend_request(self, from_user_email: str,
                              to_user_email: str) -> NoReturn:
        """
        Accepts an existing friend request

        :raises:
            UnexistentFriendRequest: the friend request does not exist or is not pending

        :param from_user_email: the user that requested the friendship
        :param to_user_email: the target user of the request
        """

    @abstractmethod
    def reject_friend_request(self, from_user_email: str,
                              to_user_email: str) -> NoReturn:
        """
        Rejects an existing friend request

        :raises:
            UnexistentFriendRequest: the friend request does not exist or is not pending

        :param from_user_email: the user that requested the friendship
        :param to_user_email: the target user of the request
        """

    @abstractmethod
    def get_friend_requests(self, user_email: str) -> List[str]:
        """
        Gets all the user emails that have sent a user request to the user

        :param user_email: the user to query for its friend requests
        :return: a list of emails
        """

    @abstractmethod
    def get_friends(self, user_email: str) -> List[str]:
        """
        Gets all the user emails that are friends of the user

        :param user_email: the user to query for its friend
        :return: a list of emails
        """

    @abstractmethod
    def delete_friendship(self, user_email1: str, user_email2: str) -> NoReturn:
        """
        Delete friendship if exists

        :param user_email1: first user email
        :param user_email2: second user email
        """

    @abstractmethod
    def are_friends(self, user_email1: str, user_email2: str) -> bool:
        """
        Check if user1 is friend with user2

        :param user_email1: the first user email
        :param user_email2: the second user email
        :return: a boolean indicating whether user1 is friend user2's friend
        """

    @abstractmethod
    def exists_friend_request(self, from_user_email: str, to_user_email: str) -> bool:
        """
        Check if exists friend request from 'requestor' to 'receiver'

        :param from_user_email: the requestor of the friendship
        :param to_user_email: the receiver of the request
        :return: a boolean indicating whether the friend request exists
        """

    @abstractmethod
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

    @abstractmethod
    def get_conversation(self, user1_email: str, user2_email: str,
                         per_page: int, page: int) -> Tuple[List[PrivateMessage], int]:
        """
        Get the paginated conversation between user1 and user2

        :raises:
            NoMoreMessagesError: the page has no messages

        :param user1_email: the email of user1
        :param user2_email: the email of user2
        :param per_page: the messages per page
        :param page: the page for the message, starting from 0
        :return: the list of private messages and the number of pages
        """

    @abstractmethod
    def get_conversations(self, user_email: str) -> Tuple[List[Dict], List[PrivateMessage]]:
        """
        Get all the conversations ordered by recent activity

        :param user_email: the email of the user for getting the conversations
        :return: a tuple (list of user data, list of last private message)
        """

    @classmethod
    def factory(cls, name: str, *args, **kwargs) -> 'FriendDatabase':
        """
        Factory pattern for database

        :param name: the name of the database to create in the factory
        :return: a database object
        """
        database_types = {cls.__name__:cls for cls in FriendDatabase.__subclasses__()}
        return database_types[name](*args, **kwargs)

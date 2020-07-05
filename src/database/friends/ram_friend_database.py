from typing import NoReturn, List, Dict, Set, Tuple
from abc import abstractmethod
from src.database.friends.exceptions.users_already_friends_error import UsersAlreadyFriendsError
from src.database.friends.exceptions.unexistent_friend_requests import UnexistentFriendRequest
from src.database.friends.exceptions.users_are_not_friends_error import UsersAreNotFriendsError
from src.database.friends.exceptions.no_more_messages_error import NoMoreMessagesError
import math
from src.database.friends.friend_database import FriendDatabase, PrivateMessage
from datetime import datetime


class RamFriendDatabase(FriendDatabase):
    """
    Friend database in ram
    """
    friend_request: Dict[str, Set[str]]
    friends: Set[Tuple[str, str]]

    def __init__(self):
        self.friend_requests = {}
        self.friends = set()
        self.messages = {}

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
        if from_user_email not in self.friend_requests:
            self.friend_requests[from_user_email] = {to_user_email}
        else:
            self.friend_requests[from_user_email].update([to_user_email])

    def accept_friend_request(self, from_user_email: str,
                              to_user_email: str) -> NoReturn:
        """
        Accepts an existing friend request

        :raises:
            UnexistentFriendRequest: the friend request does not exist or is not pending

        :param from_user_email: the user that requested the friendship
        :param to_user_email: the target user of the request
        """
        if from_user_email not in self.friend_requests or \
                to_user_email not in self.friend_requests[from_user_email]:
            raise UnexistentFriendRequest
        self.friend_requests[from_user_email].remove(to_user_email)
        friend_tuple = list(sorted([from_user_email,to_user_email]))
        friend_tuple = (friend_tuple[0], friend_tuple[1])
        self.friends.update([friend_tuple])

    def reject_friend_request(self, from_user_email: str,
                              to_user_email: str) -> NoReturn:
        """
        Rejects an existing friend request

        :raises:
            UnexistentFriendRequest: the friend request does not exist or is not pending

        :param from_user_email: the user that requested the friendship
        :param to_user_email: the target user of the request
        """
        if from_user_email not in self.friend_requests or \
                to_user_email not in self.friend_requests[from_user_email]:
            raise UnexistentFriendRequest
        self.friend_requests[from_user_email].remove(to_user_email)

    def get_friend_requests(self, user_email: str) -> List[str]:
        """
        Gets all the user emails that have sent a user request to the user

        :param user_email: the user to query for its friend requests
        :return: a list of emails
        """
        return list(k for k,v in self.friend_requests.items() if user_email in v)

    def get_friends(self, user_email: str) -> List[str]:
        """
        Gets all the user emails that are friends of the user

        :param user_email: the user to query for its friend
        :return: a list of emails
        """
        friends = [f for t in self.friends for f in t if user_email in t]
        friends = [f for f in friends if f!=user_email]
        return friends

    def are_friends(self, user_email1: str, user_email2: str) -> bool:
        """
        Check if user1 is friend with user2

        :param user_email1: the first user email
        :param user_email2: the second user email
        :return: a boolean indicating whether user1 is friend user2's friend
        """
        friend_tuple = list(sorted([user_email1,user_email2]))
        friend_tuple = (friend_tuple[0], friend_tuple[1])
        return friend_tuple in self.friends

    def exists_friend_request(self, from_user_email: str, to_user_email: str) -> bool:
        """
        Check if exists friend request from 'requestor' to 'receiver'

        :param from_user_email: the requestor of the friendship
        :param to_user_email: the receiver of the request
        :return: a boolean indicating whether the friend request exists
        """
        if from_user_email not in self.friend_requests or \
                to_user_email not in self.friend_requests[from_user_email]:
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
        if (from_user_email, to_user_email) not in self.messages:
            self.messages[(from_user_email, to_user_email)] = []
        message = PrivateMessage(from_user=from_user_email, to_user=to_user_email,
                                 timestamp=datetime.now(), message=message)
        self.messages[(from_user_email, to_user_email)].append(message)

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
        total_messages = []
        if (user1_email, user2_email) in self.messages:
            total_messages += self.messages[(user1_email, user2_email)]
        if (user2_email, user1_email) in self.messages:
            total_messages += self.messages[(user2_email, user1_email)]
        total_messages = sorted(total_messages, key=lambda x: x.timestamp, reverse=True)
        pages = int(math.ceil(len(total_messages)/per_page))
        if not page <= pages and page != 0:
            raise NoMoreMessagesError()
        return total_messages[page*per_page:(page+1)*per_page], pages

    def get_conversations(self, user_email: str) -> Tuple[List[Dict], List[PrivateMessage]]:
        """
        Get all the conversations ordered by recent activity

        :param user_email: the email of the user for getting the conversations
        :return: a tuple (list of user data, list of last private message)
        """
        user_messages_keys = [(u1, u2) for u1, u2 in self.messages.keys() if u1 == user_email or u2 == user_email]
        last_messages = []
        for key in user_messages_keys:
            last_messages.append(self.messages[key][-1])
        last_messages = sorted(last_messages, key=lambda x: x.timestamp, reverse=True)

        already_considered_users = []
        last_messages_per_user = []
        for m in last_messages:
            other_user = (m.from_user if m.from_user != user_email else m.to_user)
            if other_user in already_considered_users:
                continue
            already_considered_users.append({"email": other_user})
            last_messages_per_user.append(m)

        return already_considered_users, last_messages
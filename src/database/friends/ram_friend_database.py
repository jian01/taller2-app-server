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

    def delete_friendship(self, user_email1: str, user_email2: str) -> NoReturn:
        """
        Delete friendship if exists

        :param user_email1: first user email
        :param user_email2: second user email
        """
        friend_tuple = list(sorted([user_email1,user_email2]))
        friend_tuple = (friend_tuple[0], friend_tuple[1])
        try:
            self.friends.remove(friend_tuple)
        except KeyError:
            return

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
        total_messages = []
        if (requestor_email, other_user_email) in self.messages:
            total_messages += self.messages[(requestor_email, other_user_email)]
        if (other_user_email, requestor_email) in self.messages:
            total_messages += self.messages[(other_user_email, requestor_email)]
        total_messages = [m for m in total_messages if not m.hidden_to or requestor_email not in m.hidden_to]
        total_messages = sorted(total_messages, key=lambda x: x.timestamp, reverse=True)
        pages = int(math.ceil(len(total_messages)/per_page))
        if not page < pages and page != 0:
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
            visible_messages = [m for m in self.messages[key] if not m.hidden_to or user_email not in m.hidden_to]
            if visible_messages:
                last_messages.append(visible_messages[-1])
        last_messages = sorted(last_messages, key=lambda x: x.timestamp, reverse=True)

        already_considered_users = []
        last_messages_per_user = []
        for m in last_messages:
            other_user = (m.from_user if m.from_user != user_email else m.to_user)
            if other_user in already_considered_users:
                continue
            already_considered_users.append(other_user)
            last_messages_per_user.append(m)

        already_considered_users = [{"email":e} for e in already_considered_users]

        return already_considered_users, last_messages_per_user

    def delete_conversation(self, deletor_email: str, deleted_email: str) -> NoReturn:
        """
        Deletes the conversation between two users but just for the deletor

        :param deletor_email: the email of the one that deletes the conversation
        :param deleted_email: the email of the other user of the conversation
        """
        if (deletor_email, deleted_email) in self.messages:
            for i in range(len(self.messages[(deletor_email, deleted_email)])):
                if self.messages[(deletor_email, deleted_email)][i].hidden_to:
                    self.messages[(deletor_email, deleted_email)][i].hidden_to.update([deletor_email])
                else:
                    previous_pm = self.messages[(deletor_email, deleted_email)][i]
                    self.messages[(deletor_email, deleted_email)][i] = PrivateMessage(from_user=previous_pm.from_user,
                                                                                      to_user=previous_pm.to_user,
                                                                                      timestamp=previous_pm.timestamp,
                                                                                      message=previous_pm.message,
                                                                                      hidden_to={deletor_email})
        if (deleted_email, deletor_email) in self.messages:
            for i in range(len(self.messages[(deleted_email, deletor_email)])):
                if self.messages[(deleted_email, deletor_email)][i].hidden_to:
                    self.messages[(deleted_email, deletor_email)][i].hidden_to.update([deletor_email])
                else:
                    previous_pm = self.messages[(deleted_email, deletor_email)][i]
                    self.messages[(deleted_email, deletor_email)][i] = PrivateMessage(from_user=previous_pm.from_user,
                                                                                      to_user=previous_pm.to_user,
                                                                                      timestamp=previous_pm.timestamp,
                                                                                      message=previous_pm.message,
                                                                                      hidden_to={deletor_email})
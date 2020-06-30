from typing import NoReturn, List, Dict, Set, Tuple
from abc import abstractmethod
from src.database.friends.exceptions.users_already_friends_error import UsersAlreadyFriendsError
from src.database.friends.exceptions.unexistent_friend_requests import UnexistentFriendRequest
from src.database.friends.friend_database import FriendDatabase

class RamFriendDatabase(FriendDatabase):
    """
    Friend database in ram
    """
    friend_request: Dict[str, Set[str]]
    friends: Set[Tuple[str, str]]

    def __init__(self):
        self.friend_requests = {}
        self.friends = set()

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
            self.friend_requests.update([to_user_email])

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
import os
import requests
from src.services.exceptions.invalid_credentials_error import InvalidCredentialsError
from src.services.exceptions.invalid_login_token_error import InvalidLoginTokenError
from src.services.exceptions.user_already_registered_error import UserAlreadyRegisteredError
from src.services.exceptions.invalid_register_field_error import InvalidRegisterFieldError
from src.services.exceptions.unexistent_user_error import UnexistentUserError
from src.services.exceptions.invalid_recovery_token_error import InvalidRecoveryTokenError
from src.services.exceptions.unauthorized_user_error import UnauthorizedUserError
from src.services.exceptions.no_more_pages_error import NoMorePagesError
from src.model.photo import Photo
from io import BytesIO
from typing import Optional, NoReturn, Dict, Any, List
from functools import lru_cache
import base64
import logging

NEW_API_KEY_ENDPOINT = "/api_key"
USER_LOGIN_ENDPOINT = "/user/login"
USER_ENDPOINT = "/user"
REGISTERED_USERS_ENDPOINT = "/registered_users"
RECOVERY_EMAIL_SEND_ENDPOINT = "/user/recover_password"
RECOVER_PASSWORD_ENDPOINT = "/user/new_password"
APP_SERVERS_ENDPOINT = "/app_servers"

USER_ALREADY_REGISTERED_MESSAGE = "User with email %s is already registered"

DEFAULT_TIMEOUT = 15

class AuthServer:
    """
    The connection to the auth server
    """
    logger = logging.getLogger(__module__)
    def __init__(self, auth_server_url_env_name: str, auth_server_secret_env_name: str,
                 server_alias_env_name: str, server_health_endpoint_url_env_name: str):
        """

        :param auth_server_url_env_name: the env name containing the auth server url
        :param auth_server_secret_env_name: the env name containing the auth server secret
        :param server_alias_env_name: the env name containing the server alias
        :param server_health_endpoint_url_env_name: the env name containing the app server health endpoint
        """
        self.logger.debug("Initializing auth server")
        self.auth_url = os.getenv(auth_server_url_env_name)
        response = requests.post(self.auth_url+NEW_API_KEY_ENDPOINT,
                                 json={"secret": os.getenv(auth_server_secret_env_name),
                                       "alias": os.getenv(server_alias_env_name),
                                       "health_endpoint": os.getenv(server_health_endpoint_url_env_name)},
                                 timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        self.api_key = response.json()["api_key"]
        self.logger.info("Connected to auth server")

    def user_login(self, email: str, plain_password: str) -> Dict:
        """
        Returns a login token for the user that logs in

        :param email: the email of the user
        :param plain_password: the password of the user
        :return: a dict with login data
        """
        self.logger.debug("Logging for user with email %s" % email)
        response = requests.post(self.auth_url+USER_LOGIN_ENDPOINT,
                                 json={"email": email,
                                       "password": plain_password},
                                 params={"api_key": self.api_key},
                                 timeout=DEFAULT_TIMEOUT)
        if response.status_code == 403:
            raise InvalidCredentialsError
        if response.status_code == 404:
            raise UnexistentUserError
        response.raise_for_status()
        return response.json()

    @lru_cache(maxsize=300)
    def get_logged_email(self, login_token: str) -> str:
        """
        Gets the user corresponding to a login token

        :param login_token: the login token
        :return: the email corresponding to the logged user
        """
        response = requests.get(self.auth_url+USER_LOGIN_ENDPOINT,
                                params={"api_key": self.api_key},
                                headers={"Authorization": "Bearer %s" % login_token},
                                timeout=DEFAULT_TIMEOUT)
        if response.status_code == 401:
            raise InvalidLoginTokenError
        response.raise_for_status()
        return response.json()["email"]

    def user_register(self, email: str, fullname: str, plain_password: str,
                      phone_number: str, photo: Optional[Photo]=None) -> NoReturn:
        """
        Registers a new user

        :param email: the email of the user to register
        :param fullname: the name of the user
        :param plain_password: the password
        :param phone_number: the phone number
        :param photo: the photo of the user
        """
        self.logger.debug("Registering user with email %s" % email)
        photo_bytes = None
        if photo:
            photo_bytes = base64.b64decode(photo.get_base64())
        response = requests.post(self.auth_url+USER_ENDPOINT,
                                 data={"email": email,
                                       "fullname": fullname,
                                       "password": plain_password,
                                       "phone_number": phone_number},
                                 params={"api_key": self.api_key},
                                 files={"photo": photo_bytes} if photo_bytes else {},
                                 timeout=DEFAULT_TIMEOUT)
        if response.status_code == 400:
            if response.json()["message"] == USER_ALREADY_REGISTERED_MESSAGE % email:
                raise UserAlreadyRegisteredError
            else:
                raise InvalidRegisterFieldError(response.json()["message"])
        response.raise_for_status()

    def profile_query(self, email: str) -> Dict:
        """
        Queries an user by its email

        :param email: the email of the user to query
        :return: a dict containing all the user data
        """
        self.logger.debug("Querying profile for user with email %s" % email)
        response = requests.get(self.auth_url+USER_ENDPOINT,
                                params={"api_key": self.api_key, "email": email},
                                timeout=DEFAULT_TIMEOUT)
        if response.status_code == 404:
            raise UnexistentUserError
        response.raise_for_status()
        return response.json()

    def send_recovery_email(self, email: str) -> NoReturn:
        """
        Send a recovery email to the user

        :param email: the email of the user
        """
        self.logger.debug("Sending recovery email for user %s" % email)
        response = requests.post(self.auth_url + RECOVERY_EMAIL_SEND_ENDPOINT,
                                 json={"email": email},
                                 params={"api_key": self.api_key},
                                 timeout=DEFAULT_TIMEOUT)
        if response.status_code == 404:
            raise UnexistentUserError
        response.raise_for_status()

    def recover_password(self, email: str, token: str, new_password: str) -> NoReturn:
        """
        Recovers a password with a recovery token

        :param email: the email of the user
        :param token: the recovery token for that user
        :param new_password: the new password to ser
        """
        self.logger.debug("Recovering password for user %s" % email)
        response = requests.post(self.auth_url + RECOVER_PASSWORD_ENDPOINT,
                                 json={"email": email,
                                       "token": token,
                                       "new_password": new_password},
                                 params={"api_key": self.api_key},
                                 timeout=DEFAULT_TIMEOUT)
        if response.status_code == 400:
            raise InvalidRecoveryTokenError
        if response.status_code == 404:
            raise UnexistentUserError
        response.raise_for_status()

    def profile_update(self, email: str, user_token: str,
                       password: Optional[str] = None,
                       fullname: Optional[str] = None, phone_number: Optional[str] = None,
                       photo: Optional[Photo] = None) -> NoReturn:
        """
        Updates a user profile

        :param email: the email of the user to be updated
        :param user_token: the user login token
        :param password: the password to be updated
        :param fullname: the fullname to be updated
        :param phone_number: the phone number to be updated
        :param photo: the photo bytes to be updated
        """
        self.logger.debug("Updating %s user data" % email)
        content = {}
        if password:
            content["password"] = password
        if fullname:
            content["fullname"] = fullname
        if phone_number:
            content["phone_number"] = phone_number
        photo_bytes = None
        if photo:
            photo_bytes = base64.b64decode(photo.get_base64())
        if not content and not photo_bytes:
            return
        response = requests.put(self.auth_url + USER_ENDPOINT, data=content,
                                params={"api_key": self.api_key, "email": email},
                                files={"photo": photo_bytes} if photo_bytes else {},
                                timeout=DEFAULT_TIMEOUT,
                                headers={"Authorization": "Bearer %s" % user_token})
        if response.status_code == 403:
            raise UnauthorizedUserError
        if response.status_code == 404:
            raise UnexistentUserError
        response.raise_for_status()

    def user_delete(self, email:str, user_token: str) -> NoReturn:
        """
        Deletes a user

        :param email: the email of the user to delete
        :param user_token: the login token
        """
        self.logger.debug("Deleting %s user" % email)
        response = requests.delete(self.auth_url + USER_ENDPOINT,
                                   params={"api_key": self.api_key, "email": email},
                                   timeout=DEFAULT_TIMEOUT,
                                   headers={"Authorization": "Bearer %s" % user_token})
        if response.status_code == 403:
            raise UnauthorizedUserError
        if response.status_code == 404:
            raise UnexistentUserError
        response.raise_for_status()

    def get_registered_users(self, page: int, users_per_page: int, user_token: str) -> Dict[str, Any]:
        """
        Get the list of registered users paginated

        :param page: the page number
        :param users_per_page: the users per page
        :param user_token: the user token (must be admin)
        :return: a dictionary {"results":[users], "pages": number of pages}
        """
        self.logger.debug("Listing registered users")
        response = requests.get(self.auth_url + REGISTERED_USERS_ENDPOINT,
                                params={"api_key": self.api_key,
                                        "page": page,
                                        "users_per_page": users_per_page},
                                timeout=DEFAULT_TIMEOUT,
                                headers={"Authorization": "Bearer %s" % user_token})
        if response.status_code == 403:
            raise UnauthorizedUserError
        if response.status_code == 404:
            raise NoMorePagesError
        response.raise_for_status()
        return response.json()

    def get_app_servers_statuses(self) -> List[Dict[str, Any]]:
        """
        Get the app servers statuses

        :return: a list of dictionaries with data
        """
        self.logger.debug("Getting app server status")
        response = requests.get(self.auth_url + APP_SERVERS_ENDPOINT, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        return response.json()
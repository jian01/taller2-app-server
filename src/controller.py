import json
import logging
from typing import Optional, Tuple
from flask import request
from flask_httpauth import HTTPTokenAuth
from constants import messages
from src.services.auth_server import AuthServer
from src.model.photo import Photo
from src.services.exceptions.invalid_credentials_error import InvalidCredentialsError
from src.services.exceptions.user_already_registered_error import UserAlreadyRegisteredError
from src.services.exceptions.invalid_login_token_error import InvalidLoginTokenError
from src.services.exceptions.unexistent_user_error import UnexistentUserError
from src.services.exceptions.invalid_register_field_error import InvalidRegisterFieldError
from src.services.exceptions.invalid_recovery_token_error import InvalidRecoveryTokenError
from src.services.exceptions.unauthorized_user_error import UnauthorizedUserError
from src.services.exceptions.invalid_video_format_error import InvalidVideoFormatError
from src.database.videos.video_database import VideoDatabase, VideoData
from src.database.friends.friend_database import FriendDatabase
from src.database.friends.exceptions.users_already_friends_error import UsersAlreadyFriendsError
from src.database.friends.exceptions.unexistent_friend_requests import UnexistentFriendRequest
from src.database.friends.exceptions.unexistent_requestor_user_error import UnexistentRequestorUserError
from src.database.friends.exceptions.unexistent_target_user_error import UnexistentTargetUserError
from src.services.media_server import MediaServer
from datetime import datetime


auth = HTTPTokenAuth(scheme='Bearer')

LOGIN_MANDATORY_FIELDS = {"email", "password"}
API_KEY_CREATE_MANDATORY_FIELDS = {"alias", "secret"}
RECOVER_PASSWORD_MANDATORY_FIELDS = {"email"}
NEW_PASSWORD_MANDATORY_FIELDS = {"email", "new_password", "token"}
USERS_REGISTER_MANDATORY_FIELDS = {"email", "password", "phone_number", "fullname"}
UPLOAD_VIDEO_MANDATORY_FIELDS = {"title", "location", "visible"}
FRIEND_REQUEST_MANDATORY_FIELDS = {"other_user_email"}

class Controller:
    logger = logging.getLogger(__name__)
    def __init__(self, auth_server: AuthServer,
                 media_server: MediaServer,
                 video_database: VideoDatabase,
                 friend_database: FriendDatabase):
        """
        Here the init should receive all the parameters needed to know how to answer all the queries
        """
        self.auth_server = auth_server
        self.media_server = media_server
        self.video_database = video_database
        self.friend_database = friend_database
        @auth.verify_token
        def verify_token(token) -> Optional[Tuple[str, str]]:
            """
            Verifies a token

            :param token: the token to verify
            :return: the corresponding user email and the token used
            """
            if not token:
                return
            try:
                return auth_server.get_logged_email(token), token
            except InvalidLoginTokenError:
                return

    def api_health(self):
        """
        A dumb api health

        :return: a tuple with the text and the status to return
        """
        return messages.SUCCESS_JSON, 200

    def users_register(self):
        """
        Handles the user registration
        :return: a json with a success message on success or an error in another case
        """
        content = request.form
        if not USERS_REGISTER_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug((messages.MISSING_FIELDS_ERROR % (USERS_REGISTER_MANDATORY_FIELDS - set(content.keys())) ))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % (USERS_REGISTER_MANDATORY_FIELDS - set(content.keys())) ), 400
        photo = None
        if 'photo' in request.files:
            photo = Photo.from_bytes(request.files['photo'].stream)
        try:
            self.auth_server.user_register(email=content["email"], fullname=content["fullname"],
                                           phone_number=content["phone_number"], photo=photo,
                                           plain_password=content["password"])
        except UserAlreadyRegisteredError:
            self.logger.debug(messages.USER_ALREADY_REGISTERED_MESSAGE)
            return messages.ERROR_JSON % messages.USER_ALREADY_REGISTERED_MESSAGE, 400
        except InvalidRegisterFieldError as e:
            self.logger.debug(str(e))
            return messages.ERROR_JSON % str(e), 400
        return messages.SUCCESS_JSON, 200

    def users_login(self):
        """
        Handles the user login
        :return: a json with the login_token on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not LOGIN_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug((messages.MISSING_FIELDS_ERROR % (LOGIN_MANDATORY_FIELDS - set(content.keys())) ))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % (LOGIN_MANDATORY_FIELDS - set(content.keys())) ), 400
        try:
            login_token = self.auth_server.user_login(email=content["email"], plain_password=content["password"])
        except InvalidCredentialsError:
            self.logger.debug(messages.WRONG_CREDENTIALS_MESSAGE)
            return messages.ERROR_JSON % messages.WRONG_CREDENTIALS_MESSAGE, 403
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % content["email"])
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % content["email"]), 404
        return json.dumps({"login_token": login_token})

    def users_profile_query(self):
        """
        Handles the user recovering
        :return: a json with the data of the requested user on success or an error in another case
        """
        email_query = request.args.get('email')
        if not email_query:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % "email"))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % "email"), 400
        try:
            user_data = self.auth_server.profile_query(email_query)
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % email_query)
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % email_query), 404
        return json.dumps(user_data)

    def users_send_recovery_email(self):
        """
        Recovers a user password by sending a recovery token through email
        :return: a json with a success message on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not RECOVER_PASSWORD_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug((messages.MISSING_FIELDS_ERROR % (RECOVER_PASSWORD_MANDATORY_FIELDS - set(content.keys())) ))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % (RECOVER_PASSWORD_MANDATORY_FIELDS - set(content.keys())) ), 400
        try:
            self.auth_server.send_recovery_email(content["email"])
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % content["email"])
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % content["email"]), 404
        return messages.SUCCESS_JSON, 200

    def users_recover_password(self):
        """
        Handles the new password setting
        :return: a json with a success message on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not NEW_PASSWORD_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug((messages.MISSING_FIELDS_ERROR % (NEW_PASSWORD_MANDATORY_FIELDS - set(content.keys())) ))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % (NEW_PASSWORD_MANDATORY_FIELDS - set(content.keys())) ), 400
        try:
            self.auth_server.recover_password(content["email"], content["token"], content["new_password"])
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % content["email"])
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % content["email"]), 404
        except InvalidRecoveryTokenError:
            self.logger.debug(messages.INVALID_RECOVERY_TOKEN_MESSAGE % content["email"])
            return messages.ERROR_JSON % (messages.INVALID_RECOVERY_TOKEN_MESSAGE % content["email"]), 400
        return messages.SUCCESS_JSON, 200

    @auth.login_required
    def users_profile_update(self):
        """
        Handles updating a user's profile
        :return: a json with a success message on success or an error in another case
        """
        email_query = request.args.get('email')
        if not email_query:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % "email"))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % "email"), 400
        email_token = auth.current_user()[0]
        token = auth.current_user()[1]
        if email_token != email_query:
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        content = request.form
        password = content["password"] if "password" in content else None
        fullname = content["fullname"] if "fullname" in content else None
        phone_number = content["phone_number"] if "phone_number" in content else None
        photo = Photo.from_bytes(request.files['photo'].stream) if 'photo' in request.files else None
        try:
            self.auth_server.profile_update(email=email_query, user_token=token,
                                            password=password, fullname=fullname,
                                            phone_number=phone_number,photo=photo)
        except UnauthorizedUserError:
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % email_query)
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % email_query), 404
        return messages.SUCCESS_JSON, 200

    @auth.login_required
    def users_video_upload(self):
        """
        Uploads a video for a user
        :return: a json with the video data or an error in another case
        """
        email_query = request.args.get('email')
        if not email_query:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % "email"))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % "email"), 400
        email_token = auth.current_user()[0]
        if email_token != email_query:
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        content = request.form
        if not UPLOAD_VIDEO_MANDATORY_FIELDS.issubset(content.keys()) or not "video" in request.files:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % (UPLOAD_VIDEO_MANDATORY_FIELDS - set(content.keys())) ))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % (UPLOAD_VIDEO_MANDATORY_FIELDS - set(content.keys())) ), 400
        title = content["title"]
        location = content["location"]
        visible = True if content["visible"]=="true" else False
        video = request.files['video'].stream
        description = content["description"] if "description" in content else None
        try:
            file_location = self.media_server.upload_video(user_email=email_query,
                                                           title=title, video=video)
        except InvalidVideoFormatError:
            self.logger.debug(messages.INVALID_VIDEO_FORMAT)
            return messages.ERROR_JSON % messages.INVALID_VIDEO_FORMAT, 400
        video_data = VideoData(title=title, location=location, creation_time=datetime.now(),
                               file_location=file_location, visible=visible, description=description)
        self.video_database.add_video(user_email=email_query, video_data=video_data)
        response_dict = video_data._asdict()
        response_dict["creation_time"] = response_dict["creation_time"].isoformat()
        return json.dumps(response_dict), 200

    @auth.login_required
    def users_list_videos(self):
        """
        Uploads a video for a user
        :return: a json with the videos data or an error in another case
        """
        email_query = request.args.get('email')
        if not email_query:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % "email"))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % "email"), 400
        email_token = auth.current_user()[0]
        user_videos = self.video_database.list_user_videos(email_query)
        user_videos = [video_data._asdict() for video_data in user_videos]
        if email_query != email_token:
            user_videos = [video_data for video_data in user_videos if video_data["visible"]]
        for i in range(len(user_videos)):
            user_videos[i]["creation_time"] = user_videos[i]["creation_time"].isoformat()
        return json.dumps(user_videos), 200

    def list_top_videos(self):
        """
        Uploads a video for a user
        :return: a json with the videos data or an error in another case
        """
        top_videos_data = self.video_database.list_top_videos()
        user_videos = [data[1]._asdict() for data in top_videos_data]
        user_emails = [data[0] for data in top_videos_data]
        for i in range(len(user_videos)):
            user_videos[i]["creation_time"] = user_videos[i]["creation_time"].isoformat()
        return json.dumps([{"user": u,"video": v} for v,u in zip(user_videos, user_emails)]), 200

    @auth.login_required
    def user_send_friend_request(self):
        """
        Send a friend request to another user
        :return: a json with a success message on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not FRIEND_REQUEST_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug(messages.MISSING_FIELDS_ERROR % (FRIEND_REQUEST_MANDATORY_FIELDS - set(content.keys())))
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % (FRIEND_REQUEST_MANDATORY_FIELDS - set(content.keys())), 400
        email_token = auth.current_user()[0]
        try:
            self.friend_database.create_friend_request(email_token, content["other_user_email"])
        except UnexistentTargetUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % content["other_user_email"])
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % content["other_user_email"]), 404
        except UsersAlreadyFriendsError:
            self.logger.debug(messages.USERS_ALREADY_FRIEND_ERROR)
            return messages.ERROR_JSON % messages.USERS_ALREADY_FRIEND_ERROR, 400
        except UnexistentRequestorUserError:
            self.logger.debug(messages.INTERNAL_ERROR_CONTACT_ADMINISTRATION)
            return messages.ERROR_JSON % messages.INTERNAL_ERROR_CONTACT_ADMINISTRATION, 500
        return messages.SUCCESS_JSON, 200

    @auth.login_required
    def user_list_friend_requests(self):
        """
        Send a friend request to another user
        :return: a json with the data of the users or an error in another case
        """
        email_token = auth.current_user()[0]
        friend_emails = self.friend_database.get_friend_requests(email_token)
        friends = [self.auth_server.profile_query(email) for email in friend_emails]
        return json.dumps(friends), 200

    @auth.login_required
    def user_accept_friend_request(self):
        """
        Accept an existing friend request
        :return: a json with a success message on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not FRIEND_REQUEST_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug(messages.MISSING_FIELDS_ERROR % (FRIEND_REQUEST_MANDATORY_FIELDS - set(content.keys())))
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % (FRIEND_REQUEST_MANDATORY_FIELDS - set(content.keys())), 400
        email_token = auth.current_user()[0]
        try:
            self.friend_database.accept_friend_request(content["other_user_email"], email_token)
        except UnexistentFriendRequest:
            self.logger.debug(messages.UNEXISTENT_FRIEND_REQUEST % (content["other_user_email"], email_token))
            return messages.ERROR_JSON % (messages.UNEXISTENT_FRIEND_REQUEST %
                                          (content["other_user_email"], email_token)), 404
        return messages.SUCCESS_JSON, 200

    @auth.login_required
    def user_reject_friend_request(self):
        """
        Accept an existing friend request
        :return: a json with a success message on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not FRIEND_REQUEST_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug(messages.MISSING_FIELDS_ERROR % (FRIEND_REQUEST_MANDATORY_FIELDS - set(content.keys())))
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % (FRIEND_REQUEST_MANDATORY_FIELDS - set(content.keys())), 400
        email_token = auth.current_user()[0]
        try:
            self.friend_database.reject_friend_request(content["other_user_email"], email_token)
        except UnexistentFriendRequest:
            self.logger.debug(messages.UNEXISTENT_FRIEND_REQUEST % (content["other_user_email"], email_token))
            return messages.ERROR_JSON % (messages.UNEXISTENT_FRIEND_REQUEST %
                                          (content["other_user_email"], email_token)), 404
        return messages.SUCCESS_JSON, 200

    @auth.login_required
    def user_list_friends(self):
        """
        List friends of an user
        :return: a json with a success message on success or an error in another case
        """
        email_query = request.args.get('email')
        if not email_query:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "email")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "email", 400
        email_token = auth.current_user()[0]
        if email_token != email_query and not self.friend_database.are_friends(email_token, email_query):
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        friend_emails = self.friend_database.get_friends(email_query)
        friends = [self.auth_server.profile_query(email) for email in friend_emails]
        return json.dumps(friends), 200
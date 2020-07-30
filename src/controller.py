import json
import logging
from typing import Optional, Tuple
from flask import request
from flask_httpauth import HTTPTokenAuth
from constants import messages
from flask_cors import cross_origin
from src.services.auth_server import AuthServer
from src.model.photo import Photo
from src.services.exceptions.invalid_credentials_error import InvalidCredentialsError
from src.services.exceptions.user_already_registered_error import UserAlreadyRegisteredError
from src.services.exceptions.invalid_login_token_error import InvalidLoginTokenError
from src.services.exceptions.unexistent_user_error import UnexistentUserError
from src.services.exceptions.unexistent_video_error import UnexistentVideoError
from src.services.exceptions.invalid_register_field_error import InvalidRegisterFieldError
from src.services.exceptions.invalid_recovery_token_error import InvalidRecoveryTokenError
from src.services.exceptions.unauthorized_user_error import UnauthorizedUserError
from src.services.exceptions.invalid_video_format_error import InvalidVideoFormatError
from src.database.videos.video_database import VideoDatabase, VideoData, Reaction
from src.database.friends.friend_database import FriendDatabase
from src.database.statistics.statistics_database import StatisticsDatabase, ApiCallsStatistics
from src.database.friends.exceptions.users_already_friends_error import UsersAlreadyFriendsError
from src.database.friends.exceptions.unexistent_friend_requests import UnexistentFriendRequest
from src.database.friends.exceptions.unexistent_requestor_user_error import UnexistentRequestorUserError
from src.database.friends.exceptions.unexistent_target_user_error import UnexistentTargetUserError
from src.database.friends.exceptions.users_are_not_friends_error import UsersAreNotFriendsError
from src.database.friends.exceptions.no_more_messages_error import NoMoreMessagesError
from src.database.videos.exceptions.no_more_videos_error import NoMoreVideosError
from src.services.exceptions.no_more_pages_error import NoMorePagesError
from src.services.media_server import MediaServer
from src.database.notifications.notification_database import NotificationDatabase
from datetime import datetime
from src.register_api_call_decorator import register_api_call

auth = HTTPTokenAuth(scheme='Bearer')

LOGIN_MANDATORY_FIELDS = {"email", "password"}
API_KEY_CREATE_MANDATORY_FIELDS = {"alias", "secret"}
RECOVER_PASSWORD_MANDATORY_FIELDS = {"email"}
NEW_PASSWORD_MANDATORY_FIELDS = {"email", "new_password", "token"}
USERS_REGISTER_MANDATORY_FIELDS = {"email", "password", "phone_number", "fullname"}
UPLOAD_VIDEO_MANDATORY_FIELDS = {"title", "location", "visible"}
FRIEND_REQUEST_MANDATORY_FIELDS = {"other_user_email"}
VIDEO_REACTION_MANDATORY_FIELDS = {"target_email", "video_title", "reaction"}
VIDEO_REACTION_DELETE_MANDATORY_FIELDS = {"target_email", "video_title"}
SEND_MESSAGE_MANDATORY_FIELDS = {"other_user_email", "message"}
VIDEO_COMMENT_MANDATORY_FIELDS = {"target_email", "video_title", "comment"}


class Controller:
    logger = logging.getLogger(__module__)

    def __init__(self, auth_server: AuthServer,
                 media_server: MediaServer,
                 video_database: VideoDatabase,
                 friend_database: FriendDatabase,
                 statistic_database: StatisticsDatabase,
                 notification_database: NotificationDatabase):
        """
        Here the init should receive all the parameters needed to know how to answer all the queries
        """
        self.auth_server = auth_server
        self.media_server = media_server
        self.video_database = video_database
        self.friend_database = friend_database
        self.statistic_database = statistic_database
        self.notification_database = notification_database

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

    @register_api_call
    def api_health(self):
        """
        A dumb api health

        :return: a tuple with the text and the status to return
        """
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @cross_origin()
    def users_register(self):
        """
        Handles the user registration
        :return: a json with a success message on success or an error in another case
        """
        content = request.form
        if not USERS_REGISTER_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug((messages.MISSING_FIELDS_ERROR % (USERS_REGISTER_MANDATORY_FIELDS - set(content.keys()))))
            return messages.ERROR_JSON % (
                        messages.MISSING_FIELDS_ERROR % (USERS_REGISTER_MANDATORY_FIELDS - set(content.keys()))), 400
        photo = None
        if 'photo' in request.files:
            photo = Photo.from_bytes(request.files['photo'].stream)
        try:
            self.auth_server.user_register(email=content["email"], fullname=content["fullname"],
                                           phone_number=content["phone_number"], photo=photo,
                                           plain_password=content["password"])
        except UserAlreadyRegisteredError:
            self.logger.debug(messages.USER_ALREADY_REGISTERED_MESSAGE % content["email"])
            return messages.ERROR_JSON % messages.USER_ALREADY_REGISTERED_MESSAGE % content["email"], 400
        except InvalidRegisterFieldError as e:
            self.logger.debug(str(e))
            return messages.ERROR_JSON % str(e), 400
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @cross_origin()
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
            self.logger.debug((messages.MISSING_FIELDS_ERROR % (LOGIN_MANDATORY_FIELDS - set(content.keys()))))
            return messages.ERROR_JSON % (
                        messages.MISSING_FIELDS_ERROR % (LOGIN_MANDATORY_FIELDS - set(content.keys()))), 400
        try:
            login_dict = self.auth_server.user_login(email=content["email"], plain_password=content["password"])
        except InvalidCredentialsError:
            self.logger.debug(messages.WRONG_CREDENTIALS_MESSAGE)
            return messages.ERROR_JSON % messages.WRONG_CREDENTIALS_MESSAGE, 403
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % content["email"])
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % content["email"]), 404

        if "notification_token" in content:
            self.notification_database.set_notification_token(content["email"], content["notification_token"])

        return json.dumps(login_dict), 200

    @register_api_call
    @cross_origin()
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
        return json.dumps(user_data), 200

    @register_api_call
    @cross_origin()
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
            self.logger.debug(
                (messages.MISSING_FIELDS_ERROR % (RECOVER_PASSWORD_MANDATORY_FIELDS - set(content.keys()))))
            return messages.ERROR_JSON % (
                        messages.MISSING_FIELDS_ERROR % (RECOVER_PASSWORD_MANDATORY_FIELDS - set(content.keys()))), 400
        try:
            self.auth_server.send_recovery_email(content["email"])
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % content["email"])
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % content["email"]), 404
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @cross_origin()
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
            self.logger.debug((messages.MISSING_FIELDS_ERROR % (NEW_PASSWORD_MANDATORY_FIELDS - set(content.keys()))))
            return messages.ERROR_JSON % (
                        messages.MISSING_FIELDS_ERROR % (NEW_PASSWORD_MANDATORY_FIELDS - set(content.keys()))), 400
        try:
            self.auth_server.recover_password(content["email"], content["token"], content["new_password"])
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % content["email"])
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % content["email"]), 404
        except InvalidRecoveryTokenError:
            self.logger.debug(messages.INVALID_RECOVERY_TOKEN_MESSAGE % content["email"])
            return messages.ERROR_JSON % (messages.INVALID_RECOVERY_TOKEN_MESSAGE % content["email"]), 400
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @cross_origin()
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
        token = auth.current_user()[1]
        content = request.form
        password = content["password"] if "password" in content else None
        fullname = content["fullname"] if "fullname" in content else None
        phone_number = content["phone_number"] if "phone_number" in content else None
        photo = Photo.from_bytes(request.files['photo'].stream) if 'photo' in request.files else None
        try:
            self.auth_server.profile_update(email=email_query, user_token=token,
                                            password=password, fullname=fullname,
                                            phone_number=phone_number, photo=photo)
        except UnauthorizedUserError:
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % email_query)
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % email_query), 404
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @cross_origin()
    @auth.login_required
    def users_delete(self):
        user_email = request.args.get('email')
        token = auth.current_user()[1]
        if not user_email:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % "email"))
            return messages.ERROR_JSON % "email", 400
        user_videos = self.video_database.list_user_videos(user_email)
        try:
            self.auth_server.user_delete(user_email, token)
        except UnauthorizedUserError:
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        except UnexistentUserError:
            self.logger.debug(messages.USER_NOT_FOUND_MESSAGE % user_email)
            return messages.ERROR_JSON % (messages.USER_NOT_FOUND_MESSAGE % user_email), 404
        for video_data,_ in user_videos:
            try:
                self.media_server.delete_video(user_email, video_data.title)
            except UnexistentVideoError:
                continue
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @auth.login_required
    def users_video_upload(self):
        """
        Uploads a video for a user
        :return: a json with the video data or an error in another case
        """
        email_token = auth.current_user()[0]
        content = request.form
        if not UPLOAD_VIDEO_MANDATORY_FIELDS.issubset(content.keys()) or not "video" in request.files:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % (UPLOAD_VIDEO_MANDATORY_FIELDS - set(content.keys()))))
            return messages.ERROR_JSON % (
                        messages.MISSING_FIELDS_ERROR % (UPLOAD_VIDEO_MANDATORY_FIELDS - set(content.keys()))), 400
        title = content["title"]
        location = content["location"]
        visible = True if content["visible"] == "true" else False
        video = request.files['video'].stream
        description = content["description"] if "description" in content else None
        try:
            file_location = self.media_server.upload_video(user_email=email_token,
                                                           title=title, video=video)
        except InvalidVideoFormatError:
            self.logger.debug(messages.INVALID_VIDEO_FORMAT)
            return messages.ERROR_JSON % messages.INVALID_VIDEO_FORMAT, 400
        video_data = VideoData(title=title, location=location, creation_time=datetime.now(),
                               file_location=file_location, visible=visible, description=description)
        self.video_database.add_video(user_email=email_token, video_data=video_data)
        response_dict = video_data._asdict()
        response_dict["creation_time"] = response_dict["creation_time"].isoformat()
        return json.dumps(response_dict), 200

    @register_api_call
    @cross_origin()
    @auth.login_required
    def users_video_delete(self):
        """
        Deletes a video from a user
        :return: a json with a success message on success or an error in another case
        """
        user_email = request.args.get('email')
        video_title = request.args.get('video_title')
        email_token = auth.current_user()[0]
        if not video_title or not user_email:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % "video_title or user_email"))
            return messages.ERROR_JSON % "video_title or user_email", 400
        if user_email != email_token and not self.auth_server.profile_query(email_token)["admin"]:
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        try:
            self.media_server.delete_video(user_email, video_title)
        except UnexistentVideoError:
            self.logger.debug((messages.UNEXISTENT_VIDEO_ERROR % (video_title, email_token)))
            return messages.UNEXISTENT_VIDEO_ERROR % (video_title, email_token), 404
        self.video_database.delete_video(user_email, video_title)
        return messages.SUCCESS_JSON, 200

    @register_api_call
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
        user_videos = [(video_data._asdict(), reaction_data) for video_data, reaction_data in user_videos]
        if email_query != email_token and not self.friend_database.are_friends(email_query, email_token):
            user_videos = [data for data in user_videos if data[0]["visible"]]
        for i in range(len(user_videos)):
            user_videos[i][0]["creation_time"] = user_videos[i][0]["creation_time"].isoformat()
            user_videos[i] = (user_videos[i][0], {k.name: v for k, v in user_videos[i][1].items()})
        user_videos = [{"video": video_data, "reactions": reaction_data} for video_data, reaction_data in user_videos]
        return json.dumps(user_videos), 200

    @register_api_call
    def list_top_videos(self):
        """
        List top videos
        :return: a json with the videos data or an error in another case
        """
        top_videos_data = self.video_database.list_top_videos()
        user_videos = [data[1]._asdict() for data in top_videos_data]
        user_emails = [data[0] for data in top_videos_data]
        user_reactions = [{k.name: v for k, v in data[2].items()} for data in top_videos_data]
        for i in range(len(user_videos)):
            user_videos[i]["creation_time"] = user_videos[i]["creation_time"].isoformat()
        return json.dumps([{"user": u, "video": v, "reactions": r}
                           for v, u, r in zip(user_videos, user_emails, user_reactions)]), 200

    @register_api_call
    @auth.login_required
    def search_videos(self):
        """
        Searches for a video
        :return: a json with the videos data or an error in another case
        """
        query = request.args.get('query')
        if not query:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % "query"))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % "query"), 400
        videos_data = self.video_database.search_videos(query)
        user_videos = [data[1]._asdict() for data in videos_data]
        user_emails = [data[0] for data in videos_data]
        user_reactions = [{k.name: v for k, v in data[2].items()} for data in videos_data]

        email_token = auth.current_user()[0]
        filtered_videos = []
        filtered_users = []
        filtered_reactions = []
        for v, u, r in zip(user_videos, user_emails, user_reactions):
            if v["visible"] or (u["email"] == email_token or self.friend_database.are_friends(u["email"], email_token)):
                filtered_videos.append(v)
                filtered_users.append(u)
                filtered_reactions.append(r)
        for i in range(len(user_videos)):
            filtered_videos[i]["creation_time"] = filtered_videos[i]["creation_time"].isoformat()
        return json.dumps([{"user": u, "video": v, "reactions": r}
                           for v, u, r in zip(filtered_videos, filtered_users, filtered_reactions)]), 200

    @register_api_call
    @cross_origin()
    @auth.login_required
    def list_videos(self):
        """
        List videos paginated
        :return: a json with the videos data and pages or an error in another case
        """
        page = request.args.get('page')
        per_page = request.args.get('per_page')
        if not page or not per_page:
            self.logger.debug((messages.MISSING_FIELDS_ERROR % "page or per_page"))
            return messages.ERROR_JSON % (messages.MISSING_FIELDS_ERROR % "page or per_page"), 400
        email_token = auth.current_user()[0]
        if not self.auth_server.profile_query(email_token)["admin"]:
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        try:
            videos_data, pages = self.video_database.get_paginated_videos(int(page), int(per_page))
        except NoMoreVideosError:
            self.logger.debug(messages.NO_MORE_PAGES_ERROR)
            return messages.NO_MORE_PAGES_ERROR, 404
        user_videos = [data[1]._asdict() for data in videos_data]
        user_data = [data[0] for data in videos_data]
        user_reactions = [{k.name: v for k, v in data[2].items()} for data in videos_data]

        for i in range(len(user_videos)):
            user_videos[i]["creation_time"] = user_videos[i]["creation_time"].isoformat()
        return json.dumps({"results":
                               [{"user": u, "video": v, "reactions": r}
                           for v, u, r in zip(user_videos, user_data, user_reactions)],
                           "pages": pages}), 200

    @register_api_call
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
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % (
                        FRIEND_REQUEST_MANDATORY_FIELDS - set(content.keys())), 400
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
        self.notification_database.notify(content["other_user_email"],
                                          "New friendship request", "From %s" % email_token,
                                          {"kind": "friendship_request",
                                           "from": email_token})
        return messages.SUCCESS_JSON, 200

    @register_api_call
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

    @register_api_call
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
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % (
                        FRIEND_REQUEST_MANDATORY_FIELDS - set(content.keys())), 400
        email_token = auth.current_user()[0]
        try:
            self.friend_database.accept_friend_request(content["other_user_email"], email_token)
        except UnexistentFriendRequest:
            self.logger.debug(messages.UNEXISTENT_FRIEND_REQUEST % (content["other_user_email"], email_token))
            return messages.ERROR_JSON % (messages.UNEXISTENT_FRIEND_REQUEST %
                                          (content["other_user_email"], email_token)), 404
        return messages.SUCCESS_JSON, 200

    @register_api_call
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
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % (
                        FRIEND_REQUEST_MANDATORY_FIELDS - set(content.keys())), 400
        email_token = auth.current_user()[0]
        try:
            self.friend_database.reject_friend_request(content["other_user_email"], email_token)
        except UnexistentFriendRequest:
            self.logger.debug(messages.UNEXISTENT_FRIEND_REQUEST % (content["other_user_email"], email_token))
            return messages.ERROR_JSON % (messages.UNEXISTENT_FRIEND_REQUEST %
                                          (content["other_user_email"], email_token)), 404
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @auth.login_required
    def user_list_friends(self):
        """
        List friends of an user
        :return: a json with the friends on success or an error in another case
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

    @register_api_call
    @auth.login_required
    def delete_friendship(self):
        """
        Delete a friendship
        :return: a json on success or an error in another case
        """
        other_user_email = request.args.get('other_user_email')
        if not other_user_email:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "other_user_email")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "other_user_email", 400
        email_token = auth.current_user()[0]
        self.friend_database.delete_friendship(email_token, other_user_email)
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @auth.login_required
    def friendship_status_with(self):
        """
        Get a friendship status
        :return: a json on success or an error in another case
        {'are_friends': bool, 'received_friend_request': bool,
        'sent_friend_request': bool}
        """
        email_query = request.args.get('other')
        if not email_query:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "other")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "other", 400
        email_token = auth.current_user()[0]
        response = "no_contact"
        if self.friend_database.are_friends(email_token, email_query):
            response = "friends"
        elif self.friend_database.exists_friend_request(email_query, email_token):
            response = "received"
        elif self.friend_database.exists_friend_request(email_token, email_query):
            response = "sent"
        return json.dumps({"status": response}), 200

    @register_api_call
    @auth.login_required
    def video_reaction_get(self):
        """
        Gets the reaction of a user on a video
        :return: a json containing the reaction or an error in other case
        """
        target_email = request.args.get('target_email')
        video_title = request.args.get('video_title')
        if not target_email or not video_title:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "Query params")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "Query params", 400
        email_token = auth.current_user()[0]
        reaction = self.video_database.get_video_reaction(email_token, target_email, video_title)
        if reaction:
            reaction = reaction.name
        return json.dumps({"reaction": reaction}), 200

    @register_api_call
    @auth.login_required
    def video_reaction(self):
        """
        Reacts a video
        :return: a json with a success message on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not VIDEO_REACTION_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug(messages.MISSING_FIELDS_ERROR % (VIDEO_REACTION_MANDATORY_FIELDS - set(content.keys())))
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % (
                        VIDEO_REACTION_MANDATORY_FIELDS - set(content.keys())), 400
        email_token = auth.current_user()[0]
        reaction = [react for react in Reaction if react.name == content["reaction"]]
        if len(reaction) != 1:
            self.logger.debug(messages.UNEXISTENT_REACTION % content["reaction"])
            return messages.ERROR_JSON % messages.UNEXISTENT_REACTION % content["reaction"], 400
        self.video_database.react_video(email_token, content["target_email"],
                                        content["video_title"], reaction[0])
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @auth.login_required
    def video_reaction_delete(self):
        """
        Deletes a reaction
        :return: a json with a success message on success or an error in another case
        """
        target_email = request.args.get('target_email')
        video_title = request.args.get('video_title')
        if not target_email or not video_title:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "target_email or video_title")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "target_email or video_title", 400
        email_token = auth.current_user()[0]
        self.video_database.delete_reaction(email_token, target_email, video_title)
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @auth.login_required
    def send_message(self):
        """
        Sends a private message
        :return: a json with a success message on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not SEND_MESSAGE_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug(
                messages.MISSING_FIELDS_ERROR % (SEND_MESSAGE_MANDATORY_FIELDS - set(content.keys())))
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % (
                        SEND_MESSAGE_MANDATORY_FIELDS - set(content.keys())), 400
        email_token = auth.current_user()[0]
        try:
            self.friend_database.send_message(email_token, content["other_user_email"],
                                              content["message"])
        except UsersAreNotFriendsError:
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        self.notification_database.notify(content["other_user_email"],
                                          "Message from %s" % email_token,
                                          "%s" % content["message"],
                                          {"kind": "message",
                                           "from": email_token,
                                           "message": content["message"]})
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @auth.login_required
    def get_messages(self):
        """
        Get the messages between two users paginated
        :return: a json with the messages on success or an error in another case
        """
        other_user_email = request.args.get('other_user_email')
        page = request.args.get('page')
        per_page = request.args.get('per_page')
        if not other_user_email or not page or not per_page:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "query params")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "query params", 400
        email_token = auth.current_user()[0]
        page = int(page)
        per_page = int(per_page)
        # App sends starting with 1 but we start at 0
        page -= 1
        try:
            message_list, pages = self.friend_database.get_conversation(email_token, other_user_email, per_page, page)
        except NoMoreMessagesError:
            self.logger.debug(messages.NO_MORE_PAGES_ERROR)
            return messages.NO_MORE_PAGES_ERROR, 404
        message_list = [{k:v for k,v in m._asdict().items() if k != "hidden_to"} for m in message_list]
        for i in range(len(message_list)):
            message_list[i]["timestamp"] = message_list[i]["timestamp"].isoformat()
        return json.dumps({"messages": message_list, "pages": pages}), 200

    @register_api_call
    @auth.login_required
    def delete_messages(self):
        """
        One user deletes its messages with other one
        :return: a json with the messages on success or an error in another case
        """
        other_user_email = request.args.get('other_user_email')
        if not other_user_email:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "other_user_email")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "other_user_email", 400
        email_token = auth.current_user()[0]
        self.friend_database.delete_conversation(email_token, other_user_email)
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @auth.login_required
    def get_last_conversations(self):
        """
        Get the last conversations
        :return: a json with the last conversations [{"user_email": email, "last_message": last message}] on success
        or an error in another case
        """
        email_token = auth.current_user()[0]
        user_data, last_messages = self.friend_database.get_conversations(email_token)
        last_messages = [{k:v for k,v in m._asdict().items() if k != "hidden_to"} for m in last_messages]
        for i in range(len(last_messages)):
            last_messages[i]["timestamp"] = last_messages[i]["timestamp"].isoformat()
        response = []
        for i in range(len(last_messages)):
            response.append({"user": user_data[i], "last_message": last_messages[i]})
        return json.dumps(response), 200

    @register_api_call
    @auth.login_required
    def comment_video(self):
        """
        Comment a video
        :return: a json with a success message on success or an error in another case
        """
        try:
            assert request.is_json
        except AssertionError:
            self.logger.debug(messages.REQUEST_IS_NOT_JSON)
            return messages.ERROR_JSON % messages.REQUEST_IS_NOT_JSON, 400
        content = request.get_json()
        if not VIDEO_COMMENT_MANDATORY_FIELDS.issubset(content.keys()):
            self.logger.debug(messages.MISSING_FIELDS_ERROR % (VIDEO_COMMENT_MANDATORY_FIELDS - set(content.keys())))
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % (
                        VIDEO_REACTION_MANDATORY_FIELDS - set(content.keys())), 400
        email_token = auth.current_user()[0]
        self.video_database.comment_video(email_token, content["target_email"],
                                          content["video_title"], content["comment"])
        return messages.SUCCESS_JSON, 200

    @register_api_call
    @auth.login_required
    def get_video_comments(self):
        """
        Get the comments for one video
        :return: a json with [{user data, comment}] or an error in other case
        """
        other_user_email = request.args.get('other_user_email')
        video_title = request.args.get('video_title')
        if not other_user_email or not video_title:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "query params")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "query params", 400
        users_data, comments = self.video_database.get_comments(other_user_email, video_title)
        response = [{"user": u,
                     "comment": {"content":c.content, "timestamp": c.timestamp.isoformat()}}
                    for u,c in zip(users_data, comments)]
        return json.dumps(response), 200

    @register_api_call
    @cross_origin()
    @auth.login_required
    def registered_users(self):
        """
        Handles the return of all registered users
        return: a json with a list of dictionaries with the registered users data
                for the required page with a fixed users_per_page value
        """
        try:
            users_per_page = int(request.args.get('users_per_page'))
            page = int(request.args.get('page'))
        except TypeError:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "page or users_per_page")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "page or users_per_page", 400
        token = auth.current_user()[1]
        try:
            data_page = self.auth_server.get_registered_users(page, users_per_page, token)
        except UnauthorizedUserError:
            self.logger.debug(messages.USER_NOT_AUTHORIZED_ERROR)
            return messages.ERROR_JSON % messages.USER_NOT_AUTHORIZED_ERROR, 403
        except NoMorePagesError:
            self.logger.debug(messages.NO_MORE_PAGES_ERROR)
            return messages.NO_MORE_PAGES_ERROR, 404
        return json.dumps(data_page), 200


    @cross_origin()
    def api_call_statistics(self):
        """
        Computes api call statistics and returns it

        :return: a json with statistics
        """
        try:
            days = int(request.args.get('days'))
        except TypeError:
            self.logger.debug(messages.MISSING_FIELDS_ERROR % "days")
            return messages.ERROR_JSON % messages.MISSING_FIELDS_ERROR % "days", 400
        api_call_statistics = self.statistic_database.compute_statistics(days)
        last_days_uploaded_videos = {k.isoformat(): v for k, v in api_call_statistics.last_days_uploaded_videos.items()}
        last_days_user_registrations = {k.isoformat(): v for k, v in api_call_statistics.last_days_user_registrations.items()}
        last_days_users_logins = {k.isoformat(): v for k, v in api_call_statistics.last_days_users_logins.items()}
        last_days_api_call_amount = {k.isoformat(): v for k, v in api_call_statistics.last_days_api_call_amount.items()}
        last_day_mean_api_call_time = {k.isoformat(): v for k, v in api_call_statistics.last_day_mean_api_call_time.items()}
        return json.dumps({"last_days_uploaded_videos": last_days_uploaded_videos,
                           "last_days_user_registrations": last_days_user_registrations,
                           "last_days_users_logins": last_days_users_logins,
                           "last_days_api_call_amount": last_days_api_call_amount,
                           "last_day_mean_api_call_time": last_day_mean_api_call_time,
                           "last_days_api_calls_by_path": api_call_statistics.last_days_api_calls_by_path,
                           "last_days_api_calls_by_status": api_call_statistics.last_days_api_calls_by_status,
                           "last_days_api_calls_response_times_sample": api_call_statistics.last_days_api_calls_response_times_sample,
                           "last_days_api_calls_by_method": api_call_statistics.last_days_api_calls_by_method
                           })

    @cross_origin()
    def app_server_statuses(self):
        """
        Gets app server statuses
        :return: a json with app server statuses
        """
        statuses = self.auth_server.get_app_servers_statuses()
        for i in range(len(statuses)):
            try:
                statuses[i]["metrics"] = self.statistic_database.technical_metrics_from_server(statuses[i]["server_alias"])._asdict()
            except Exception:
                continue
        return json.dumps(statuses)

    @auth.login_required
    def login_get(self):
        """
        Get the user behind a login token

        :return: the user behind the login token or 401
        """
        return json.dumps({"user_email": auth.current_user()[0]}), 200





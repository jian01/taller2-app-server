from flask import Flask, send_from_directory
from src.controller import Controller
from logging.config import fileConfig
from config.load_config import load_config
from typing import Optional
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS


fileConfig('config/logging_conf.ini')

DEFAULT_CONFIG_FILE = "config/default_conf.yml"
SWAGGER_URL = "/swagger"
API_URL = "/static/swagger.yaml"


def create_application(config_path: Optional[str] = None, return_controller: Optional[bool] = False):
    """
    Creates the flask application

    :param config_path: the path to the configuration
    :param return_controller: if the controller should also be returned as a second value (for testing purposes)
    :return: a Flask app
    """
    if not config_path:
        config_path = DEFAULT_CONFIG_FILE
    config = load_config(config_path)
    controller = Controller(config.auth_server,config.media_server,
                            config.video_database,config.friend_database)
    if not return_controller:
        return create_application_with_controller(controller)
    else:
        return create_application_with_controller(controller), controller

def create_application_with_controller(controller: Controller):
    app = Flask(__name__)

    swaggerui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL,
                                                  config= {"app_name": "Chotuve Auth Server"})

    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

    app.add_url_rule('/health', 'api_health', controller.api_health)
    app.add_url_rule('/user', 'users_register', controller.users_register,
                     methods=["POST"])
    app.add_url_rule('/user/login', 'users_login', controller.users_login,
                     methods=["POST"])
    app.add_url_rule('/user', 'users_profile_query',
                     controller.users_profile_query, methods=['GET'])
    app.add_url_rule('/user', 'users_profile_update',
                     controller.users_profile_update, methods=['PUT'])
    app.add_url_rule('/user/recover_password', 'users_recover_password',
                     controller.users_send_recovery_email, methods=["POST"])
    app.add_url_rule('/user/new_password', 'users_new_password',
                     controller.users_recover_password, methods=["POST"])

    app.add_url_rule('/user/video', 'users_upload_video',
                     controller.users_video_upload, methods=["POST"])
    app.add_url_rule('/user/videos', 'users_list_videos',
                     controller.users_list_videos, methods=["GET"])
    app.add_url_rule('/videos/top', 'list_top_videos',
                     controller.list_top_videos, methods=["GET"])
    app.add_url_rule('/videos/search', 'search_videos',
                     controller.search_videos, methods=["GET"])
    app.add_url_rule('/videos/reaction', 'video_reaction',
                     controller.video_reaction, methods=["POST"])
    app.add_url_rule('/videos/reaction', 'video_reaction_delete',
                     controller.video_reaction_delete, methods=["DELETE"])
    app.add_url_rule('/videos/comment', 'comment_video',
                     controller.comment_video, methods=["POST"])
    app.add_url_rule('/videos/comments', 'get_video_comments',
                     controller.get_video_comments, methods=["GET"])


    app.add_url_rule('/user/friend_request', 'user_send_friend_request',
                     controller.user_send_friend_request, methods=["POST"])
    app.add_url_rule('/user/friend_request/accept', 'user_accept_friend_request',
                     controller.user_accept_friend_request, methods=["POST"])
    app.add_url_rule('/user/friend_request/reject', 'user_reject_friend_request',
                     controller.user_reject_friend_request, methods=["POST"])
    app.add_url_rule('/user/friend_requests', 'user_list_friend_requests',
                     controller.user_list_friend_requests, methods=["GET"])
    app.add_url_rule('/user/friends', 'user_list_friends',
                     controller.user_list_friends, methods=["GET"])
    app.add_url_rule('/user/friendship_status_with', 'friendship_status_with',
                     controller.friendship_status_with, methods=["GET"])

    app.add_url_rule('/user/message', 'user_send_message',
                     controller.send_message, methods=["POST"])
    app.add_url_rule('/user/messages_with', 'user_list_messages',
                     controller.get_messages, methods=["GET"])
    app.add_url_rule('/user/last_conversations', 'last_conversations',
                     controller.get_last_conversations, methods=["GET"])

    return app
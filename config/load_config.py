from typing import NamedTuple
from yaml import load
from yaml import Loader
from src.services.auth_server import AuthServer
from src.services.media_server import MediaServer
from src.database.videos.video_database import VideoDatabase

class AppServerConfig(NamedTuple):
    auth_server: AuthServer
    media_server: MediaServer
    video_database: VideoDatabase

def load_config(config_path: str) -> AppServerConfig:
    """
    Loads the config for the server

    :param config_path: the path where to load the config
    :return: nothing
    """
    with open(config_path, "r") as yaml_file:
        config_dict = load(yaml_file, Loader=Loader)

    auth_server = AuthServer(**config_dict["auth_server"])
    media_server = MediaServer(**config_dict["media_server"])

    video_database = VideoDatabase.factory(config_dict["video_database"],
                                           **config_dict["video_databases"][config_dict["video_database"]])

    return AppServerConfig(auth_server=auth_server, media_server=media_server,
                           video_database=video_database)


from typing import NamedTuple
from yaml import load
from yaml import Loader
from src.services.auth_server import AuthServer

class AppServerConfig(NamedTuple):
    auth_server: AuthServer

def load_config(config_path: str) -> AppServerConfig:
    """
    Loads the config for the server

    :param config_path: the path where to load the config
    :return: nothing
    """
    with open(config_path, "r") as yaml_file:
        config_dict = load(yaml_file, Loader=Loader)

    auth_server = AuthServer(**config_dict["auth_server"])

    return AppServerConfig(auth_server=auth_server)


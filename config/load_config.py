from typing import NamedTuple
from yaml import load
from yaml import Loader


def load_config(config_path: str):
    """
    Loads the config for the server

    :param config_path: the path where to load the config
    :return: nothing
    """

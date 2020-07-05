from typing import NoReturn, List, Optional, NamedTuple, Tuple, Dict
from abc import abstractmethod
from datetime import datetime
from enum import Enum


class Reaction(Enum):
    """
    Reaction type enum
    """
    like = 1
    dislike = 2

class VideoData(NamedTuple):
    """
    A video data container

    title: the title of the video
    location: the location of the video
    creation_time: the creation time
    file_location: the location of the file
    visible: if its visible or not
    description: the description of the video
    """
    title: str
    location: str
    creation_time: datetime
    file_location: str
    visible: bool
    description: Optional[str] = None

class VideoDatabase:
    """
    Video database abstraction
    """

    @abstractmethod
    def add_video(self, user_email: str, video_data: VideoData) -> NoReturn:
        """
        Adds a video to the database

        :param user_email: the email of the user owner of the video
        :param video_data: the video data to upload
        """

    @abstractmethod
    def list_user_videos(self, user_email: str) -> List[Tuple[VideoData, Dict[Reaction, int]]]:
        """
        Get all the user videos

        :param user_email: the user's email
        :return: a list (video data, reactions counts)
        """

    @abstractmethod
    def list_top_videos(self) -> List[Tuple[Dict, VideoData, Dict[Reaction, int]]]:
        """
        Get top videos

        :return: a list of (user data, video data, reactions counts)
        """

    @abstractmethod
    def search_videos(self, search_query: str) -> List[Tuple[Dict, VideoData, Dict[Reaction, int]]]:
        """
        Searches videos with a query

        :param search_query: the query to search
        :return: a list of (user data, video data, reactions counts)
        """

    @abstractmethod
    def react_video(self, actor_email: str, target_email: str,
                   video_title: str, reaction: Reaction) -> NoReturn:
        """
        Likes a video

        :param actor_email: the liker of the video
        :param target_email: the email of the owner of the video
        :param video_title: the title of the video
        :param reaction: the type of reaction
        """

    @abstractmethod
    def delete_reaction(self, actor_email: str, target_email: str,
                        video_title: str) -> NoReturn:
        """
        Deletes video reaction

        :param actor_email: the liker of the video
        :param target_email: the email of the owner of the video
        :param video_title: the title of the video
        """

    @classmethod
    def factory(cls, name: str, *args, **kwargs) -> 'VideoDatabase':
        """
        Factory pattern for database

        :param name: the name of the database to create in the factory
        :return: a database object
        """
        database_types = {cls.__name__:cls for cls in VideoDatabase.__subclasses__()}
        return database_types[name](*args, **kwargs)

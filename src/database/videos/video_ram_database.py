from typing import NoReturn, List, Optional, NamedTuple, Tuple, Dict
from abc import abstractmethod
from datetime import datetime
from src.database.videos.video_database import VideoData, VideoDatabase

class RamVideoDatabase(VideoDatabase):
    """
    Video ram database
    """
    videos_by_user: Dict[str, List[Tuple[int, VideoData]]]
    current_id: int

    def __init__(self):
        self.videos_by_user = {}
        self.current_id = 0

    def add_video(self, user_email: str, video_data: VideoData) -> int:
        """
        Adds a video to the database

        :param user_email: the email of the user owner of the video
        :param video_data: the video data to upload
        :return: a video unique id
        """
        if user_email not in self.videos_by_user:
            self.videos_by_user[user_email] = [(self.current_id, video_data)]
        else:
            self.videos_by_user[user_email].append((self.current_id, video_data))
        return self.current_id - 1

    def list_user_videos(self, user_email: str) -> List[Tuple[int, VideoData]]:
        """
        Get all the user videos

        :param user_email: the user's email
        :return: a list of tuples containing the id of the video and its data
        """
        return self.videos_by_user[user_email]
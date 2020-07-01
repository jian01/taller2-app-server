from typing import NoReturn, List, Optional, NamedTuple, Tuple, Dict
from abc import abstractmethod
from datetime import datetime
from src.database.videos.video_database import VideoData, VideoDatabase

class RamVideoDatabase(VideoDatabase):
    """
    Video ram database
    """
    videos_by_user: Dict[str, List[VideoData]]
    current_id: int

    def __init__(self):
        self.videos_by_user = {}

    def add_video(self, user_email: str, video_data: VideoData) -> NoReturn:
        """
        Adds a video to the database

        :param user_email: the email of the user owner of the video
        :param video_data: the video data to upload
        """
        if user_email not in self.videos_by_user:
            self.videos_by_user[user_email] = [video_data]
        else:
            self.videos_by_user[user_email].append(video_data)

    def list_user_videos(self, user_email: str) -> List[VideoData]:
        """
        Get all the user videos

        :param user_email: the user's email
        :return: a list video data
        """
        return list(reversed(self.videos_by_user[user_email]))

    def list_top_videos(self):
        """
        Get top videos

        :return: a list of (user data, video data)
        """
        result = []
        for k, v in self.videos_by_user.items():
            for i in range(len(v)):
                if v[i].visible:
                    result.append(({"email": k},v[i]))
        return result
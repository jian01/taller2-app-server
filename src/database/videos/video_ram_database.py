from typing import NoReturn, List, Optional, NamedTuple, Tuple, Dict
from abc import abstractmethod
from datetime import datetime
from src.database.videos.video_database import VideoData, VideoDatabase
from nltk import word_tokenize


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
                    result.append(({"email": k}, v[i]))
        return result

    def search_videos(self, search_query: str):
        """
        Searches videos with a query

        :param search_query: the query to search
        :return: a list of (user data, video data)
        """
        tokenized_query = word_tokenize(search_query.lower())
        bigrams_query = [tokenized_query[i:i + 2] for i in range(len(tokenized_query) - 2 + 1)]
        result = []
        for k, v in self.videos_by_user.items():
            for i in range(len(v)):
                if v[i].visible:
                    word_count = 0
                    desc_count = 0
                    tokenized_title = word_tokenize(v[i].title.lower())
                    bigrams_title = [tokenized_title[i:i + 2] for i in range(len(tokenized_title) - 2 + 1)]
                    tokenized_desc = (word_tokenize(v[i].description[:1000].lower()) if v[i].description else [])
                    for w in tokenized_query:
                        word_count += len([t for t in tokenized_title if t == w])
                        desc_count += len([t for t in tokenized_desc if t == w])
                    for b in bigrams_query:
                        word_count += len([t for t in bigrams_title if t == b])
                    if word_count > 0 or desc_count > 0:
                        result.append(({"email": k}, v[i], word_count * 0.8 + desc_count * 0.2))
        result = sorted(result, key=lambda x:x[2],reverse=True)
        result = [(r[0],r[1]) for r in result]
        return result

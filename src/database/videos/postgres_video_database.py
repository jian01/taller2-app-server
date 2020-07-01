import psycopg2
from typing import NoReturn, List, Optional, NamedTuple, Tuple, Dict
from src.database.videos.video_database import VideoData, VideoDatabase
import logging
import os
import json
import requests
import math
import datetime

VIDEO_INSERT_QUERY = """
INSERT INTO {} (user_email, title, creation_time, visible, location, file_location, description)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

LIST_USER_VIDEOS_QUERY = """
SELECT title, creation_time, visible, location, file_location, description
FROM %s
WHERE user_email = '%s'
ORDER BY creation_time DESC
"""

TOP_VIDEO_QUERY = """
SELECT user_email, u.fullname, u.phone_number, u.photo, title, creation_time, visible, location, file_location, description
FROM (
SELECT user_email, title, creation_time, visible, location, file_location, description
FROM %s
WHERE visible = true
ORDER BY RANDOM()
LIMIT 10) as v
INNER JOIN %s as u
ON u.email = v.user_email
"""

class PostgresVideoDatabase(VideoDatabase):
    """
    Postgres & Firebase implementation of Database abstraction
    """
    logger = logging.getLogger(__name__)
    # TODO: avoid sql injection
    def __init__(self, videos_table_name: str, users_table_name: str,
                 postgr_host_env_name: str, postgr_user_env_name: str,
                 postgr_pass_env_name: str, postgr_database_env_name: str):

        self.videos_table_name = videos_table_name
        self.users_table_name = users_table_name
        self.conn = psycopg2.connect(host=os.environ[postgr_host_env_name], user=os.environ[postgr_user_env_name],
                                     password=os.environ[postgr_pass_env_name],
                                     database=os.environ[postgr_database_env_name])
        if self.conn.closed == 0:
            self.logger.info("Connected to postgres database")
        else:
            self.logger.error("Unable to connect to postgres database")
            raise ConnectionError("Unable to connect to postgres database")

    def add_video(self, user_email: str, video_data: VideoData) -> NoReturn:
        """
        Adds a video to the database

        :param user_email: the email of the user owner of the video
        :param video_data: the video data to upload
        """
        cursor = self.conn.cursor()
        self.logger.debug("Saving video for user with email %s" % user_email)

        cursor.execute(VIDEO_INSERT_QUERY.format(self.videos_table_name),
                       (user_email, video_data.title, video_data.creation_time.isoformat(),
                        video_data.visible, video_data.location, video_data.file_location,
                        video_data.description))
        self.conn.commit()
        cursor.close()

    def list_user_videos(self, user_email: str) -> List[VideoData]:
        """
        Get all the user videos

        :param user_email: the user's email
        :return: a list video data
        """
        self.logger.debug("Listing videos for user with email %s" % user_email)
        cursor = self.conn.cursor()
        cursor.execute(LIST_USER_VIDEOS_QUERY % (self.videos_table_name, user_email))
        result = cursor.fetchall()
        # title, creation_time, visible, location, file_location, description
        result = [VideoData(title=r[0], creation_time=r[1], visible=r[2], location=r[3],
                            file_location=r[4], description=r[5])
                  for r in result]
        cursor.close()

        return result

    def list_top_videos(self):
        """
        Get top videos

        :return: a list of (user data, video data)
        """
        self.logger.debug("Listing top videos")
        cursor = self.conn.cursor()
        cursor.execute(TOP_VIDEO_QUERY % (self.videos_table_name,
                                          self.users_table_name))
        result = cursor.fetchall()
        # user_email, fullname, phone_number, photo, title, creation_time, visible, location, file_location, description
        result_videos = [VideoData(title=r[4], creation_time=r[5], visible=r[6], location=r[7],
                                   file_location=r[8], description=r[9])
                         for r in result]
        result_emails = [{"email": r[0], "fullname": r[1], "phone_number":r[2],
                          "photo": r[3]} for r in result]
        cursor.close()

        return list(zip(result_emails, result_videos))
from typing import NoReturn
from io import BytesIO
import os
import requests
from src.services.exceptions.invalid_video_format_error import InvalidVideoFormatError
from src.services.exceptions.unexistent_video_error import UnexistentVideoError
import logging

VIDEO_UPLOAD_TIMEOUT = 100
DEFAULT_TIMEOUT = 15

VIDEOS_ENDPOINT = "/videos"

class MediaServer:
    """
    The media server object
    """
    media_url: str

    logger = logging.getLogger(__module__)
    def __init__(self, media_server_url_env_name: str):
        """

        :param media_server_url_env_name: the env name containing the media server url
        """
        self.media_url = os.getenv(media_server_url_env_name)
        # TODO: health-check
        self.logger.info("Connected to media server")

    def upload_video(self, user_email: str, title: str, video: BytesIO) -> str:
        """
        Uploads a video for a user

        :raises:
            InvalidVideoFormatError: the video file has an invalid format

        :param user_email: the user for which the video is being uploaded
        :param title: the title of the video to upload
        :param video: the video to upload
        :return: the file url
        """
        self.logger.debug("Uploading video for %s" % user_email)
        r = requests.post(self.media_url + VIDEOS_ENDPOINT,
                          data={"email": user_email, "title": title},
                          files={"file": ("video.mp4", video)},
                          timeout=VIDEO_UPLOAD_TIMEOUT)
        if r.status_code == 400:
            raise InvalidVideoFormatError
        r.raise_for_status()
        return r.json()["url"]

    def delete_video(self, user_email: str, title: str) -> NoReturn:
        """
        Deletes a video

        :raises:
            UnexistentVideoError: the video to delete does not exist

        :param user_email: the email of the owner of the video
        :param title: the title of the video to delete
        """
        self.logger.debug("Deleting video for %s" % user_email)
        r = requests.delete(self.media_url + VIDEOS_ENDPOINT,
                            params={"email": user_email, "title": title})
        if r.status_code == 404:
            raise UnexistentVideoError
        r.raise_for_status()

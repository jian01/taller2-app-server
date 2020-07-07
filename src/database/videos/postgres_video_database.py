import psycopg2
from typing import NoReturn, List, Optional, NamedTuple, Tuple, Dict
from src.database.videos.video_database import VideoData, VideoDatabase, Reaction, Comment
import logging
import os
from datetime import datetime
from nltk import word_tokenize

VIDEO_WITH_LIKES_QUERY = '''
SELECT user_email, title, creation_time, visible, location, file_location, description, COALESCE(vr_likes.count, 0) as like_count, COALESCE(vr_dislikes.count, 0) as dislike_count
FROM {videos_table_name} as v
LEFT JOIN
(SELECT target_email, video_title, COUNT(*) as count
FROM {video_reactions_table_name}
WHERE reaction_type = 1
GROUP BY 1,2
) as vr_likes
ON v.title = vr_likes.video_title AND v.user_email = vr_likes.target_email
LEFT JOIN
(SELECT target_email, video_title, COUNT(*) as count
FROM {video_reactions_table_name}
WHERE reaction_type = 2
GROUP BY 1,2
) as vr_dislikes
ON v.title = vr_dislikes.video_title AND v.user_email = vr_dislikes.target_email
'''

VIDEO_INSERT_QUERY = """
INSERT INTO {videos_table_names} (user_email, title, creation_time, visible, location, file_location, description)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (user_email, title) DO UPDATE 
  SET creation_time = excluded.creation_time,
      visible = excluded.visible,
      location = excluded.location,
      file_location = excluded.file_location,
      description = excluded.description;
"""

LIST_USER_VIDEOS_QUERY = """
SELECT title, creation_time, visible, location, file_location, description, like_count, dislike_count
FROM (
{video_with_likes}
) AS video_with_likes
WHERE user_email = '%s'
ORDER BY creation_time DESC
"""

TOP_VIDEO_QUERY = """
SELECT user_email, u.fullname, u.phone_number, u.photo, title, creation_time, visible, location, file_location, description, like_count, dislike_count
FROM (
SELECT user_email, title, creation_time, visible, location, file_location, description, like_count, dislike_count
FROM (
{video_with_likes}
) AS video_with_likes
WHERE visible = true
ORDER BY RANDOM()
LIMIT 10) as v
INNER JOIN {users_table_name} as u
ON u.email = v.user_email
"""

BASE_SEARCH_QUERY = """
SELECT user_email, u.fullname, u.phone_number, u.photo, title, creation_time, visible, location, file_location, description, like_count, dislike_count
FROM (
SELECT * FROM (
{video_with_likes}
) AS video_with_likes
WHERE (%s) AND visible = true
ORDER BY RANDOM()
LIMIT 100) as v
INNER JOIN {users_table_name} as u
ON u.email = v.user_email
"""

REACTION_INSERT_QUERY = """
INSERT INTO {video_reactions_table_name} (reactor_email, target_email, video_title, reaction_type)
VALUES (%s, %s, %s, %s)
ON CONFLICT (reactor_email, target_email, video_title) DO UPDATE 
  SET reaction_type = excluded.reaction_type;
"""

DELETE_REACTION_QUERY = """
DELETE FROM {video_reactions_table_name}
WHERE reactor_email=%s AND target_email=%s AND video_title=%s;
"""

COMMENT_VIDEO_QUERY = """
INSERT INTO {video_comments_table_name} (author_email, video_owner_email, video_title, comment, datetime)
VALUES (%s, %s, %s, %s, %s)
"""

GET_COMMENTS_QUERY = """
SELECT u.email, u.fullname, u.phone_number, u.photo, vc.comment, vc.datetime
FROM {video_comments_table_name} vc
INNER JOIN {users_table_name} as u
ON u.email = vc.author_email
WHERE vc.video_owner_email = %s AND vc.video_title = %s
"""

LIKE_SEARCH_TITLE_ELEMENT = "LOWER(title) LIKE '%{}%'"
LIKE_SEARCH_DESCRIPTION_ELEMENT = "LOWER(description) LIKE '%{}%'"


class PostgresVideoDatabase(VideoDatabase):
    """
    Postgres & Firebase implementation of Database abstraction
    """
    logger = logging.getLogger(__name__)

    # TODO: avoid sql injection
    def __init__(self, videos_table_name: str, users_table_name: str,
                 video_reactions_table_name: str, video_comments_table_name: str,
                 postgr_host_env_name: str, postgr_user_env_name: str,
                 postgr_pass_env_name: str, postgr_database_env_name: str):

        self.videos_table_name = videos_table_name
        self.users_table_name = users_table_name
        self.video_reactions_table_name = video_reactions_table_name
        self.video_comments_table_name = video_comments_table_name
        self.conn = psycopg2.connect(host=os.environ[postgr_host_env_name], user=os.environ[postgr_user_env_name],
                                     password=os.environ[postgr_pass_env_name],
                                     database=os.environ[postgr_database_env_name])
        if self.conn.closed == 0:
            self.logger.info("Connected to postgres database")
        else:
            self.logger.error("Unable to connect to postgres database")
            raise ConnectionError("Unable to connect to postgres database")

    @staticmethod
    def safe_query_run(connection, cursor, query: str, params: Optional[Tuple] = None):
        try:
            cursor.execute(query, params)
        except Exception as err:
            connection.rollback()
            raise err

    def add_video(self, user_email: str, video_data: VideoData) -> NoReturn:
        """
        Adds a video to the database

        :param user_email: the email of the user owner of the video
        :param video_data: the video data to upload
        """
        cursor = self.conn.cursor()
        self.logger.debug("Saving video for user with email %s" % user_email)
        self.safe_query_run(self.conn, cursor,
                            VIDEO_INSERT_QUERY.format(videos_table_names=self.videos_table_name),
                            (user_email, video_data.title, video_data.creation_time.isoformat(),
                             video_data.visible, video_data.location, video_data.file_location,
                             video_data.description))
        self.conn.commit()
        cursor.close()

    def list_user_videos(self, user_email: str) -> List[Tuple[VideoData, Dict[Reaction, int]]]:
        """
        Get all the user videos

        :param user_email: the user's email
        :return: a list (video data, reactions counts)
        """
        self.logger.debug("Listing videos for user with email %s" % user_email)
        cursor = self.conn.cursor()
        self.safe_query_run(self.conn, cursor,
                            LIST_USER_VIDEOS_QUERY.format(video_with_likes=
                                                          VIDEO_WITH_LIKES_QUERY.format(
                                                              videos_table_name=self.videos_table_name,
                                                              video_reactions_table_name=self.video_reactions_table_name))
                            % user_email)
        result = cursor.fetchall()
        # title, creation_time, visible, location, file_location, description, likes, dislikes
        result = [(VideoData(title=r[0], creation_time=r[1], visible=r[2], location=r[3],
                             file_location=r[4], description=r[5]),
                   {Reaction.like: r[6], Reaction.dislike: r[7]})
                  for r in result]
        cursor.close()

        return result

    def list_top_videos(self) -> List[Tuple[Dict, VideoData, Dict[Reaction, int]]]:
        """
        Get top videos

        :return: a list of (user data, video data, reactions counts)
        """
        self.logger.debug("Listing top videos")
        cursor = self.conn.cursor()

        self.safe_query_run(self.conn, cursor,
                            TOP_VIDEO_QUERY.format(video_with_likes=
                                                   VIDEO_WITH_LIKES_QUERY.format(
                                                       videos_table_name=self.videos_table_name,
                                                       video_reactions_table_name=self.video_reactions_table_name),
                                                   users_table_name=self.users_table_name))
        result = cursor.fetchall()
        # user_email, fullname, phone_number, photo, title, creation_time, visible, location, file_location, description, likes, dislikes
        result_videos = [VideoData(title=r[4], creation_time=r[5], visible=r[6], location=r[7],
                                   file_location=r[8], description=r[9])
                         for r in result]
        result_emails = [{"email": r[0], "fullname": r[1], "phone_number": r[2],
                          "photo": r[3]} for r in result]
        result_reactions = [{Reaction.like: r[10], Reaction.dislike: r[11]} for r in result]
        cursor.close()

        return list(zip(result_emails, result_videos, result_reactions))

    @staticmethod
    def build_search_query(tokenized_query: List[str], videos_table_name: str,
                           users_table_name: str, video_reactions_table_name: str) -> str:
        """
        Builds the query for searching
        """
        where_conditions = []
        for token in tokenized_query:
            where_conditions.append(LIKE_SEARCH_TITLE_ELEMENT.format(token))
            where_conditions.append("OR")
            where_conditions.append(LIKE_SEARCH_DESCRIPTION_ELEMENT.format(token))
            where_conditions.append("OR")
        where_conditions = " ".join(where_conditions[:-1])
        return BASE_SEARCH_QUERY.format(users_table_name=users_table_name,
                                        video_with_likes=
                                        VIDEO_WITH_LIKES_QUERY.format(videos_table_name=videos_table_name,
                                                                      video_reactions_table_name=video_reactions_table_name)
                                        ) % where_conditions

    def search_videos(self, search_query: str) -> List[Tuple[Dict, VideoData, Dict[Reaction, int]]]:
        """
        Searches videos with a query

        :param search_query: the query to search
        :return: a list of (user data, video data, reactions counts)
        """
        tokenized_query = word_tokenize(search_query.lower())[:20]
        bigrams_query = [tokenized_query[i:i + 2] for i in range(len(tokenized_query) - 2 + 1)]

        self.logger.debug("Searching query %s" % search_query)
        cursor = self.conn.cursor()
        query = self.build_search_query(tokenized_query, self.videos_table_name, self.users_table_name,
                                        self.video_reactions_table_name)
        self.safe_query_run(self.conn, cursor, query)
        result = cursor.fetchall()
        # user_email, fullname, phone_number, photo, title, creation_time, visible, location, file_location, description, likes, dislikes
        result_videos = [VideoData(title=r[4], creation_time=r[5], visible=r[6], location=r[7],
                                   file_location=r[8], description=r[9])
                         for r in result]
        result_emails = [{"email": r[0], "fullname": r[1], "phone_number": r[2],
                          "photo": r[3]} for r in result]
        result_reactions = [{Reaction.like: r[10], Reaction.dislike: r[11]} for r in result]
        cursor.close()

        result = []
        for u, v, r in zip(result_emails, result_videos, result_reactions):
            word_count = 0
            desc_count = 0
            tokenized_title = word_tokenize(v.title.lower())
            bigrams_title = [tokenized_title[i:i + 2] for i in range(len(tokenized_title) - 2 + 1)]
            tokenized_desc = (word_tokenize(v.description[:1000].lower()) if v.description else [])
            for w in tokenized_query:
                word_count += len([t for t in tokenized_title if t == w])
                desc_count += len([t for t in tokenized_desc if t == w])
            for b in bigrams_query:
                word_count += len([t for t in bigrams_title if t == b])
            if word_count > 0 or desc_count > 0:
                result.append((u, v, r, word_count * 0.8 + desc_count * 0.2))
        result = sorted(result, key=lambda x: x[3], reverse=True)
        result = [(r[0], r[1], r[2]) for r in result]
        return result

    def react_video(self, actor_email: str, target_email: str,
                    video_title: str, reaction: Reaction) -> NoReturn:
        """
        Likes a video

        :param actor_email: the liker of the video
        :param target_email: the email of the owner of the video
        :param video_title: the title of the video
        :param reaction: the type of reaction
        """
        cursor = self.conn.cursor()
        self.logger.debug("User %s reacting to video" % actor_email)
        self.safe_query_run(self.conn, cursor,
                            REACTION_INSERT_QUERY.format(video_reactions_table_name=self.video_reactions_table_name),
                            (actor_email, target_email, video_title, reaction.value))
        self.conn.commit()
        cursor.close()

    def delete_reaction(self, actor_email: str, target_email: str,
                        video_title: str) -> NoReturn:
        """
        Deletes video reaction

        :param actor_email: the liker of the video
        :param target_email: the email of the owner of the video
        :param video_title: the title of the video
        """
        cursor = self.conn.cursor()
        self.logger.debug("Deleting reaction for user with email %s" % actor_email)
        self.safe_query_run(self.conn, cursor,
                            DELETE_REACTION_QUERY.format(video_reactions_table_name=self.video_reactions_table_name),
                            (actor_email, target_email, video_title))
        self.conn.commit()
        cursor.close()

    def comment_video(self, actor_email: str, target_email: str, video_title: str,
                      comment: str) -> NoReturn:
        """
        Comments a video

        :param actor_email: the email of the comment's author
        :param target_email: the email of the owner of the video
        :param video_title: the video title
        :param comment: the comment
        """
        cursor = self.conn.cursor()
        self.logger.debug("User %s commenting video" % actor_email)
        self.safe_query_run(self.conn, cursor,
                            COMMENT_VIDEO_QUERY.format(video_comments_table_name=self.video_comments_table_name),
                            (actor_email, target_email, video_title, comment, datetime.now().isoformat()))
        self.conn.commit()
        cursor.close()

    def get_comments(self, target_email: str, video_title: str) -> Tuple[List[Dict], List[Comment]]:
        """
        Get all the comments for a video

        :param target_email: the email of the owner of the video
        :param video_title: the title of the video
        :return: a tuple of (list of user data, list of comments)
        """
        self.logger.debug("Listing comments for %s video of %s" % (target_email, video_title))
        cursor = self.conn.cursor()

        self.safe_query_run(self.conn, cursor,
                            GET_COMMENTS_QUERY.format(
                                video_comments_table_name=self.video_comments_table_name,
                                users_table_name=self.users_table_name),
                            (target_email, video_title))
        result = cursor.fetchall()
        # u.email, u.fullname, u.phone_number, u.photo, vc.comment, vc.datetime
        result_comments = [Comment(content=r[4],timestamp=r[5]) for r in result]
        result_users = [{"email": r[0], "fullname": r[1], "phone_number": r[2],
                         "photo": r[3]} for r in result]
        cursor.close()
        return result_users, result_comments

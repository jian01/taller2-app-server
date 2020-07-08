from typing import NoReturn, List, Optional, NamedTuple, Tuple, Dict
from abc import abstractmethod
from datetime import datetime
from src.database.videos.video_database import VideoData, VideoDatabase, Reaction, Comment
from nltk import word_tokenize


class RamVideoDatabase(VideoDatabase):
    """
    Video ram database
    """
    videos_by_user: Dict[str, List[VideoData]]
    current_id: int

    def __init__(self):
        self.videos_by_user = {}
        self.reactions = {}
        self.comments = {}

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

    def delete_video(self, user_email: str, video_title: str) -> NoReturn:
        """
        Deletes a video from the database

        :param user_email: the user owner of the video
        :param video_title: the video title
        """
        if user_email in self.videos_by_user:
            self.videos_by_user[user_email] = [v for v in self.videos_by_user[user_email]
                                               if v.title!=video_title]

    def get_video_reactions(self, target_email: str, video_title: str) -> Dict[Reaction, int]:
        """
        Gets the video reaction counts

        :param target_email: the email of the video owner
        :param video_title: the video title
        :return: a dict of counts
        """
        result = {Reaction.like: 0, Reaction.dislike: 0}
        if target_email not in self.reactions or video_title not in self.reactions[target_email]:
            return result
        for _, r in self.reactions[target_email][video_title]:
            result[r] += 1
        return result

    def list_user_videos(self, user_email: str) -> List[Tuple[VideoData, Dict[Reaction, int]]]:
        """
        Get all the user videos

        :param user_email: the user's email
        :return: a list (video data, reactions counts)
        """
        videos = list(reversed(self.videos_by_user[user_email]))
        return [(v, self.get_video_reactions(user_email, v.title)) for v in videos]


    def list_top_videos(self) -> List[Tuple[Dict, VideoData, Dict[Reaction, int]]]:
        """
        Get top videos

        :return: a list of (user data, video data, reactions counts)
        """
        result = []
        for k, v in self.videos_by_user.items():
            for i in range(len(v)):
                if v[i].visible:
                    result.append(({"email": k}, v[i], self.get_video_reactions(k, v[i].title)))
        return result

    def search_videos(self, search_query: str) -> List[Tuple[Dict, VideoData, Dict[Reaction, int]]]:
        """
        Searches videos with a query

        :param search_query: the query to search
        :return: a list of (user data, video data, reactions counts)
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
        result = [(r[0],r[1], self.get_video_reactions(r[0]["email"], r[1].title)) for r in result]
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
        self.delete_reaction(actor_email, target_email, video_title)
        if target_email not in self.reactions:
            self.reactions[target_email] = {}
        if video_title not in self.reactions[target_email]:
            self.reactions[target_email][video_title] = []
        self.reactions[target_email][video_title].append((actor_email, reaction))

    def get_video_reaction(self, actor_email: str, target_email: str, video_title: str) -> Optional[Reaction]:
        """
        Gets the reaction of the user
        If there is no reaction returns None

        :param actor_email: the email of the user that reacted
        :param target_email: the owner of the video
        :param video_title: the video title
        :return: a reaction or None
        """
        if target_email not in self.reactions or video_title not in self.reactions[target_email]:
            return None
        reaction = [r for a, r in self.reactions[target_email][video_title] if a == actor_email]
        if not reaction:
            return None
        else:
            return reaction[0]

    def delete_reaction(self, actor_email: str, target_email: str,
                        video_title: str) -> NoReturn:
        """
        Deletes video reaction

        :param actor_email: the liker of the video
        :param target_email: the email of the owner of the video
        :param video_title: the title of the video
        """
        if target_email not in self.reactions or video_title not in self.reactions[target_email]:
            return
        self.reactions[target_email][video_title] = [r for r in self.reactions[target_email][video_title] if r[0] != actor_email]

    @abstractmethod
    def comment_video(self, actor_email: str, target_email: str, video_title: str,
                      comment: str) -> NoReturn:
        """
        Comments a video

        :param actor_email: the email of the comment's author
        :param target_email: the email of the owner of the video
        :param video_title: the video title
        :param comment: the comment
        """
        if not (target_email, video_title) in self.comments:
            self.comments[(target_email, video_title)] = []
        self.comments[(target_email, video_title)].append((actor_email,
                                                           Comment(content=comment,
                                                                   timestamp=datetime.now())))

    @abstractmethod
    def get_comments(self, target_email: str, video_title: str) -> Tuple[List[Dict], List[Comment]]:
        """
        Get all the comments for a video

        :param target_email: the email of the owner of the video
        :param video_title: the title of the video
        :return: a tuple of (list of user data, list of comments)
        """
        comment_tuples = []
        if (target_email, video_title) in self.comments:
            comment_tuples = list(reversed(self.comments[(target_email, video_title)]))
        user_data = [{"email": t[0]} for t in comment_tuples]
        comment_data = [t[1] for t in comment_tuples]
        return user_data, comment_data
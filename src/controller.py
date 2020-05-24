import json
import logging
from typing import Optional
from flask import request
from flask_cors import cross_origin
from flask_httpauth import HTTPTokenAuth

auth = HTTPTokenAuth(scheme='Bearer')


class Controller:
    logger = logging.getLogger(__name__)
    def __init__(self):
        """
        Here the init should receive all the parameters needed to know how to answer all the queries
        """

        @auth.verify_token
        def verify_token(token) -> bool:
            """
            Verifies a token

            :param token: the token to verify
            :return: the corresponding user
            """
            return True

    def api_health(self):
        """
        A dumb api health

        :return: a tuple with the text and the status to return
        """
        return "OK", 200
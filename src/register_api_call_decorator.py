from typing import Callable
from src.database.statistics.statistics_database import StatisticsDatabase, ApiCall
from datetime import datetime
from flask import request, Response
from timeit import default_timer as timer
import logging

statistics_database: StatisticsDatabase = None
logger = logging.getLogger("src.register_api_call_decorator")


def set_statistics_database(database: StatisticsDatabase):
    global statistics_database
    statistics_database = database


def register_api_call(func: Callable):
    global statistics_database

    def wrapper(*args, **kwargs):
        start = timer()
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            logger.exception("Internal Server Error")
            result = ("Internal Server Error", 500)
        time_elapsed = timer() - start
        if isinstance(result, tuple):
            api_call = ApiCall(path=request.path, method=request.method,
                               status=result[1], timestamp=datetime.now(),
                               time=time_elapsed)
        else:
            api_call = ApiCall(path=request.path, method=request.method,
                               status=result.status_code, timestamp=datetime.now(),
                               time=time_elapsed)
        try:
            statistics_database.register_api_call(api_call)
        except Exception as err:
            logger.exception("Error saving to statistics database")
            pass
        return result

    return wrapper

from typing import NamedTuple, NoReturn, List, Tuple, Dict, Generator
from abc import abstractmethod
from datetime import datetime

class ApiCall(NamedTuple):
    """
    Api call DTO
    """
    path: str
    status: int
    timestamp: datetime
    time: float
    method: str

class ApiCallsStatistics(NamedTuple):
    """
    The statistics of the api calls
    """
    last_30_days_uploaded_videos: List[Tuple[datetime, int]]
    last_30_days_user_registrations: List[Tuple[datetime, int]]
    last_30_days_users_logins: List[Tuple[datetime, int]]
    last_30_days_distinct_users_logged: int
    last_30_days_api_call_amount: List[Tuple[datetime, int]]
    last_30_day_mean_api_call_time: List[Tuple[datetime, float]]
    last_30_days_api_calls_by_path: Dict[str, int]
    last_30_days_api_calls_by_status: Dict[int, int]
    last_30_days_api_calls_response_time: List[float]
    last_30_days_api_calls_by_method: Dict[str, int]

class StatisticsDatabase:
    """
    Api statistics database
    """

    @abstractmethod
    def register_api_call(self, api_call: ApiCall) -> NoReturn:
        """
        Registers an api call

        :param api_call: the api call to register
        """

    @abstractmethod
    def last_30_days_api_calls(self) -> Generator[List[ApiCall], None, None]:
        """
        Gets a generator of the last 30 days api calls

        :return: a generator of lists of api calls
        """

    def compute_statistics(self) -> ApiCallsStatistics:
        """
        Computes the statistics
        :return: an ApiCallsStatistics object
        """

        api_call_generator = self.last_30_days_api_calls()

    @classmethod
    def factory(cls, name: str, *args, **kwargs) -> 'StatisticsDatabase':
        """
        Factory pattern for database

        :param name: the name of the database to create in the factory
        :return: a database object
        """
        database_types = {cls.__name__:cls for cls in StatisticsDatabase.__subclasses__()}
        return database_types[name](*args, **kwargs)
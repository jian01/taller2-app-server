from typing import NamedTuple, NoReturn, List, Tuple, Dict, Generator, Any
from abc import abstractmethod
from datetime import datetime, date, timedelta
import random

RELATIVE_SAMPLE_API_CALL_TIME = 0.1

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
    last_days_uploaded_videos: Dict[date, int]
    last_days_user_registrations: Dict[date, int]
    last_days_users_logins: Dict[date, int]
    last_days_api_call_amount: Dict[date, int]
    last_day_mean_api_call_time: Dict[date, float]
    last_days_api_calls_by_path: Dict[str, int]
    last_days_api_calls_by_status: Dict[int, int]
    last_days_api_calls_response_times_sample: List[float]
    last_days_api_calls_by_method: Dict[str, int]


class TechnicalMetrics(NamedTuple):
    mean_response_time_last_7_days: float
    api_calls_last_7_days: int
    status_500_rate_last_7_days: float
    status_400_rate_last_7_days: float


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
    def last_days_api_calls(self, days: int) -> Generator[List[ApiCall], None, None]:
        """
        Gets a generator of the last days api calls

        :param days: the number of days back
        :return: a generator of lists of api calls
        """

    def compute_statistics(self, days: int) -> ApiCallsStatistics:
        """
        Computes the statistics

        :param days: the number of days back
        :return: an ApiCallsStatistics object
        """
        today_datetime = datetime.now()
        api_call_generator = self.last_days_api_calls(days)
        api_call_statistics = ApiCallsStatistics(last_days_uploaded_videos={},
                                                 last_days_user_registrations={},
                                                 last_days_users_logins={},
                                                 last_days_api_call_amount={},
                                                 last_day_mean_api_call_time={},
                                                 last_days_api_calls_by_path={},
                                                 last_days_api_calls_by_status={},
                                                 last_days_api_calls_response_times_sample=[],
                                                 last_days_api_calls_by_method={})
        # Initialize all days at zero
        for i in range(days + 1):
            aux_date = today_datetime - timedelta(days=i)
            api_call_statistics.last_days_uploaded_videos[aux_date.date()] = 0
            api_call_statistics.last_days_user_registrations[aux_date.date()] = 0
            api_call_statistics.last_days_users_logins[aux_date.date()] = 0
            api_call_statistics.last_days_api_call_amount[aux_date.date()] = 0

        for api_calls in api_call_generator:
            for api_call in api_calls:
                days_delta = abs((today_datetime - api_call.timestamp).days)
                if days_delta > days:
                    continue

                # Video upload
                if api_call.method == "POST" and api_call.path == "/user/video" and api_call.status == 200:
                    api_call_statistics.last_days_uploaded_videos[api_call.timestamp.date()] += 1

                # User registration
                if api_call.method == "POST" and api_call.path == "/user" and api_call.status == 200:
                    api_call_statistics.last_days_user_registrations[api_call.timestamp.date()] += 1

                # User login
                if api_call.method == "POST" and api_call.path == "/user/login" and api_call.status == 200:
                    api_call_statistics.last_days_users_logins[api_call.timestamp.date()] += 1

                # Api call amount and mean time
                api_call_statistics.last_days_api_call_amount[api_call.timestamp.date()] += 1
                if api_call.timestamp.date() not in api_call_statistics.last_day_mean_api_call_time:
                    api_call_statistics.last_day_mean_api_call_time[api_call.timestamp.date()] = api_call.time
                else:
                    api_call_statistics.last_day_mean_api_call_time[api_call.timestamp.date()] += api_call.time

                # Calls by path
                if api_call.path not in api_call_statistics.last_days_api_calls_by_path:
                    api_call_statistics.last_days_api_calls_by_path[api_call.path] = 1
                else:
                    api_call_statistics.last_days_api_calls_by_path[api_call.path] += 1

                # Calls by status
                if api_call.status not in api_call_statistics.last_days_api_calls_by_status:
                    api_call_statistics.last_days_api_calls_by_status[api_call.status] = 1
                else:
                    api_call_statistics.last_days_api_calls_by_status[api_call.status] += 1

                # Response times
                if random.random() < RELATIVE_SAMPLE_API_CALL_TIME:
                    api_call_statistics.last_days_api_calls_response_times_sample.append(api_call.time)

                # Calls by method
                if api_call.method not in api_call_statistics.last_days_api_calls_by_method:
                    api_call_statistics.last_days_api_calls_by_method[api_call.method] = 1
                else:
                    api_call_statistics.last_days_api_calls_by_method[api_call.method] += 1

        for k in api_call_statistics.last_day_mean_api_call_time.keys():
            api_call_statistics.last_day_mean_api_call_time[k] /= api_call_statistics.last_days_api_call_amount[k]

        return api_call_statistics

    @abstractmethod
    def technical_metrics_from_server(self, alias: str) -> TechnicalMetrics:
        """
        Get technical metrics from a particular server

        :raises:
            UnexistentAppServer: if the alias is not associated with an app server

        :param alias: the alias of the app server
        :return: the technical metrics
        """

    @classmethod
    def factory(cls, name: str, *args, **kwargs) -> 'StatisticsDatabase':
        """
        Factory pattern for database

        :param name: the name of the database to create in the factory
        :return: a database object
        """
        database_types = {cls.__name__:cls for cls in StatisticsDatabase.__subclasses__()}
        return database_types[name](*args, **kwargs)
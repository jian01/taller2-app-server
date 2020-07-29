from src.database.statistics.statistics_database import ApiCall, StatisticsDatabase, TechnicalMetrics
from typing import NoReturn, Generator, List, Dict, Any
from datetime import datetime

DEFAULT_BATCH_SIZE = 100

class RamStatisticsDatabase(StatisticsDatabase):
    """
    Api statistics database
    """

    def __init__(self):
        self.api_calls = []

    def register_api_call(self, api_call: ApiCall) -> NoReturn:
        """
        Registers an api call

        :param api_call: the api call to register
        """
        self.api_calls.append(api_call)

    def last_days_api_calls(self, days: int) -> Generator[List[ApiCall], None, None]:
        """
        Gets a generator of the last days api calls

        :param days: the number of days back
        :return: a generator of lists of api calls
        """
        batches = len(self.api_calls)//DEFAULT_BATCH_SIZE
        batches += (1 if batches*DEFAULT_BATCH_SIZE < len(self.api_calls) else 0)
        for i in range(batches):
            yield [api_call
                   for api_call in self.api_calls[i*DEFAULT_BATCH_SIZE:(i+1)*DEFAULT_BATCH_SIZE]
                   if abs((datetime.now() - api_call.timestamp).days) <= days]

    def technical_metrics_from_server(self, alias: str) -> TechnicalMetrics:
        """
        Get technical metrics from a particular server

        :raises:
            UnexistentAppServer: if the alias is not associated with an app server

        :param alias: the alias of the app server
        :return: the technical metrics
        """
        status_500_count = 0
        status_400_count = 0
        api_call_count = 0
        response_time_sum = 0
        today_datetime = datetime.now()
        for call in self.api_calls:
            days_delta = abs((today_datetime - call.timestamp).days)
            if days_delta > 7:
                continue
            status_400_count += (1 if call.status == 400 else 0)
            status_500_count += (1 if call.status == 500 else 0)
            api_call_count += 1
            response_time_sum += call.time
        return TechnicalMetrics(mean_response_time_last_7_days=response_time_sum/api_call_count,
                                api_calls_last_7_days=api_call_count,
                                status_500_rate_last_7_days=status_500_count/api_call_count,
                                status_400_rate_last_7_days=status_400_count/api_call_count)

import psycopg2
import os
from src.database.statistics.statistics_database import ApiCall, StatisticsDatabase, TechnicalMetrics
from src.database.statistics.exceptions.unexistent_app_server import UnexistentAppServer
from typing import NoReturn, Generator, List, Optional, Tuple
import logging
import math
from src.database.utils.postgres_connection import PostgresUtils

DEFAULT_BATCH_SIZE = 200

ADD_API_CALL_QUERY = """
INSERT INTO {app_server_api_calls_table} (alias, path, status, datetime, "time", method)
VALUES (%s, %s, %s, %s, %s, %s)
"""

COUNT_ROWS_API_CALLS_QUERY = """
SELECT COUNT(*) FROM {app_server_api_calls_table}
WHERE datetime > NOW() - INTERVAL '%s days'
"""

GET_PAGINATED_API_CALLS_QUERY = """
SELECT path, status, datetime, "time", method
FROM {app_server_api_calls_table}
WHERE datetime > NOW() - INTERVAL '%s days'
LIMIT %s OFFSET %s;
"""

GET_CALS_BY_STATUS_QUERY = """
SELECT status, COUNT(*) as amount
FROM {app_server_api_calls_table}
WHERE datetime > NOW() - INTERVAL '%s days' AND alias = %s
GROUP BY status
"""

GET_MEAN_RESPONSE_TIMES_QUERY = """
SELECT AVG("time")
FROM {app_server_api_calls_table}
WHERE datetime > NOW() - INTERVAL '%s days' AND alias = %s
"""


class PostgresStatisticsDatabase(StatisticsDatabase):
    """
    Api statistics database
    """
    logger = logging.getLogger(__module__)

    def __init__(self, app_server_api_calls_table: str,
                 server_alias_env_name: str,
                 postgr_host_env_name: str, postgr_user_env_name: str,
                 postgr_pass_env_name: str, postgr_database_env_name: str):

        self.app_server_api_calls_table = app_server_api_calls_table
        self.server_alias = os.environ[server_alias_env_name]
        self.conn = PostgresUtils.get_postgres_connection(host=os.environ[postgr_host_env_name],
                                                          user=os.environ[postgr_user_env_name],
                                                          password=os.environ[postgr_pass_env_name],
                                                          database=os.environ[postgr_database_env_name])
        if self.conn.closed == 0:
            self.logger.info("Connected to postgres database")
        else:
            self.logger.error("Unable to connect to postgres database")
            raise ConnectionError("Unable to connect to postgres database")

    def register_api_call(self, api_call: ApiCall) -> NoReturn:
        """
        Registers an api call

        :param api_call: the api call to register
        """
        cursor = self.conn.cursor()
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     ADD_API_CALL_QUERY.format(
                                         app_server_api_calls_table=self.app_server_api_calls_table),
                                     (self.server_alias, api_call.path, api_call.status, api_call.timestamp.isoformat(),
                                      api_call.time, api_call.method))
        self.conn.commit()
        cursor.close()

    def last_days_api_calls(self, days: int) -> Generator[List[ApiCall], None, None]:
        """
        Gets a generator of the last days api calls

        :param days: the number of days back
        :return: a generator of lists of api calls
        """
        cursor = self.conn.cursor()

        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     COUNT_ROWS_API_CALLS_QUERY.format(
                                         app_server_api_calls_table=self.app_server_api_calls_table),
                                     (days,))
        result = cursor.fetchone()

        pages = int(math.ceil(result[0] / DEFAULT_BATCH_SIZE))
        for page in range(pages):
            PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                         GET_PAGINATED_API_CALLS_QUERY.format(
                                             app_server_api_calls_table=self.app_server_api_calls_table),
                                         (days, DEFAULT_BATCH_SIZE, page * DEFAULT_BATCH_SIZE))
            result = cursor.fetchall()
            # path, status, datetime, "time", method
            yield [ApiCall(path=r[0], status=r[1], timestamp=r[2],
                           time=r[3], method=r[4]) for r in result]

    def technical_metrics_from_server(self, alias: str) -> TechnicalMetrics:
        """
        Get technical metrics from a particular server

        :raises:
            UnexistentAppServer: if the alias is not associated with an app server

        :param alias: the alias of the app server
        :return: the technical metrics
        """
        cursor = self.conn.cursor()
        stats = {"total": 0, 400: 0, 500: 0, "mean_time": 0.0}
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     GET_CALS_BY_STATUS_QUERY.format(
                                         app_server_api_calls_table=self.app_server_api_calls_table),
                                     (7,alias))
        result = cursor.fetchall()
        if not result:
            raise UnexistentAppServer
        for r in result:
            stats["total"] += r[1]
            if r[0] == 400:
                stats[400] = r[1]
            if r[0] == 500:
                stats[500] = r[1]
        PostgresUtils.safe_query_run(self.logger, self.conn, cursor,
                                     GET_MEAN_RESPONSE_TIMES_QUERY.format(
                                         app_server_api_calls_table=self.app_server_api_calls_table),
                                     (7,alias))
        result = cursor.fetchall()
        for r in result:
            stats["mean_time"] = r[0]
        cursor.close()
        return TechnicalMetrics(mean_response_time_last_7_days=stats["mean_time"],
                                api_calls_last_7_days=stats["total"],
                                status_500_rate_last_7_days=stats[500] / stats["total"],
                                status_400_rate_last_7_days=stats[400] / stats["total"])
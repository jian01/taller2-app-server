import psycopg2
import os
from src.database.statistics.statistics_database import ApiCall, StatisticsDatabase
from typing import NoReturn, Generator, List, Optional, Tuple
import logging
import math

DEFAULT_BATCH_SIZE = 30

ADD_API_CALL_QUERY = """
INSERT INTO {app_server_api_calls_table} (alias, path, status, datetime, "time", method)
VALUES (%s, %s, %s, %s, %s, %s)
"""

COUNT_ROWS_API_CALLS_QUERY = """
SELECT COUNT(*) FROM {app_server_api_calls_table}
WHERE alias = %s
"""

GET_PAGINATED_API_CALLS_QUERY = """
SELECT path, status, datetime, "time", method
FROM {app_server_api_calls_table}
WHERE alias = %s
LIMIT %s OFFSET %s;
"""

class PostgresStatisticsDatabase(StatisticsDatabase):
    """
    Api statistics database
    """
    logger = logging.getLogger(__name__)

    def __init__(self, app_server_api_calls_table: str,
                 server_alias_env_name: str,
                 postgr_host_env_name: str, postgr_user_env_name: str,
                 postgr_pass_env_name: str, postgr_database_env_name: str):

        self.app_server_api_calls_table = app_server_api_calls_table
        self.server_alias = os.environ[server_alias_env_name]
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
        except Exception:
            connection.rollback()

    def register_api_call(self, api_call: ApiCall) -> NoReturn:
        """
        Registers an api call

        :param api_call: the api call to register
        """
        cursor = self.conn.cursor()
        self.safe_query_run(self.conn, cursor,
                            ADD_API_CALL_QUERY.format(app_server_api_calls_table=self.app_server_api_calls_table),
                            (self.server_alias, api_call.path, api_call.status, api_call.timestamp.isoformat(),
                             api_call.time, api_call.method))
        self.conn.commit()
        cursor.close()

    def last_30_days_api_calls(self) -> Generator[List[ApiCall], None, None]:
        """
        Gets a generator of the last 30 days api calls

        :return: a generator of lists of api calls
        """
        cursor = self.conn.cursor()

        self.safe_query_run(self.conn, cursor,
                            COUNT_ROWS_API_CALLS_QUERY.format(app_server_api_calls_table=self.app_server_api_calls_table),
                            (self.server_alias,))
        result = cursor.fetchone()

        pages = int(math.ceil(result[0] / DEFAULT_BATCH_SIZE))
        for page in range(pages):
            self.safe_query_run(self.conn, cursor,
                                GET_PAGINATED_API_CALLS_QUERY.format(app_server_api_calls_table=self.app_server_api_calls_table),
                                (self.server_alias, DEFAULT_BATCH_SIZE, page * DEFAULT_BATCH_SIZE))
            result = cursor.fetchall()
            # path, status, datetime, "time", method
            yield [ApiCall(path=r[0], status=r[1], timestamp=r[2],
                           time=r[3], method=r[4]) for r in result]

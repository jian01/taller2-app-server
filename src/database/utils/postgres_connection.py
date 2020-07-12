import psycopg2

# Perdon por esto, hotfix rapido, TODO: hacer un singleton que no de verguenza

postgres_connections = {}

class PostgresUtils:
    @staticmethod
    def get_postgres_connection(host: str, user: str, password: str, database: str):
        """
        Gets a postgres connection or returns an existing one if was already created

        :param host: host of the postgres db
        :param user: user
        :param password: password
        :param database: the database name
        :return: a postgres connection
        """
        global postgres_connections
        if (host, user, password, database) in postgres_connections:
            return postgres_connections[(host, user, password, database)]
        else:
            conn = psycopg2.connect(host=host, user=user,password=password,database=database)
            postgres_connections[(host, user, password, database)] = conn
            return conn


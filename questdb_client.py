import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class QuestDBClient:
    def __init__(self, host='127.0.0.1', port=8812, database='qdb', user='admin', password='quest'):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.connection.cursor()
            logger.info("Connected to QuestDB")
        except Exception as e:
            logger.error(f"Failed to connect to QuestDB: {e}")
            self.connection = None
            self.cursor = None

    def is_connected(self):
        return self.connection is not None and not self.connection.closed

    def create_tables(self):
        if not self.is_connected():
            return

        tables = [
            """
            CREATE TABLE IF NOT EXISTS ticks_ltp (
                timestamp TIMESTAMP,
                symbol SYMBOL,
                ltp DOUBLE,
                volume LONG
            ) timestamp(timestamp) PARTITION BY DAY;
            """,
            """
            CREATE TABLE IF NOT EXISTS ticks_quote (
                timestamp TIMESTAMP,
                symbol SYMBOL,
                bid DOUBLE,
                ask DOUBLE,
                spread DOUBLE,
                volume LONG,
                open_interest LONG
            ) timestamp(timestamp) PARTITION BY DAY;
            """,
            """
            CREATE TABLE IF NOT EXISTS ticks_depth (
                timestamp TIMESTAMP,
                symbol SYMBOL,
                level INT,
                bid DOUBLE,
                ask DOUBLE,
                bid_qty LONG,
                ask_qty LONG
            ) timestamp(timestamp) PARTITION BY DAY;
            """
        ]

        for table_query in tables:
            try:
                self.cursor.execute(table_query)
                self.connection.commit()
            except Exception as e:
                logger.warning(f"Table creation: {e}")
                self.connection.rollback()

    def insert_ltp(self, symbol, ltp, volume=None):
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO ticks_ltp (timestamp, symbol, ltp, volume)
            VALUES (%s, %s, %s, %s)
            """
            timestamp = datetime.now()  # Use local time (IST)
            self.cursor.execute(query, (timestamp, symbol, ltp, volume))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert LTP: {e}")
            self.connection.rollback()
            return False

    def insert_quote(self, symbol, bid, ask, spread, volume, open_interest):
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO ticks_quote (timestamp, symbol, bid, ask, spread, volume, open_interest)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            timestamp = datetime.now()  # Use local time (IST)
            self.cursor.execute(query, (timestamp, symbol, bid, ask, spread, volume, open_interest))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert quote: {e}")
            self.connection.rollback()
            return False

    def insert_depth(self, symbol, level, bid, ask, bid_qty, ask_qty):
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO ticks_depth (timestamp, symbol, level, bid, ask, bid_qty, ask_qty)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            timestamp = datetime.now()  # Use local time (IST)
            self.cursor.execute(query, (timestamp, symbol, level, bid, ask, bid_qty, ask_qty))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert depth: {e}")
            self.connection.rollback()
            return False

    def batch_insert_ltp(self, data):
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO ticks_ltp (timestamp, symbol, ltp)
            VALUES %s
            """
            timestamp = datetime.now()  # Use local time (IST)
            values = [(timestamp, item['symbol'], item['ltp']) for item in data]
            execute_values(self.cursor, query, values)
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to batch insert LTP: {e}")
            self.connection.rollback()
            return False

    def get_latest_ticks(self, symbol, limit=100):
        if not self.is_connected():
            return []

        try:
            query = """
            SELECT timestamp, ltp
            FROM ticks_ltp
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """
            self.cursor.execute(query, (symbol, limit))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch latest ticks: {e}")
            return []

    def get_aggregated_data(self, symbol, interval='1m', start_time=None, limit=500):
        if not self.is_connected():
            return []

        try:
            if start_time is None:
                start_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            # QuestDB aggregation query
            query = """
            SELECT
                timestamp as time,
                first(ltp) as open,
                max(ltp) as high,
                min(ltp) as low,
                last(ltp) as close,
                count(*) as volume
            FROM ticks_ltp
            WHERE symbol = %s AND timestamp >= %s
            SAMPLE BY %s
            ORDER BY time DESC
            LIMIT %s
            """

            self.cursor.execute(query, (symbol, start_time, interval, limit))
            results = self.cursor.fetchall()

            # Reverse to get chronological order
            return list(reversed(results))
        except Exception as e:
            logger.error(f"Failed to fetch aggregated data: {e}")
            # Fallback to simple query
            try:
                query = """
                SELECT
                    timestamp as time,
                    ltp as close,
                    ltp as open,
                    ltp as high,
                    ltp as low,
                    1 as volume
                FROM ticks_ltp
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """
                self.cursor.execute(query, (symbol, limit))
                results = self.cursor.fetchall()
                return list(reversed(results))
            except Exception as e2:
                logger.error(f"Fallback query also failed: {e2}")
                return []

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Disconnected from QuestDB")
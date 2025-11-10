import math
from datetime import date
from logging import Logger
from typing import Optional

from psycopg import Connection, Cursor
from psycopg.sql import SQL, Identifier, Placeholder
from psycopg.types.json import Json

from libs.utils import get_bounding_datetime

class SupabaseStage:
    def __init__(self, tables: dict, read_batch_size: int,
                 write_batch_size: int, logger: Logger):
        """
        Initialize the SupabaseStage interface.
        Args:
            tables (dict): The name of the tables to be used in this class.
            read_batch_size (int): The batch size for reading from Supabase.
            write_batch_size (int): The batch size for writing to Supabase.
            logger (Logger): The Logger instance for logging.
            db_instance: The DB instance for creating and checking connections.
        Returns:
            None
        """
        self.schema = "stage"
        self.read_batch_size = read_batch_size
        self.write_batch_size = write_batch_size
        self.logger = logger

        self.artist_table = tables["artist"]
        self.venue_table = tables["venue"]
        self.event_table = tables["event"]
    
    
    def get_artists(self, cursor: Cursor) -> list[dict]:
        results = []
        offset = 0

        try:
            while True:
                query = SQL("""
                    SELECT * 
                    FROM {}.{}
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.artist_table))

                values = (self.read_batch_size, offset)
                rows = cursor.execute(query, values).fetchall()

                if not rows:
                    break

                if cursor.description is None:
                    raise ValueError("Unexpected empty result")

                columns = [desc[0] for desc in cursor.description]
                batch = [dict(zip(columns, row)) for row in rows]
                results.extend(batch)
                offset += self.read_batch_size

            return results
        except Exception as e:
            self.logger.warning(f"Error retrieving artists: {e}")
            raise


    def get_venues(self, cursor: Cursor) -> list[dict]:
        results = []
        offset = 0

        try:
            while True:
                query = SQL("""
                    SELECT id, name, address, city, state, country, postal_code,
                        latitude, longitude, timezone, phone, website,
                        capacity, social, source, source_id 
                    FROM {}.{}
                    WHERE name IS NOT NULL AND name != 'null'
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.venue_table))

                values = (self.read_batch_size, offset)
                rows = cursor.execute(query, values).fetchall()

                if not rows:
                    break

                if cursor.description is None:
                    raise ValueError("Unexpected empty result")

                columns = [desc[0] for desc in cursor.description]
                batch = [dict(zip(columns, row)) for row in rows]
                results.extend(batch)
                offset += self.read_batch_size

            return results
        except Exception as e:
            self.logger.warning(f"Error retrieving venues: {e}")
            raise


    def get_event_date_range(self, cursor: Cursor) -> tuple[Optional[date], Optional[date]]:
        query = SQL("""
            SELECT GREATEST(MIN(datetime_local), CURRENT_DATE - INTERVAL '7 days') AS start_date,
                MAX(datetime_local) AS end_date
            FROM {}.{};
        """).format(Identifier(self.schema), Identifier(self.event_table))

        try:
            row = cursor.execute(query).fetchone()

            if row and row[0] is not None and row[1] is not None:
                return row[0].date(), row[1].date()
            else:
                return None, None
        except Exception as e:
            self.logger.warning(f"Error retrieving event date range: {e}")
            raise


    def get_events_on_date(self, cursor: Cursor, date: date) -> list[dict]:
        start_datetime, end_datetime = get_bounding_datetime(date)
        results = []
        offset = 0

        try:
            while True:
                query = SQL("""
                    SELECT *
                    FROM {}.{}
                    WHERE datetime_local BETWEEN %s AND %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.event_table))

                values = (start_datetime, end_datetime, self.read_batch_size, offset)
                rows = cursor.execute(query, values).fetchall()

                if not rows:
                    break

                if cursor.description is None:
                    raise ValueError("Unexpected empty result")

                columns = [desc[0] for desc in cursor.description]
                batch = [dict(zip(columns, row)) for row in rows]
                results.extend(batch)
                offset += self.read_batch_size

            return results
        except Exception as e:
            self.logger.warning(f"Error retrieving events: {e}")
            raise

    def save_artists(self, conn: Connection, cursor: Cursor, artists: list[dict]) -> None:
        """
        Saves data to the stage artist table in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(artists), batch_size):
                    batch = artists[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.artist_table)
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise


    def save_venues(self, conn: Connection, cursor: Cursor, venues: list[dict]) -> None:
        """
        Saves data to the stage venue table in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(venues), batch_size):
                    batch = venues[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.venue_table)
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise


    def save_events(self, conn: Connection, cursor: Cursor, events: list[dict]) -> None:
        """
        Saves data to the stage event table in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(events), batch_size):
                    batch = events[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.event_table)
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise
    
    
    def __upsert_in_batch(self, cursor: Cursor, data: list[dict], table_name: str) -> None:
        """
        Upserts all data in one go.
        """
        if not data:
            return
        
        columns = list(data[0].keys())

        values = []
        for row in data:
            row_tuple = []
            for col in columns:
                val = row[col]
                if isinstance(val, dict):
                    val = Json(val) 
                elif isinstance(val, list):
                    if len(val) > 0 and isinstance(val[0], dict):
                        val = Json(val)
                elif isinstance(val, (int, float)) and math.isnan(val):
                    val = None
                row_tuple.append(val)
            values.append(tuple(row_tuple))

        query = SQL("""
            INSERT INTO {}.{} ({})
            VALUES ({})
            ON CONFLICT (id) DO UPDATE SET {};
        """).format(
            Identifier(self.schema),
            Identifier(table_name),
            SQL(', ').join(map(Identifier, columns)),
            SQL(', ').join(Placeholder() * len(columns)),
            SQL(', ').join([SQL('{} = EXCLUDED.{}').format(Identifier(col), Identifier(col))
                            for col in columns if col != "id"])
        )
        
        cursor.executemany(query, values)
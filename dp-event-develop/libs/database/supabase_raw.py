import math
from datetime import datetime
from logging import Logger

from psycopg import Connection, Cursor
from psycopg.sql import SQL, Identifier, Placeholder
from psycopg.types.json import Json


class SupabaseRaw:
    def __init__(self, tables: dict, read_batch_size: int,
                 write_batch_size: int, logger: Logger):
        """
        Initialize the SupabaseRaw interface.
        Args:
            tables (dict): The name of the tables to be used in this class.
            read_batch_size (int): The batch size for reading from Supabase.
            write_batch_size (int): The batch size for writing to Supabase.
            logger (Logger): The Logger instance for logging.
        Returns:
            None
        """
        self.schema = "raw"
        self.read_batch_size = read_batch_size
        self.write_batch_size = write_batch_size
        self.logger = logger

        self.seatgeek_event_table = tables["seatgeek_event"]
        self.seatgeek_venue_table = tables["seatgeek_venue"]
        self.seatgeek_performer_table = tables["seatgeek_performer"]
        self.ticketmaster_event_table = tables["ticketmaster_event"]
        self.ticketmaster_venue_table = tables["ticketmaster_venue"]
        self.ticketmaster_attraction_table = tables["ticketmaster_attraction"]

     
    def get_seatgeek_artists(self, cursor: Cursor, last_processed_date: datetime) -> list[dict]:
        results = []
        offset = 0
        try:
            while True:
                query = SQL("""
                    SELECT id, name, image, spotify_id
                    FROM {}.{}
                    WHERE modified_at > %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.seatgeek_performer_table))

                values = (last_processed_date.strftime("%Y-%m-%d %H:%M:%S%z"), self.read_batch_size, offset)
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
            self.logger.warning(f"Error retrieving SeatGeek artists: {e}")
            raise


    def get_seatgeek_venues(self, cursor: Cursor, last_processed_date: datetime) -> list[dict]:
        results = []
        offset = 0
        try:
            while True:
                query = SQL("""
                    SELECT id, name, address, city, state, country, postal_code, timezone, location, capacity
                    FROM {}.{}
                    WHERE modified_at > %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.seatgeek_venue_table))

                values = (last_processed_date.strftime("%Y-%m-%d %H:%M:%S%z"), self.read_batch_size, offset)
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
            self.logger.warning(f"Error retrieving SeatGeek Venues: {e}")
            raise


    def get_seatgeek_events(self, cursor: Cursor, last_processed_date: datetime) -> list[dict]:
        results = []
        offset = 0
        try:
            while True:
                query = SQL("""
                    SELECT id, title, type, datetime_local, datetime_utc, timezone, venue, performers
                    FROM {}.{}
                    WHERE modified_at > %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.seatgeek_event_table))

                values = (last_processed_date.strftime("%Y-%m-%d %H:%M:%S"), self.read_batch_size, offset)
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
            self.logger.warning(f"Error retrieving SeatGeek Events: {e}")
            raise


    def get_ticketmaster_artists(self, cursor: Cursor, last_processed_date: datetime) -> list[dict]:
        results = []
        offset = 0
        try:
            while True:
                query = SQL("""
                    SELECT id, name, images, spotify_id
                    FROM {}.{}
                    WHERE modified_at > %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.ticketmaster_attraction_table))

                values = (last_processed_date.strftime("%Y-%m-%d %H:%M:%S%z"), self.read_batch_size, offset)
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
            self.logger.warning(f"Error retrieving Ticketmaster artists: {e}")
            raise


    def get_ticketmaster_venues(self, cursor: Cursor, last_processed_date: datetime) -> list[dict]:
        results = []
        offset = 0
        try:
            while True:
                query = SQL("""
                    SELECT id, name, address, city, state, country, postal_code, timezone, location
                    FROM {}.{}
                    WHERE modified_at > %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.ticketmaster_venue_table))

                values = (last_processed_date.strftime("%Y-%m-%d %H:%M:%S"), self.read_batch_size, offset)
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
            self.logger.warning(f"Error retrieving Ticketmaster Venues: {e}")
            raise


    def get_ticketmaster_events(self, cursor: Cursor, last_processed_date: datetime) -> list[dict]:
        results = []
        offset = 0
        try:
            while True:
                query = SQL("""
                    SELECT id, name, type, datetime_local, datetime_utc, timezone, venues, attractions, price_ranges
                    FROM {}.{}
                    WHERE modified_at > %s
                    ORDER BY id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.ticketmaster_event_table))

                values = (last_processed_date.strftime("%Y-%m-%d %H:%M:%S"), self.read_batch_size, offset)
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
            self.logger.warning(f"Error retrieving Ticketmaster Events: {e}")
            raise


    def save_seatgeek_events(self, conn: Connection, cursor: Cursor, events: list[dict]) -> None:
        """
        Saves raw SeatGeek event data to Supabase in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(events), batch_size):
                    batch = events[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.seatgeek_event_table)
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise


    def save_seatgeek_venues(self, conn: Connection, cursor: Cursor, venues: list[dict]) -> None:
        """
        Saves raw SeatGeek venue data to Supabase in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(venues), batch_size):
                    batch = venues[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.seatgeek_venue_table)
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise


    def save_seatgeek_performers(self, conn: Connection, cursor: Cursor, performers: list[dict]) -> None:
        """
        Saves raw SeatGeek performer data to Supabase in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(performers), batch_size):
                    batch = performers[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.seatgeek_performer_table)
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise


    def save_ticketmaster_events(self, conn: Connection, cursor: Cursor, events: list[dict]) -> None:
        """
        Saves raw Ticketmaster event data to Supabase in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(events), batch_size):
                    batch = events[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.ticketmaster_event_table)
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise


    def save_ticketmaster_venues(self, conn: Connection, cursor: Cursor, venues: list[dict]) -> None:
        """
        Saves raw Ticketmaster venue data to Supabase in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(venues), batch_size):
                    batch = venues[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.ticketmaster_venue_table)
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise


    def save_ticketmaster_attractions(self, conn: Connection, cursor: Cursor, attractions: list[dict]) -> None:
        """
        Saves raw Ticketmaster attraction data to Supabase in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(attractions), batch_size):
                    batch = attractions[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.ticketmaster_attraction_table)
        
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
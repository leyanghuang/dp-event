import math
from datetime import date
from logging import Logger

from psycopg import Connection, Cursor
from psycopg.sql import SQL, Identifier, Placeholder
from psycopg.types.json import Json

from libs.utils import get_bounding_datetime


class SupabasePublic:
    def __init__(self, tables: dict, read_batch_size: int,
                 write_batch_size: int, logger: Logger):
        """
        Initialize the SupabasePublic interface.
        Args:
            tables (dict): The name of the tables to be used in this class.
            read_batch_size (int): The batch size for reading from Supabase.
            write_batch_size (int): The batch size for writing to Supabase.
            logger (Logger): The Logger instance for logging.
        Returns:
            None
        """
        self.schema = "public"
        self.read_batch_size = read_batch_size
        self.write_batch_size = write_batch_size
        self.logger = logger

        self.artist_table = tables["artist"]
        self.venue_table = tables["venue"]
        self.dma_table = tables["dma"]
        self.market_table = tables["market"]
        self.venue_dma_table = tables["venue_dma"]
        self.event_table = tables["event"]
        self.event_artist_table = tables["event_artist"]
        

    def get_artists(self, cursor: Cursor) -> list[dict]:
        results = []
        offset = 0

        try:
            while True:
                query = SQL("""
                    SELECT id, spotify_id, seatgeek_ids, ticketmaster_ids  
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
                        capacity, social, ticketmaster_ids, seatgeek_ids, is_valid
                    FROM {}.{}
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


    def get_dmas(self, cursor: Cursor) -> list[dict]:
        query = SQL("""
            SELECT d.id, 
                d.geometry, 
                COALESCE(jsonb_agg(
                    jsonb_build_object('id', m.id, 'coordinates', m.coordinates)
                ) FILTER (WHERE m.id IS NOT NULL), '[]'::jsonb) AS market
            FROM {}.{} AS d
            LEFT JOIN {}.{} AS m ON d.id = m.dma_id
            GROUP BY d.id, d.geometry;
        """).format(Identifier(self.schema), Identifier(self.dma_table),
                    Identifier(self.schema), Identifier(self.market_table))

        try:
            rows = cursor.execute(query).fetchall()

            if cursor.description is None:
                raise ValueError("Unexpected empty result")

            columns = [desc[0] for desc in cursor.description] 
            results = [dict(zip(columns, row)) for row in rows]
            if results:
                return results   
        except Exception as e:
            self.logger.warning(f"Error retrieving DMAs: {e}")
            raise
        return []

    def get_matched_venues(self, cursor: Cursor) -> set:
        matched_venue_ids = set()
        offset = 0

        try:
            while True:
                query = SQL("""
                    SELECT DISTINCT venue_id
                    FROM {}.{}
                    ORDER BY venue_id
                    LIMIT %s OFFSET %s;
                """).format(Identifier(self.schema), Identifier(self.venue_dma_table))

                values = (self.read_batch_size, offset)
                rows = cursor.execute(query, values).fetchall()

                if not rows:
                    break

                batch_ids = {row[0] for row in rows}
                matched_venue_ids.update(batch_ids)

                offset += self.read_batch_size

            return matched_venue_ids

        except Exception as e:
            self.logger.warning(f"Error retrieving matched venues: {e}")
            raise

    def get_events_on_date(self, cursor: Cursor, date: date) -> list[dict]:
        start_datetime, end_datetime = get_bounding_datetime(date)
        results = []
        offset = 0

        try:
            while True:
                query = SQL("""
                    SELECT id, seatgeek_ids, ticketmaster_ids
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
        Saves artist data to Supabase in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(artists), batch_size):
                    batch = artists[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.artist_table, on_conflict="id")
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise


    def save_venues(self, conn: Connection, cursor: Cursor, venues: list[dict], venue_dmas: list[dict]) -> None:
        """
        Saves venue data to Supabase in batches.
        """
        try:
            with conn.transaction():
                batch_size = self.write_batch_size
                for i in range(0, len(venues), batch_size):
                    batch = venues[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.venue_table, on_conflict="id")
                
                for i in range(0, len(venue_dmas), batch_size):
                    batch = venue_dmas[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.venue_dma_table, on_conflict=["venue_id", "dma_id"])
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise


    def save_events(self, conn: Connection, cursor: Cursor, events: list[dict], event_artists: list[dict]) -> None:
        """
        Saves event data to Supabase in batches.
        """
        try:
            with conn.transaction():
                # Save events
                batch_size = self.write_batch_size
                for i in range(0, len(events), batch_size):
                    batch = events[i:i + batch_size]
                    self.__upsert_in_batch(cursor, batch, self.event_table, on_conflict="id")

                # Delete existing event_artists
                event_ids = [event_artist["event_id"] for event_artist in event_artists]
                delete_query = SQL("""
                    DELETE FROM {}.{}
                    WHERE event_id::text = ANY(%s);
                """).format(Identifier(self.schema), Identifier(self.event_artist_table))

                cursor.execute(delete_query, (event_ids,))

                # Save event_artists
                for i in range(0, len(event_artists), batch_size):
                    batch = event_artists[i:i + batch_size]
                    self.__insert_in_batch(cursor, batch, self.event_artist_table)
        
        except Exception as e:
            self.logger.warning(f"Error upserting data: {e}")
            raise
    

    def __upsert_in_batch(self, cursor: Cursor, data: list[dict], table_name: str, on_conflict: str | list[str]) -> None:
        """
        Upserts all data in one go.
        """
        if not data:
            return
        
        columns = list(data[0].keys())

        on_conflict = on_conflict if isinstance(on_conflict, list) else [on_conflict]

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
            ON CONFLICT ({}) DO UPDATE SET {};
        """).format(
            Identifier(self.schema),
            Identifier(table_name),
            SQL(', ').join(map(Identifier, columns)),
            SQL(', ').join(Placeholder() * len(columns)),
            SQL(', ').join(map(Identifier, on_conflict)),
            SQL(', ').join([SQL('{} = EXCLUDED.{}').format(Identifier(col), Identifier(col))
                            for col in columns if col not in on_conflict])
        )
        
        cursor.executemany(query, values)
    

    def __insert_in_batch(self, cursor: Cursor, data: list[dict], table_name: str) -> None:
        """
        Inserts all data in one go.
        """
        if not data:
            return
        
        columns = list(data[0].keys())
        values = [tuple(row[col] for col in columns) for row in data]

        query = SQL("""
            INSERT INTO {}.{} ({})
            VALUES ({});
        """).format(
            Identifier(self.schema),
            Identifier(table_name),
            SQL(', ').join(map(Identifier, columns)),
            SQL(', ').join(Placeholder() * len(columns))
        )
        
        cursor.executemany(query, values)
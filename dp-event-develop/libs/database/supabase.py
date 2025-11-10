from datetime import datetime, date
from typing import Optional
from logging import Logger

import psycopg

from libs.database.database import Database
from libs.database.supabase_raw import SupabaseRaw
from libs.database.supabase_stage import SupabaseStage
from libs.database.supabase_public import SupabasePublic
from libs.database.supabase_log import SupabaseLog
from libs.utils import retry_on_db_error

class SupabaseDatabase(Database):
    def __init__(self, tables: dict, user: str, password: str, host: str, port: str, dbname: str,
                 read_batch_size: int, write_batch_size: int, logger: Logger):
        
        self.supabase_raw = SupabaseRaw(tables["raw"], read_batch_size, write_batch_size, logger)
        self.supabase_stage = SupabaseStage(tables["stage"], read_batch_size, write_batch_size, logger)
        self.supabase_public = SupabasePublic(tables["public"], read_batch_size, write_batch_size, logger)
        self.supabase_log = SupabaseLog(tables["log"]["log_table"], logger)
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.dbname = dbname
        self.logger = logger


    # Logging functions
    @retry_on_db_error()
    def save_job_start_time(self, job_name: str) -> Optional[datetime]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_log.save_job_start_time(cursor, job_name)
    
    @retry_on_db_error()
    def save_job_completed_time(self, status: str) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                self.supabase_log.save_job_completed_time(cursor, status)
    
    @retry_on_db_error()
    def update_last_processed_date(self, last_processed_date: Optional[datetime] = None) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                self.supabase_log.update_last_processed_date(cursor, last_processed_date)

    # Raw functions
    @retry_on_db_error()
    def get_raw_seatgeek_artists(self, last_processed_date: datetime) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.get_seatgeek_artists(cursor, last_processed_date)
    
    @retry_on_db_error()
    def get_raw_seatgeek_venues(self, last_processed_date: datetime) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.get_seatgeek_venues(cursor, last_processed_date)
    
    @retry_on_db_error()
    def get_raw_seatgeek_events(self, last_processed_date: datetime) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.get_seatgeek_events(cursor, last_processed_date)
    
    @retry_on_db_error()
    def get_raw_ticketmaster_artists(self, last_processed_date: datetime) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.get_ticketmaster_artists(cursor, last_processed_date)
    
    @retry_on_db_error()
    def get_raw_ticketmaster_venues(self, last_processed_date: datetime) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.get_ticketmaster_venues(cursor, last_processed_date)
    
    @retry_on_db_error()
    def get_raw_ticketmaster_events(self, last_processed_date: datetime) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.get_ticketmaster_events(cursor, last_processed_date)
    
    @retry_on_db_error()
    def save_raw_seatgeek_events(self, events: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.save_seatgeek_events(conn, cursor, events)

    @retry_on_db_error()
    def save_raw_seatgeek_venues(self, venues: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.save_seatgeek_venues(conn, cursor, venues)
    
    @retry_on_db_error()
    def save_raw_seatgeek_performers(self, performers: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.save_seatgeek_performers(conn, cursor, performers)
    
    @retry_on_db_error()
    def save_raw_ticketmaster_events(self, events: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.save_ticketmaster_events(conn, cursor, events)

    @retry_on_db_error()
    def save_raw_ticketmaster_venues(self, venues: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.save_ticketmaster_venues(conn, cursor, venues)
    
    @retry_on_db_error()
    def save_raw_ticketmaster_attractions(self, attractions: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_raw.save_ticketmaster_attractions(conn, cursor, attractions)
    
    # Stage functions
    @retry_on_db_error()
    def get_stage_artists(self) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_stage.get_artists(cursor)
    
    @retry_on_db_error()
    def get_stage_venues(self) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_stage.get_venues(cursor)
    
    @retry_on_db_error()
    def get_stage_event_date_range(self) -> tuple[date | None, date | None]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_stage.get_event_date_range(cursor)
    
    @retry_on_db_error()
    def get_stage_events_on_date(self, date: date) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_stage.get_events_on_date(cursor, date)
    
    @retry_on_db_error()
    def save_stage_artists(self, artists: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                self.supabase_stage.save_artists(conn, cursor, artists)
    
    @retry_on_db_error()
    def save_stage_venues(self, venues: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                self.supabase_stage.save_venues(conn, cursor, venues)
    
    @retry_on_db_error()
    def save_stage_events(self, events: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                self.supabase_stage.save_events(conn, cursor, events)
    
    # Public functions
    @retry_on_db_error()
    def get_public_artists(self) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_public.get_artists(cursor)
    
    @retry_on_db_error()
    def get_public_venues(self) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_public.get_venues(cursor)
    
    @retry_on_db_error()
    def get_public_dmas(self) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_public.get_dmas(cursor)
    
    @retry_on_db_error()
    def get_matched_public_venues(self) -> set:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_public.get_matched_venues(cursor)
    
    @retry_on_db_error()
    def get_public_events_on_date(self, date: date) -> list[dict]:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                return self.supabase_public.get_events_on_date(cursor, date)
    
    @retry_on_db_error()
    def save_public_artists(self, artists: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                self.supabase_public.save_artists(conn, cursor, artists)
    
    @retry_on_db_error()
    def save_public_venues(self, venues: list[dict], venue_dma_map: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                self.supabase_public.save_venues(conn, cursor, venues, venue_dma_map)
    
    @retry_on_db_error()
    def save_public_events(self, events: list[dict], event_artists: list[dict]) -> None:
        with psycopg.connect(user=self.user, password=self.password, host=self.host,
                             port=self.port, dbname=self.dbname, autocommit=True) as conn:
            with conn.cursor() as cursor:
                self.supabase_public.save_events(conn, cursor, events, event_artists)
from datetime import datetime, date
from typing import Optional
from abc import ABC, abstractmethod


class Database(ABC):
    # Logging functions
    @abstractmethod
    def save_job_start_time(self, job_name: str) -> Optional[datetime]:
        """Save the start time of the job and return the last processed date for stage jobs"""
        pass

    @abstractmethod
    def save_job_completed_time(self, status: str) -> None:
        """Save the completion time of the job"""
        pass

    @abstractmethod
    def update_last_processed_date(self, last_processed_date: Optional[datetime] = None) -> None:
        """Update the last processed date for the job"""
        pass
    
    
    # Raw functions
    @abstractmethod
    def get_raw_seatgeek_artists(self, last_processed_date: datetime) -> list[dict]:
        """Retrieves data from seatgeek_performer in batches."""
        pass

    @abstractmethod
    def get_raw_seatgeek_venues(self, last_processed_date: datetime) -> list[dict]:
        """Retrieves data from seatgeek_venue in batches."""
        pass

    @abstractmethod
    def get_raw_seatgeek_events(self, last_processed_date: datetime) -> list[dict]:
        """Retrieves data from seatgeek_event in batches."""
        pass
    
    @abstractmethod
    def get_raw_ticketmaster_artists(self, last_processed_date: datetime) -> list[dict]:
        """Retrieves data from ticketmaster_attraction in batches."""
        pass

    @abstractmethod
    def get_raw_ticketmaster_venues(self, last_processed_date: datetime) -> list[dict]:
        """Retrieves data from ticketmaster_venue in batches."""
        pass

    @abstractmethod
    def get_raw_ticketmaster_events(self, last_processed_date: datetime) -> list[dict]:
        """Retrieves data from ticketmaster_event in batches."""
        pass
    
    @abstractmethod
    def save_raw_seatgeek_events(self, events: list[dict]) -> None:
        """Saves SeatGeek events to raw"""
        pass

    @abstractmethod
    def save_raw_seatgeek_venues(self, venues: list[dict]) -> None:
        """Saves SeatGeek venues to raw"""
        pass

    @abstractmethod
    def save_raw_seatgeek_performers(self, performers: list[dict]) -> None:
        """Saves SeatGeek performers to raw"""
        pass
    
    @abstractmethod
    def save_raw_ticketmaster_events(self, events: list[dict]) -> None:
        """Saves Ticketmaster events to raw"""
        pass

    @abstractmethod
    def save_raw_ticketmaster_venues(self, venues: list[dict]) -> None:
        """Saves Ticketmaster venues to raw"""
        pass

    @abstractmethod
    def save_raw_ticketmaster_attractions(self, attractions: list[dict]) -> None:
        """Saves Ticketmaster attractions to raw"""
        pass


    # Stage functions
    @abstractmethod
    def get_stage_artists(self) -> list[dict]:
        """Retrieves artists from the stage table"""
        pass

    @abstractmethod
    def get_stage_venues(self) -> list[dict]:
        """Retrieves venues from the stage table"""
        pass

    @abstractmethod
    def get_stage_event_date_range(self) -> tuple[date | None, date | None]:
        """Retrieves the date range of events from the stage table"""
        pass

    @abstractmethod
    def get_stage_events_on_date(self, date: date) -> list[dict]:
        """Retrieves events on a specific date from the stage table"""
        pass

    @abstractmethod
    def save_stage_artists(self, artists: list) -> None:
        """Saves data to the artist stage table in Supabase in batches."""
        pass

    @abstractmethod
    def save_stage_venues(self, venues: list[dict]) -> None:
        """Saves data to the venue stage table in Supabase in batches."""
        pass

    @abstractmethod
    def save_stage_events(self, events: list[dict]) -> None:
        """Saves data to the event stage table in Supabase in batches."""
        pass


    # Public functions
    @abstractmethod
    def get_public_artists(self) -> list[dict]:
        """Retrieves artists from public"""
        pass

    @abstractmethod
    def get_public_venues(self) -> list[dict]:
        """Retrieves venues from public"""
        pass

    @abstractmethod
    def get_public_dmas(self) -> list[dict]:
        """Retrieves dmas from public"""
        pass

    @abstractmethod
    def get_matched_public_venues(self) -> set:
        """Retrieves matched venues from public"""
        pass

    @abstractmethod
    def get_public_events_on_date(self, date: date) -> list[dict]:
        """Retrieves events on a specific date from public"""
        pass

    @abstractmethod
    def save_public_artists(self, artists: list[dict]) -> None:
        """Saves artist data to public"""
        pass

    @abstractmethod
    def save_public_venues(self, venues: list[dict], venue_dma_map: list[dict]) -> None:
        """Saves venues and venue-dma maps to public"""
        pass

    @abstractmethod
    def save_public_events(self, events: list[dict], event_artists: list[dict]) -> None:
        """Saves event data to public"""
        pass
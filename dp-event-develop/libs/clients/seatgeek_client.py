import requests
from requests.exceptions import Timeout, RequestException
from datetime import datetime, timedelta, date, time
import time as t
from logging import Logger
from typing import Optional


class SeatgeekClient:
    def __init__(self, url: str, client_id: str, client_secret: str, event_fetch_limit: int,
                 api_retry_limit: int, api_retry_delay: int, logger: Logger) -> None:
        self.url = url
        self.client_id = client_id
        self.client_secret = client_secret
        self.event_fetch_limit = event_fetch_limit
        self.api_retry_limit = api_retry_limit
        self.api_retry_delay = api_retry_delay
        self.logger = logger


    def fetch_events_for_day(self, date: date) -> list[dict]:
        """
        Fetch events from SeatGeek API for a specific day.
        Args:
            date (datetime): Date for which events are to be fetched.
        Returns:
            list[dict]: List of events fetched from the API if available; an empty list otherwise.

        """
        events = []
        start_datetime = datetime.combine(date, time(0, 0, 0))
        end_datetime = start_datetime + timedelta(days=1)

        page = 1
        while True:
            response = self.__fetch_events(start_datetime, end_datetime, page)

            if not response:
                break
            
            events.extend(response)
            page += 1
        
        return events


    def fetch_performer(self, performer_id: str) -> Optional[dict]:
        """
        Fetch performer from SeatGeek API.
        Args:
            performer_id (str): ID of the performer to fetch.
        Returns:
            dict: Performer data fetched from the API.
        """        
        performer_url = f"{self.url}performers/{performer_id}"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        attempt = 1
        while attempt <= self.api_retry_limit:
            try:
                self.logger.info(f"Attempt {attempt}: Fetching performer with ID {performer_id}")

                response = requests.get(performer_url, params=params, timeout=30)

                if response and response.status_code == 200:
                    self.logger.info(f"Response received with status code 200.")
                    return response.json()
                
                elif response and response.status_code == 429:
                    self.logger.warning(f"Rate limit exceeded. Waiting for 15 minutes...")
                    t.sleep(15 * 60)  # Sleep for 15 minutes
                    self.logger.info("Resuming...")
                    continue

                elif response.status_code == 404:
                    self.logger.warning(f"Performer with ID {performer_id} not found.")
                    return None

                else:
                    self.logger.warning(f"Attempt {attempt}: Failed to fetch performer, status code {response.status_code}")
            
            except requests.exceptions.Timeout as e:
                self.logger.warning(f"Attempt {attempt}: Timeout occurred while fetching performer: {e}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Attempt {attempt}: An error occurred while fetching performer: {e}")
            
            attempt += 1
            t.sleep(self.api_retry_delay)

        self.logger.warning(f"Failed to fetch performer after {attempt - 1} attempts.")
        return None
    

    def __fetch_events(self, start_date: datetime, end_date: datetime, page: int=0) -> list[dict]:
        """
        Fetch events from SeatGeek API with date filters and retry mechanism.
        Args:
            start_date (datetime): Start date and time for the event.
            end_date (datetime): End date and time for the event.
            page (int): Page number for deep paging.
        Returns:
            list[dict]: List of event objects if available; an empty list otherwise.
        """
        event_url = f"{self.url}events"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "per_page": self.event_fetch_limit,
            "page": page,
            "datetime_utc.gte": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "datetime_utc.lt": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sort": "datetime_utc.asc",
        }

        attempt = 1
        while attempt <= self.api_retry_limit:
            try:
                self.logger.info(
                    f"Attempt {attempt}: Fetching events from {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')} "
                    f"to {end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}, page {page}")

                response = requests.get(event_url, params=params, timeout=30)

                if response and response.status_code == 200:
                    self.logger.info(f"Response received with status code 200.")
                    result = response.json()

                    return result.get('events', [])
                
                elif response.status_code == 429:
                    self.logger.warning(f"Rate limit exceeded. Waiting for 15 minutes...")
                    t.sleep(15 * 60)  # Sleep for 15 minutes
                    self.logger.info("Resuming...")
                    continue

                else:
                    self.logger.warning(f"Attempt {attempt}: Failed to fetch events, status code {response.status_code}")
            
            except requests.exceptions.Timeout as e:
                self.logger.warning(f"Attempt {attempt}: Timeout occurred while fetching events: {e}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Attempt {attempt}: An error occurred while fetching events: {e}")
            
            attempt += 1
            t.sleep(self.api_retry_delay)

        self.logger.error(f"Failed to fetch event after {attempt - 1} attempts.")
        return []
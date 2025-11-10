import time as t
import requests
from datetime import datetime, timezone, timedelta, time
from logging import Logger


class TicketmasterClient:
    def __init__(self, url: str, api_keys: list, api_size_limit: int,
                 api_retry_limit: int, api_retry_delay: int, logger: Logger) -> None:
        self.url = url
        self.api_keys = api_keys
        self.api_size_limit = api_size_limit
        self.api_retry_limit = api_retry_limit
        self.api_retry_delay = api_retry_delay
        self.logger = logger
        self.__set_api_key(initial=True)


    def fetch_events_for_day(self, date):
        """
        Fetch events from Ticketmaster API for a specific day.
        Args:
            date (datetime): Date for which events are to be fetched.
        Returns:
            list: List of events fetched from the API.
        """
        events = []
        for hour in range(24):  # Hour by hour fetching
            start_datetime = datetime.combine(date, time(hour, 0, 0))
            end_datetime = start_datetime + timedelta(hours=1)

            page = 0  # Reset page number for each hour
            while True:
                response = self.__fetch_events(start_datetime, end_datetime, page)

                if not response:
                    break
                
                events.extend(response)
                page += 1

                if page * self.api_size_limit >= 1000:
                    self.logger.warning("Deep paging limit exceeded. Skipping...")
                    break
                    
        return events

    
    def __fetch_events(self, start_date: datetime, end_date: datetime, page: int=0) -> list[dict]:
        """
        Fetch events from Ticketmaster API with date filters and retry mechanism.
        Args:
            start_date (datetime): Start date and time for the event.
            end_date (datetime): End date and time for the event.
            page (int): Page number for deep paging.
        Returns:
            list[dict]: List of event objects if available; an empty list otherwise.
        """
        params = {
            "apikey": self.current_api_key,
            "startDateTime": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endDateTime": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "page": page,
            "size": self.api_size_limit,
            "locale": "en",
        }
        attempt = 1
        while attempt <= self.api_retry_limit:
            try:
                self.logger.info(
                    f"Attempt {attempt}: Fetching events from {start_date.strftime('%Y-%m-%dT%H:%M:%SZ')} "
                    f"to {end_date.strftime('%Y-%m-%dT%H:%M:%SZ')}, page {page}")

                response = requests.get(self.url, params=params, timeout=60)

                if response and response.status_code == 200:
                    self.logger.info(f"Response received with status code 200.")
                    result = response.json()

                    return result.get('_embedded', {}).get('events', [])
                
                elif response.status_code == 429:
                    self.logger.warning(f"Rate limit exceeded. Switching API key...")
                    self.__set_api_key()
                    params["apikey"] = self.current_api_key
                    continue

                else:
                    self.logger.warning(f"Attempt {attempt}: Failed to fetch events, status code {response.status_code}")
            
            except requests.exceptions.Timeout as e:
                self.logger.warning(f"Attempt {attempt}: Timeout occurred while fetching events: {e}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Attempt {attempt}: An error occurred while fetching events: {e}")
            
            attempt += 1
            t.sleep(self.api_retry_delay)

        self.logger.error(f"Failed to fetch data after {attempt - 1} attempts.")
        return []


    def __set_api_key(self, initial: bool = False) -> None:
        """
        Sets the best API key as current key.
        Returns:
            None
        """
        # Evaluate wait times for every key and store as (wait_time, key) tuples
        wait_times = []
        for key in self.api_keys:
            wait_time = self.__get_wait_time(key)
            wait_times.append((wait_time, key))

        # Find the (wait_time, key) with the smallest wait time
        wait_time, best_key = min(wait_times, key=lambda x: x[0])

        if not initial and wait_time > 0:
            self.logger.warning(f"Waiting for {wait_time} seconds until API reset...")
            t.sleep(wait_time)
            self.logger.info("API reset reached. Resuming...")
            
        self.current_api_key = best_key
    

    def __get_wait_time(self, key: str) -> int:
        """
        Get the wait time in seconds for an API key.
        Returns:
            int: Wait time in seconds.
        """
        params = {
            "apikey": key,
            "size": 1,
        }

        attempt = 1
        while attempt <= self.api_retry_limit:
            try:
                response = requests.get(self.url, params=params, timeout=60)
                if response.status_code == 429:
                    reset_time_ms = response.headers.get("Rate-Limit-Reset")
                    if reset_time_ms:
                        reset_timestamp = int(reset_time_ms) / 1000
                        reset_time = datetime.fromtimestamp(reset_timestamp, tz=timezone.utc)

                        return int((reset_time - datetime.now(timezone.utc)).total_seconds()) + 1
                else:
                    return 0
            
            except requests.exceptions.Timeout as e:
                self.logger.warning(f"Attempt {attempt}: Timeout occurred while fetching wait time: {e}")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Attempt {attempt}: An error occurred while fetching wait time: {e}")

            attempt += 1
            t.sleep(self.api_retry_delay)
        
        return 0
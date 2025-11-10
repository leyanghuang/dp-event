from datetime import datetime, timezone
from logging import Logger
from typing import Optional

from psycopg import Cursor
from psycopg.sql import SQL, Identifier


class SupabaseLog:
    def __init__(self, log_table: str, logger: Logger):
        """
        Initialize the SupabaseLog interface.
        Args:
            log_table (str): The name of the log table.
            logger (Logger): The Logger instance for logging.
        Returns:
            None
        """
        self.schema = "log"
        self.log_table = log_table
        self.logger = logger


    def save_job_start_time(self, cursor: Cursor, job_name: str) -> Optional[datetime]:
        """
        Saves the start time of a data pipeline job and returns the last processed data for stage jobs.
        Args:
            cursor (Cursor): The database connection cursor.
            job_name (str): The name of the job.
        Returns:
            last_processed_date (Optional[datetime]): The last processed date of the previous job.
        Raises:
            APIError: If the API call fails after the specified number of retries.
        """
        if "stage" in job_name or "ticketmaster" in job_name:
            last_processed_date = self.__get_last_processed_date(cursor, job_name)

            query = SQL("""
                INSERT INTO {}.{} (job_name, last_processed_date, started_at)
                VALUES (%s, %s, %s)
                RETURNING id;
            """).format(Identifier(self.schema), Identifier(self.log_table))
            values = (
                job_name,
                last_processed_date.strftime("%Y-%m-%d %H:%M:%S%z"),
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
            )

            try:
                response = cursor.execute(query, values).fetchone()
                if response:
                    self.log_id = response[0]
            except Exception as e:
                self.logger.warning(f"Error inserting last processed date: {e}")
                raise
            return last_processed_date
        else:
            query = SQL("""
                INSERT INTO {}.{} (job_name, started_at)
                VALUES (%s, %s)
                RETURNING id;
            """).format(Identifier(self.schema), Identifier(self.log_table))
            values = (
                job_name,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")
            )

            try:
                response = cursor.execute(query, values).fetchone()
                if response:
                    self.log_id = response[0]
            except Exception as e:
                self.logger.warning(f"Error inserting last processed date: {e}")
                raise
            
    def save_job_completed_time(self, cursor: Cursor, status: str = 'Success') -> None:
        """
        Saves the completion time of a data pipeline job.
        Args:
            cursor (Cursor): The database connection cursor.
            status (str): The status of the job. Defaults to 'Success'.
        Returns:
            None
        Raises:
            APIError: If the API call fails after the specified number of retries.
        """
        completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S%z")

        query = SQL("""
            UPDATE {}.{}
            SET completed_at = %s, status = %s
            WHERE id = %s;
        """).format(Identifier(self.schema), Identifier(self.log_table))

        values = (completed_at, status, self.log_id)

        try:
            cursor.execute(query, values)
        except Exception as e:
            self.logger.warning(f"Failed to update job completion time: {e}")
            raise

    def update_last_processed_date(self, cursor: Cursor, last_processed_date: Optional[datetime]) -> None:
        """
        Updates the last processed date in the log table for the current job.
        Args:
            cursor (Cursor): The database connection cursor.
            last_processed_date (Optional[datetime]): The last processed date to update. If None, uses the current time.
        Raises:
            APIError: If the API call fails after the specified number of retries.
        """
        if not last_processed_date:
            last_processed_date = datetime.now(timezone.utc)
        
        query = SQL("""
            UPDATE {}.{}
            SET last_processed_date = %s
            WHERE id = %s;
        """).format(Identifier(self.schema), Identifier(self.log_table))

        values = (
            last_processed_date.strftime("%Y-%m-%d %H:%M:%S%z"),
            self.log_id
        )

        try:
            cursor.execute(query, values)
        except Exception as e:
            self.logger.warning(f"Error updating last processed date: {e}")
            raise

    def __get_last_processed_date(self, cursor, job_name: str)-> datetime:
        """
        Retrieves the last processed date from the log table.
        This function will return the last processed date if the previous job was not successful.
        If the previous job was successful, then it will return None.
        Args:
            cursor (Cursor): The database connection cursor.
            job_name (str): The name of the job.
        Returns:
            last_processed_date (str): The last processed date of the previous job.
        Raises:
            APIError: If the API call fails after the specified number of retries.
        """
        query = SQL("""
            SELECT last_processed_date
            FROM {}.{}
            WHERE job_name = %s
            ORDER BY started_at DESC
            LIMIT 1;
        """).format(Identifier(self.schema), Identifier(self.log_table))

        values = (job_name,)
        try:
            response = cursor.execute(query, values).fetchone()
        
            if response and response[0]:
                return response[0]
        except Exception as e:
            self.logger.warning(f"Error fetching last processed date: {e}")
            raise
        return datetime(1900, 1, 1, 0, 0, 0)

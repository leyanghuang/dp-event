from datetime import datetime, date
import time
import psycopg


def convert_to_date(datetime_str: str) -> date:
    """
    Converts a datetime string to a date object
    """
    if datetime_str is None:
        return None
    
    dt_object = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
    return dt_object.date()


def get_bounding_datetime(input_date: date) -> tuple[str, str]:
    """
    Finds the starting and ending timestamp for the given date
    """
    start_of_day = datetime.combine(input_date, datetime.min.time())
    end_of_day = datetime.combine(input_date, datetime.max.time().replace(microsecond=0))
    
    return start_of_day.strftime("%Y-%m-%d %H:%M:%S"), end_of_day.strftime("%Y-%m-%d %H:%M:%S")


def retry_on_db_error(retries: int = 3, delay: int = 120):
    """
    Decorator to retry a function upon encountering a database error.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except (psycopg.DatabaseError, psycopg.OperationalError, psycopg.InterfaceError) as e:
                    attempt += 1
                    if attempt < retries:
                        time.sleep(delay)
                    else:
                        raise
        return wrapper
    return decorator
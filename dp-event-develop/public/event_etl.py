from logging import Logger
from datetime import timedelta

from public.common import (
    consolidate_events
)
from libs.database.database import Database

def public_event_job(
        database: Database,
        config: dict,
        logger: Logger
    ) -> None:
    """
    Runs the pipeline to fetch and process data and writes them to the Supabase table.
    Write a detailed description on what happens here.
    Args:
        database (Database): An instance of the Database interface.
        config (Dict): A dictionary containing the constants for the pipeline from the config file.
        logger (Logger): A logger instance.
    """
    try:
        logger.info("Starting public event ETL job...")
        database.save_job_start_time(config["job_name"])

        logger.info(f"Fetching date ranges...")
        start_date, end_date = database.get_stage_event_date_range()
        logger.info(f"Fetched start date: {start_date} and end date: {end_date}.")

        # Fetch existing venues from public schema
        logger.info(f"Fetching venues from public schema...")
        public_venues = database.get_public_venues()
        logger.info(f"Fetched {len(public_venues)} venues.")

        # Fetch existing artists from public schema
        logger.info(f"Fetching artists from public schema...")
        public_artists = database.get_public_artists()
        logger.info(f"Fetched {len(public_artists)} artists.")

        if not start_date or not end_date:
            logger.warning("No events found in stage schema.")
            database.save_job_completed_time("Success")
            logger.info("Public event ETL job completed.")
            return

        # Process and save events
        current_date = start_date
        while current_date <= end_date:
            # Fetch events from stage schema
            logger.info(f"Fetching events for date {current_date} from stage schema...")
            events = database.get_stage_events_on_date(current_date)
            logger.info(f"Fetched {len(events)} stage events.")

            if events:
                # Fetch existing events from public schema
                logger.info(f"Fetching events for date {current_date} from public schema...")
                public_events = database.get_public_events_on_date(current_date)
                logger.info(f"Fetched {len(public_events)} public events.")
            
                # Consolidate events
                logger.info(f"Consolidating {len(events)} events for date {current_date}...")
                events, event_artists = consolidate_events(events, public_events, public_venues, public_artists, logger)
                logger.info("Events consolidated.")
                
                if events:  
                    # Save events and event_artists to Supabase public schema
                    logger.info(f"Saving {len(events)} events and {len(event_artists)} maps for date {current_date} to public...")
                    database.save_public_events(events, event_artists)
                    logger.info("Events saved.")

            else:
                logger.info(f"No events to save for date {current_date}.")

            current_date += timedelta(days=1)

        database.save_job_completed_time("Success")
        logger.info("Public event ETL job completed.")

    except KeyboardInterrupt:
        logger.critical("Script interrupted and stopped by user.")
        database.save_job_completed_time("Interrupted")

    except Exception:
        logger.error("Unhandled exception", exc_info=True)
        database.save_job_completed_time("Failed")
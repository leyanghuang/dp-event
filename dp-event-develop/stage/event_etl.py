from logging import Logger

from stage.common import (
    process_seatgeek_events,
    process_ticketmaster_events
)
from libs.database.database import Database

def stage_event_job(
        database: Database,
        config: dict,
        logger: Logger
    ) -> None:
    """
    Runs the pipeline to fetch and merge raw events from Supabase and writes them to the staging table.
    This function fetches the last processed date from the log table, fetches the raw SeatGeek and Ticketmaster events
    that occurred after the last processed date, and merges them.
    It logs the progress at every step and saves the completed time with a status of "Failed" if an exception occurs.
    Args:
        database (Database): An instance of the Database interface.
        config (Dict): A dictionary containing the constants for the pipeline from the config file.
        logger (Logger): A logger instance.
    """
    try:
        logger.info("Starting stage event ETL job...")
        last_processed_date = database.save_job_start_time(config["job_name"])
        if not last_processed_date:
            raise ValueError("Expected last_processed_date to be of type datetime, but received NoneType.")
        logger.info(f"Fetched last_processed_date: {last_processed_date}.")

        # Process and save SeatGeek events
        # Fetch raw SeatGeek events from table
        logger.info(f"Fetching raw SeatGeek events...")
        seatgeek_events = database.get_raw_seatgeek_events(last_processed_date)
        logger.info(f"Fetched {len(seatgeek_events)} raw SeatGeek events.")
        
        if seatgeek_events:
            # Process SeatGeek events
            logger.info(f"Processing {len(seatgeek_events)} SeatGeek events ...")
            events = process_seatgeek_events(seatgeek_events)
            logger.info("Events processed.")
            
            if events:
                # Save SeatGeek events to Supabase stage schema
                logger.info(f"Saving {len(events)} SeatGeek events to stage schema...")
                database.save_stage_events(events)
                logger.info("Events saved.")

        else:
            logger.info("No SeatGeek events to save.")
                 
        # Process and save Ticketmaster events
        # Fetch raw Ticketmaster events from table
        logger.info(f"Fetching raw Ticketmaster events ...")
        ticketmaster_events = database.get_raw_ticketmaster_events(last_processed_date)
        logger.info(f"Fetched {len(ticketmaster_events)} raw Ticketmaster events.")
        
        if ticketmaster_events:
            # Process Ticketmaster events
            logger.info(f"Processing {len(ticketmaster_events)} Ticketmaster events ...")
            events = process_ticketmaster_events(ticketmaster_events)
            logger.info("Events processed.")
            
            if events:
                # Save Ticketmaster events to Supabase stage schema
                logger.info(f"Saving {len(events)} Ticketmaster events to stage schema...")
                database.save_stage_events(events)
                logger.info("Events saved.")

        else:
            logger.info("No Ticketmaster events to save.")

        database.update_last_processed_date()
        database.save_job_completed_time("Success")
        logger.info("Stage event ETL job completed.")

    except KeyboardInterrupt:
        logger.critical("Script interrupted and stopped by user.")
        database.save_job_completed_time("Interrupted")

    except Exception:
        logger.error("Unhandled exception", exc_info=True)
        database.save_job_completed_time("Failed")
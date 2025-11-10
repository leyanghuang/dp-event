from logging import Logger

from stage.common import (
    process_seatgeek_venues,
    process_ticketmaster_venues
)
from libs.database.database import Database

def stage_venue_job(
        database: Database,
        config: dict,
        logger: Logger
    ) -> None:
    """
    Runs the pipeline to fetch and merge raw venues from Supabase and writes them to the staging table.
    This function fetches the last processed date from the log table, fetches the raw SeatGeek and Ticketmaster venues
    that occurred after the last processed date, and merges them.
    It logs the progress at every step and saves the completed time with a status of "Failed" if an exception occurs.
    Args:
        database (Database): An instance of the Database interface.
        config (Dict): A dictionary containing the constants for the pipeline from the config file.
        logger (Logger): A logger instance.
    """
    try:
        logger.info("Starting stage venue ETL job...")
        last_processed_date = database.save_job_start_time(config["job_name"])
        if not last_processed_date:
            raise ValueError("Expected last_processed_date to be of type datetime, but received NoneType.")
        logger.info(f"Fetched last_processed_date: {last_processed_date}.")

        # Process and save SeatGeek venues
        # Fetch raw SeatGeek venues from table
        logger.info(f"Fetching raw SeatGeek venues...")
        seatgeek_venues = database.get_raw_seatgeek_venues(last_processed_date)
        logger.info(f"Fetched {len(seatgeek_venues)} raw SeatGeek venues.")

        if seatgeek_venues:
            # Process Seatgeek venues
            logger.info(f"Processing {len(seatgeek_venues)} SeatGeek venues ...")
            processed_seatgeek_venues = process_seatgeek_venues(seatgeek_venues)
            logger.info("Venues processed.")

            if processed_seatgeek_venues:
                # Save SeatGeek venues to Supabase stage table
                logger.info(f"Saving {len(processed_seatgeek_venues)} SeatGeek venues to stage schema...")
                database.save_stage_venues(processed_seatgeek_venues)
                logger.info(f"Venues saved.")

        else:
            logger.info("No SeatGeek venues to save.")
        
        # Process and save Ticketmaster venues
        # Fetch raw Ticketmaster venues from table
        logger.info(f"Fetching raw Ticketmaster venues ...")
        ticketmaster_venues = database.get_raw_ticketmaster_venues(last_processed_date)
        logger.info(f"Fetched {len(ticketmaster_venues)} raw Ticketmaster venues.")

        if ticketmaster_venues:
            # Process Ticketmaster venues
            logger.info(f"Processing {len(ticketmaster_venues)} Ticketmaster venues ...")
            processed_ticketmaster_venues = process_ticketmaster_venues(ticketmaster_venues)
            logger.info("Venues processed.")

            if processed_ticketmaster_venues:
                # Save Ticketmaster data to Supabase stage table
                logger.info(f"Saving {len(processed_ticketmaster_venues)} Ticketmaster venues to stage schema...")
                database.save_stage_venues(processed_ticketmaster_venues)
                logger.info(f"Venues saved.")
            
        else:
            logger.info("No Ticketmaster venues to save.")

        # Update last_processed_date in log table
        database.update_last_processed_date()
        database.save_job_completed_time("Success")
        logger.info("Stage venue ETL job completed.")

    except KeyboardInterrupt:
        logger.critical("Script interrupted and stopped by user.")
        database.save_job_completed_time("Interrupted")

    except Exception:
        logger.error("Unhandled exception", exc_info=True)
        database.save_job_completed_time("Failed")
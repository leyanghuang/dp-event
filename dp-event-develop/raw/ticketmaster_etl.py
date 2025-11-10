from logging import Logger
from datetime import datetime, timedelta, timezone

from raw.common import (
    process_ticketmaster_events,
    process_ticketmaster_music_performers,
    process_ticketmaster_venues,
    get_data_date,
    to_datetime_utc,
    remove_duplicates_by_id
)
from libs.clients.ticketmaster_client import TicketmasterClient
from libs.database.database import Database


def raw_ticketmaster_job(
        ticketmaster_client: TicketmasterClient,
        database: Database,
        config: dict,
        logger: Logger
    ) -> None:
    """
    Runs the pipeline to fetch and process data and writes them to the Supabase table.
    Write a detailed description on what happens here.
    Args:
        ticketmaster_client (TicketmasterClient): An instance of the TicketmasterClient interface.
        database (Database): An instance of the Database interface.
        config (Dict): A dictionary containing the constants for the pipeline from the config file.
        logger (Logger): A logger instance.
    """
    try:
        logger.info('Starting Ticketmaster ETL job...')
        last_processed_date = database.save_job_start_time(config["job_name"])
        if not last_processed_date:
            raise ValueError("Expected last_processed_date to be of type datetime, but received NoneType.")
        logger.info(f"Fetched last_processed_date: {last_processed_date}.")

        # Loop every day
        data_date = get_data_date(last_processed_date)
        while (data_date - datetime.now(timezone.utc).date()).days <= 365:
            logger.info(f'Fetching Ticketmaster data for {data_date}...')
            events = ticketmaster_client.fetch_events_for_day(data_date)
            logger.info(f'Ticketmaster data fetched for {data_date}.')

            if events:
                logger.info(f"Processing Events for {data_date}...")
                processed_events = process_ticketmaster_events(events)
                logger.info(f"Events processed for {data_date}.")

                # Making event list unique based on ID
                processed_events = remove_duplicates_by_id(processed_events)

                # Save events to Supabase if exists
                if processed_events:
                    logger.info(f"Saving Events for {data_date}...")
                    database.save_raw_ticketmaster_events(processed_events)
                    logger.info(f"{len(processed_events)} Events saved to raw for {data_date}.")

                processed_venues = []
                processed_attractions = []
                for event in processed_events:
                    processed_venues.extend(process_ticketmaster_venues(event.get('venues', [])))

                    # If event is of type music, also process and save attractions separately.
                    if event.get('type', 'unknown') == 'music':
                        processed_attractions.extend(process_ticketmaster_music_performers(event.get('attractions', [])))

                # Making venue list unique based on ID
                processed_venues = remove_duplicates_by_id(processed_venues)

                # Save venues to Supabase if exists
                if processed_venues:
                    logger.info(f"Saving Venues for {data_date}...")
                    database.save_raw_ticketmaster_venues(processed_venues)
                    logger.info(f"{len(processed_venues)} Venues saved to raw for {data_date}.")
                
                # Making attraction list unique based on ID
                processed_attractions = remove_duplicates_by_id(processed_attractions)

                # Save attractions to Supabase if exists
                if processed_attractions:
                    logger.info(f"Saving Attractions for {data_date}...")
                    database.save_raw_ticketmaster_attractions(processed_attractions)
                    logger.info(f"{len(processed_attractions)} Attractions saved to raw for {data_date}.")

            # Increase data_date by 1 day
            database.update_last_processed_date(to_datetime_utc(data_date))
            data_date += timedelta(days=1)

        logger.info(f"Completed fetching Ticketmaster data.")
        database.save_job_completed_time("Success")
        logger.info("Ticketmaster ETL job completed.")

    except KeyboardInterrupt:
        logger.warning("Script interrupted and stopped by user.")
        database.save_job_completed_time("Interrupted")

    except Exception:
        logger.error("Unhandled exception", exc_info=True)
        database.save_job_completed_time("Failed")
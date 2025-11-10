from logging import Logger
from datetime import datetime, timedelta, timezone

from raw.common import (
    process_seatgeek_events,
    process_seatgeek_performer,
    process_seatgeek_venue,
    remove_duplicates_by_id
)
from libs.clients.seatgeek_client import SeatgeekClient
from libs.database.database import Database


def raw_seatgeek_job(
        seatgeek_client: SeatgeekClient,
        database: Database,
        config: dict,
        logger: Logger
    ) -> None:
    """
    Fetches SeatGeek event data from SeatGeek API, processes them,
    and writes them to the Supabase raw table.
    Args:
        seatgeek_client (SeatgeekClient): An instance of the SeatgeekClient interface.
        database (Database): An instance of the Database interface.
        config (Dict): A dictionary containing the constants for the job from the config file.
        logger (Logger): A logger instance.
    """
    # This is how to load the constants from the config
    YEARS_TO_FETCH = config["years_to_fetch"]

    try:
        logger.info("Starting SeatGeek ETL job...")
        database.save_job_start_time(config["job_name"])

        fetched_performers = set()

        # Loop every day
        data_date = datetime.now(timezone.utc).date()
        while (data_date - datetime.now(timezone.utc).date()).days <= (365 * YEARS_TO_FETCH):
            logger.info(f'Fetching Seatgeek events for {data_date}...')
            events = seatgeek_client.fetch_events_for_day(data_date)
            logger.info(f'{len(events)} Seatgeek events fetched for {data_date}.')

            if events:
                logger.info(f"Processing Events for {data_date}...")
                processed_events = process_seatgeek_events(events)
                logger.info(f"Events processed for {data_date}.")

                # Making event list unique based on ID
                processed_events = remove_duplicates_by_id(processed_events)

                # Save events to Supabase if exists
                if processed_events:
                    logger.info(f"Saving Events for {data_date}...")
                    database.save_raw_seatgeek_events(processed_events)
                    logger.info(f"{len(processed_events)} Events saved to raw for {data_date}.")

                processed_venues = []
                processed_performers = []
                for event in events:
                    processed_venues.append(process_seatgeek_venue(event.get('venue', {})))

                    # If event is of type music, also process and save performers separately.
                    if event.get("type", "").lower() in ["band", "concert", "music_festival"]:
                        for performer in event.get("performers", []):
                            performer_id = performer.get("id", None)
                            if performer_id and performer_id not in fetched_performers:
                                performer = seatgeek_client.fetch_performer(performer_id)

                                if performer:
                                    processed_performers.append(process_seatgeek_performer(performer))
                                    fetched_performers.add(performer_id)

                # Making venue list unique based on ID
                processed_venues = remove_duplicates_by_id(processed_venues)

                # Save venues to Supabase if exists
                if processed_venues:
                    logger.info(f"Saving Venues for {data_date}...")
                    database.save_raw_seatgeek_venues(processed_venues)
                    logger.info(f"{len(processed_venues)} Venues saved to raw for {data_date}.")
                
                # Making attraction list unique based on ID
                processed_performers = remove_duplicates_by_id(processed_performers)

                # Save attractions to Supabase if exists
                if processed_performers:
                    logger.info(f"Saving Performers for {data_date}...")
                    database.save_raw_seatgeek_performers(processed_performers)
                    logger.info(f"{len(processed_performers)} Performers saved to raw for {data_date}.")

            # Increase data_date by 1 day
            data_date += timedelta(days=1)

        logger.info(f"Completed fetching for {YEARS_TO_FETCH} year/s.")
        database.save_job_completed_time("Success")
        logger.info("SeatGeek ETL job completed.")

    except KeyboardInterrupt:
        logger.warning("Script interrupted and stopped by user.")
        database.save_job_completed_time("Interrupted")

    except Exception:
        logger.error("Unhandled exception", exc_info=True)
        database.save_job_completed_time("Failed")
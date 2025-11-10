from logging import Logger

from stage.common import (
    process_seatgeek_artists,
    process_ticketmaster_artists
)
from libs.database.database import Database
from libs.clients.spotify_client import SpotifyClient

def stage_artist_job(
        spotify_client: SpotifyClient,
        database: Database,
        config: dict,
        logger: Logger
    ) -> None:
    """
    Runs the job to fetch artist data from raw, then process and save them to the stage schema.
    The job only fetches and processes the artist after the last processed date.
    It keeps the SeatGeek and Ticketmaster artists separate.
    Args:
        spotify_client (SpotifyClient): An instance of the SpotifyClient.
        database (Database): An instance of the Database interface.
        config (Dict): A dictionary containing the constants for the pipeline from the config file.
        logger (Logger): A logger instance.
    """
    try:
        logger.info("Starting stage artist ETL job...")
        last_processed_date = database.save_job_start_time(config["job_name"])
        if not last_processed_date:
            raise ValueError("Expected last_processed_date to be of type datetime, but received NoneType.")
        logger.info(f"Fetched last_processed_date: {last_processed_date}.")

        # Process and save SeatGeek artists
        # Fetch raw SeatGeek artists from table
        logger.info(f"Fetching raw SeatGeek artists ...")
        seatgeek_artists = database.get_raw_seatgeek_artists(last_processed_date)
        logger.info(f"Fetched {len(seatgeek_artists)} raw SeatGeek artists.")

        if seatgeek_artists:
            # Process Seatgeek artists
            logger.info(f"Processing SeatGeek artists...")
            processed_seatgeek_artists = process_seatgeek_artists(seatgeek_artists)
            logger.info("SeatGeek artists processed.")

            # Append missing names
            logger.info(f"Appending missing names from Spotify...")
            updated_artists = spotify_client.append_missing_names(processed_seatgeek_artists)

            # Append missing spotify ids
            logger.info(f"Appending missing spotify_ids from Spotify...")
            artists = spotify_client.append_spotify_ids(updated_artists)

            if artists:
                # Save SeatGeek artists to Supabase stage table
                logger.info(f"Saving {len(artists)} SeatGeek artists to stage schema...")
                database.save_stage_artists(artists)
                logger.info(f"Saved {len(artists)} SeatGeek artists.")

        else:
            logger.info("No SeatGeek artists to save")

        # Process and save Ticketmaster artists
        # Fetch raw Ticketmaster artists from table
        logger.info(f"Fetching raw Ticketmaster artists ...")
        ticketmaster_artists = database.get_raw_ticketmaster_artists(last_processed_date)
        logger.info(f"Fetched {len(ticketmaster_artists)} raw Ticketmaster artists.")

        if ticketmaster_artists:
            # Process Ticketmaster artists
            logger.info(f"Processing Ticketmaster artists...")
            processed_ticketmaster_artists = process_ticketmaster_artists(ticketmaster_artists)
            logger.info("Ticketmaster artists processed.")

            # Append missing names
            logger.info(f"Appending missing names from Spotify...")
            updated_artists = spotify_client.append_missing_names(processed_ticketmaster_artists)

            # Append missing spotify ids
            logger.info(f"Appending missing spotify_ids from Spotify...")
            artists = spotify_client.append_spotify_ids(updated_artists)

            if artists:
                # Save Ticketmaster data to Supabase stage table
                logger.info(f"Saving {len(artists)} Ticketmaster artists to stage schema...")
                database.save_stage_artists(artists)
                logger.info(f"Saved {len(artists)} Ticketmaster artists.")
            
        else:
            logger.info("No Ticketmaster artists to save.")
        
        # Update last_processed_date in log table
        database.update_last_processed_date()
        database.save_job_completed_time("Success")
        logger.info("Stage artist ETL job completed.")

    except KeyboardInterrupt:
        logger.critical("Script interrupted and stopped by user.")
        database.save_job_completed_time("Interrupted")

    except Exception:
        logger.error("Unhandled exception", exc_info=True)
        database.save_job_completed_time("Failed")
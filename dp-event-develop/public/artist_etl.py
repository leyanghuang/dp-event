from logging import Logger

from public.common import (
    consolidate_artists
)
from libs.database.database import Database

def public_artist_job(
        database: Database,
        config: dict,
        logger: Logger
    ) -> None:
    """
    Runs the pipeline to fetch artist data from stage schema, process and write them to the public table.
    Args:
        database (Database): An instance of the Database interface.
        config (Dict): A dictionary containing the constants for the pipeline from the config file.
        logger (Logger): A logger instance.
    """
    # Load the constants from the config
    MATCH_THRESHOLD = config["match_threshold"]

    try:
        logger.info("Starting public artist ETL job...")
        database.save_job_start_time(config["job_name"])

        # Fetch artists from stage schema
        logger.info(f"Fetching artists from stage schema...")
        artists = database.get_stage_artists()
        logger.info(f"Fetched {len(artists)} stage artists.")

        # Fetch artists from public schema
        logger.info(f"Fetching artists from public schema...")
        public_artists = database.get_public_artists()
        logger.info(f"Fetched {len(public_artists)} public artists.")

        # Process and save artists
        if artists:
            # Consolidate artists
            logger.info(f"Consolidating {len(artists)} artists...")
            artists = consolidate_artists(artists, public_artists, MATCH_THRESHOLD, logger)
            logger.info("Artists consolidated.")

            if artists:
                # Save artists to Supabase public schema
                logger.info(f"Saving {len(artists)} artists to public schema...")
                database.save_public_artists(artists)
                logger.info("Artists saved.")

        else:
            logger.info("No artists to save.")

        database.save_job_completed_time("Success")
        logger.info("Public artist ETL job completed.")

    except KeyboardInterrupt:
        logger.critical("Script interrupted and stopped by user.")
        database.save_job_completed_time("Interrupted")

    except Exception:
        logger.error("Unhandled exception", exc_info=True)
        database.save_job_completed_time("Failed")
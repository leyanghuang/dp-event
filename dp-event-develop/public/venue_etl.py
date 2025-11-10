from logging import Logger
from public.common import (
    process_venues,
    compare_existing_venues,
    map_venue_dma
)
from libs.database.database import Database

def public_venue_job(
        database: Database,
        config: dict,
        logger: Logger
    ) -> None:
    """
    Runs the pipeline to fetch venue data from stage schema, process and write them to the public table.
    Args:
        database (Database): An instance of the Database interface.
        config (Dict): A dictionary containing the constants for the pipeline from the config file.
        logger (Logger): A logger instance.
    """
    name_threshold = config["name_threshold"]
    address_threshold = config["address_threshold"]
    distance_threshold = config["distance_threshold"]

    try:
        logger.info("Starting public venue ETL job...")
        database.save_job_start_time(config["job_name"])
        
        # Fetch data
        logger.info(f"Fetching venues from stage schema...")
        venues = database.get_stage_venues()
        logger.info(f"Fetched {len(venues)} venues.")

        # Fetch existing venues from public schema
        logger.info(f"Fetching existing venues from public schema...")
        public_venues = database.get_public_venues()
        logger.info(f"Fetched {len(public_venues)} existing venues.")

        # Fetch DMAs with markets from public schema
        logger.info(f"Fetching DMAs with markets from public schema...")
        dmas = database.get_public_dmas()
        logger.info(f"Fetched {len(dmas)} DMAs.")

        # Fetch venues with DMAs mapped
        logger.info(f"Fetching venues that have DMAs mapped...")
        mapped_venues = database.get_matched_public_venues()
        logger.info(f"Fetched {len(mapped_venues)} mapped venues.")
        
        if venues: 
            # Consolidate Venues
            logger.info(f"Processing venues...")
            venues = process_venues(venues, name_threshold, address_threshold)
            logger.info(f"Processed {len(venues)} venues.")

            # Compare existing and new data 
            logger.info(f"Comparing with existing venues...")
            consolidated_venues = compare_existing_venues(public_venues, venues,
                                                          name_threshold, address_threshold)

            if consolidated_venues:
                # Map venues to DMAs
                logger.info(f"Mapping with DMAs...")
                venue_dma_map = map_venue_dma(consolidated_venues, dmas, mapped_venues, distance_threshold)
                logger.info(f"Venues mapped to DMAs.")
                
                # Save venue data to Supabase public schema
                logger.info(f"Saving {len(consolidated_venues)} venues and {len(venue_dma_map)} maps to public...")
                database.save_public_venues(consolidated_venues, venue_dma_map)
                logger.info("Venues saved.")

        else:
            logger.info("No venues to save.")

        database.save_job_completed_time("Success")
        logger.info("Public venue ETL job completed.")

    except KeyboardInterrupt:
        logger.critical("Script interrupted and stopped by user.")
        database.save_job_completed_time("Interrupted")

    except Exception:
        logger.error("Unhandled exception", exc_info=True)
        database.save_job_completed_time("Failed")
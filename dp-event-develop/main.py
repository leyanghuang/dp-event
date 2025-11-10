import os
import sys
from logging import Logger, StreamHandler, Formatter, INFO, ERROR

from config.config_loader import load_config
from libs.clients.seatgeek_client import SeatgeekClient
from libs.clients.ticketmaster_client import TicketmasterClient
from libs.clients.spotify_client import SpotifyClient
from libs.database.supabase import SupabaseDatabase
from libs.logging.slack_log_handler import SlackLogHandler
from libs.logging.slack import Slack
from raw.seatgeek_etl import raw_seatgeek_job
from raw.ticketmaster_etl import raw_ticketmaster_job
from stage.artist_etl import stage_artist_job
from stage.venue_etl import stage_venue_job
from stage.event_etl import stage_event_job
from public.artist_etl import public_artist_job
from public.venue_etl import public_venue_job
from public.event_etl import public_event_job


# Load environment variables from .env file in dev environment
is_dev = len(sys.argv) > 1 and sys.argv[1] == '-dev'
if is_dev:
    from dotenv import load_dotenv
    load_dotenv()

# Load credentials from environment variables
# Supabase
SUPABASE_USER = os.getenv("SUPABASE_USER", "")
SUPABASE_PASSWORD = os.getenv("SUPABASE_PASSWORD", "")
SUPABASE_HOST = os.getenv("SUPABASE_HOST", "")
SUPABASE_PORT = os.getenv("SUPABASE_PORT", "")
SUPABASE_DBNAME = os.getenv("SUPABASE_DBNAME", "")


# SeatGeek
SEATGEEK_CLIENT_ID = os.getenv("SEATGEEK_CLIENT_ID", "")
SEATGEEK_CLIENT_SECRET = os.getenv("SEATGEEK_CLIENT_SECRET", "")

# Ticketmaster
TICKETMASTER_KEYS = os.getenv("TICKETMASTER_API_KEYS", "").split(",")
TICKETMASTER_KEYS = [key.strip() for key in TICKETMASTER_KEYS]

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

# Load configuration
try:
    if is_dev:
        config = load_config("dev")
    else:
        config = load_config("prod")
except Exception as e:
    sys.exit(1)

if not config:
    sys.exit(1)  # Exit if config is not loaded? TODO: Handle gracefully

try:
    tables = config["database_tables"]

    read_batch_size = config["constants"]["read_batch_size"]
    write_batch_size = config["constants"]["write_batch_size"]

    raw_seatgeek_config = config["jobs"]["raw_seatgeek"]
    raw_ticketmaster_config = config["jobs"]["raw_ticketmaster"]

    stage_artist_config = config["jobs"]["stage_artist"]
    stage_venue_config = config["jobs"]["stage_venue"]
    stage_event_config = config["jobs"]["stage_event"]

    public_artist_config = config["jobs"]["public_artist"]
    public_venue_config = config["jobs"]["public_venue"]
    public_event_config = config["jobs"]["public_event"]

except KeyError as e:
    sys.exit(1)  # Exit if configurations are not found.


# Configure custom logging to Slack
if is_dev:
    logger = Logger("Console-logger")
    logger.setLevel(INFO)
    console_handler = StreamHandler()
    console_handler.setLevel(INFO)
    formatter = Formatter("[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s Line %(lineno)d] - %(message)s")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
else:
    logger = Logger("Slack-logger")
    logger.setLevel(INFO)
    SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK", "")
    slack = Slack(SLACK_WEBHOOK)
    logger.addHandler(SlackLogHandler(slack, ERROR))

# Initialize API clients and database interfaces
seatgeek_client = SeatgeekClient(raw_seatgeek_config.get("base_api_url"),
                                 SEATGEEK_CLIENT_ID, SEATGEEK_CLIENT_SECRET,
                                 raw_seatgeek_config.get("api_size_limit"),
                                 raw_seatgeek_config.get("api_retry_limit"),
                                 raw_seatgeek_config.get("api_retry_delay"), logger)
ticketmaster_client = TicketmasterClient(raw_ticketmaster_config.get("base_api_url"), TICKETMASTER_KEYS,
                                         raw_ticketmaster_config.get("api_size_limit"),
                                         raw_ticketmaster_config.get("api_retry_limit"),
                                         raw_ticketmaster_config.get("api_retry_delay"), logger)
spotify_client = SpotifyClient(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, logger)
database = SupabaseDatabase(tables, SUPABASE_USER, SUPABASE_PASSWORD, SUPABASE_HOST,
                            SUPABASE_PORT, SUPABASE_DBNAME, read_batch_size, write_batch_size, logger)

def main():
    """
    Main function to run the pipeline in repeat.
    """
    while True:
        logger.info("Pipeline started.")
        
        raw_seatgeek_job(seatgeek_client, database, raw_seatgeek_config, logger)
        raw_ticketmaster_job(ticketmaster_client, database, raw_ticketmaster_config, logger)

        stage_artist_job(spotify_client, database, stage_artist_config, logger)
        stage_venue_job(database, stage_venue_config, logger)
        stage_event_job(database, stage_event_config, logger)

        public_artist_job(database, public_artist_config, logger)
        public_venue_job(database, public_venue_config, logger)
        public_event_job(database, public_event_config, logger)

        logger.info("Pipeline executed.")

        if is_dev:
            break

if __name__ == "__main__":
    main()
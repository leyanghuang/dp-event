# Data Pipeline Event
This pipeline aims to fetches event, artist, and venue data from different sources, processes and consolidate them and save them to their respective tables.

# Overview

The pipeline performs the following steps:

1. **Initialization**: Sets up configurations and logging.
2. **Raw**: 
   - Fetches venues, events & artists using Seatgeek & Ticketmaster API`s.
   - Processes them and save them in **raw** schema.
3. **Stage**:
   - Fetches venues, events & artists from **raw** schema.
   - Append missing names and spotify ids to artists using Spotipy (Spotify client).
   - Processes them and save them in **stage** schema. 
4. **Public**:
   - Fetches venues, events & artists from **stage** schema and compare with existing data from **public** schema.
   - Map venues with DMAs.
   - Consolidate and save them in **public** schema. 
5. **Logging**:
   - Tracks pipeline execution, including start time, progress, and completion status.
   - Handles exceptions to log failures and interruptions.

## Configuration

The pipeline relies on a configuration file or dictionary to control its operation. Key configurations include:

- **`years_to_fetch`**: Number of years of data to retrieve.
- **`api_size_limit`**: Maximum number of records fetched per API request.
- **`api_retry_limit`**: Maximum number of retry attempts in case of API failure.
- **`api_retry_delay`**: Delay (in seconds) between retry attempts.
- **`base_api_url`**: Endpoint for fetching data from Ticketmaster/Seatgeek.

- **`name_threshold_upper`**: Upper threshold for venue name matching.
- **`name_threshold_lower`**: Lower threshold for venue name matching.
- **`coord_threshold`**: Acceptable proximity for venue location matching.
- **`distance_threshold`**: Maximum allowable distance for venue location matching.

- **`event_threshold`**: Similarity threshold for event matching.
- **`artist_threshold`**: Similarity threshold for artist association in events.
- **`venue_threshold`**: Similarity threshold for venue association in events.

- **`database_tables`**:  Specifies the destination/source tables for the data.

## Usage

1. **Dependencies**: Requirements.txt file contains all the required dependencies.
   
2. **Environment Variables**: Following variables are required in Repository Secrets for the GitHub Actions to work:
   
      DOCKER_CONTAINER_NAME

      DOCKER_IMAGE_PATH

      DOCKER_IMAGE_TAG

      DOCKER_PASSWORD

      DOCKER_USERNAME

      HOST_IP

      SLACK_WEBHOOK

      SSH_PASSWORD

      SSH_USERNAME
   
      SUPABASE_USER
   
      SUPABASE_PASSWORD
   
      SUPABASE_HOST
   
      SUPABASE_PORT
   
      SUPABASE_DBNAME
   
      SEATGEEK_CLIENT_ID
   
      SEATGEEK_CLIENT_SECRET
   
      TICKETMASTER_API_KEYS
   
      SPOTIFY_CLIENT_IDS
   
      SPOTIFY_CLIENT_SECRET

      ZEROTIER_CENTRAL_TOKEN

      ZEROTIER_NETWORK_ID

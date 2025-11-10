import time
from logging import Logger
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from ratelimit import limits, sleep_and_retry


class SpotifyClient:
    def __init__(self, client_id: str, client_secret: str, logger: Logger):
        self.client_id = client_id
        self.client_secret = client_secret
        self.logger = logger
        self.spotify_client = self.__get_spotify_client()


    def __get_spotify_client(self):
        """Create and return a Spotify client using the current client credentials."""
        client_id = self.client_id
        client_secret = self.client_secret
        client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=client_credentials_manager,requests_timeout=30,retries=3)
        time.sleep(3)  # Prevent aggressive requests on initialization
        return sp


    def append_spotify_ids(self, artists_data):
        updated_artists = []
        for artist in artists_data:
            if not artist['spotify_id'] and artist['name']:
                artist_name = artist['name']
                try:
                    results = self.__search_artist(artist_name)
                    if not isinstance(results, dict):
                        raise ValueError("Expected results to be a dict")
                    items = results['artists']['items']
                    spotify_id = None
                    for item in items:
                        if item['name'].lower() == artist_name.lower():  # Case-insensitive match
                            spotify_id = item['id']
                            break  # Stop at the first exact match           
                    artist['spotify_id'] = spotify_id if spotify_id else None

                    if not spotify_id:
                        self.logger.info(f"No exact match found for artist: {artist_name}")

                except Exception as e:
                    self.logger.warning(f"Unexpected error for artist: {artist_name}. Error: {e}")
                    artist['spotify_id'] = None

            updated_artists.append(artist)       
        return updated_artists


    def append_missing_names(self, artists_data):
        updated_artists = []
        for artist in artists_data:
            if artist['spotify_id'] and not artist['name']:
                spotify_id = artist['spotify_id']
                try:
                    result = self.__get_artist_by_id(spotify_id)
                    if not isinstance(result, dict):
                        raise ValueError("Expected result to be a dict")
                    artist_name = result['name']
                    artist['name'] = artist_name if artist_name else None

                    if not artist_name:
                        self.logger.info(f"Could not retrieve name for Spotify ID: {spotify_id}")

                except Exception as e:
                    self.logger.warning(f"Unexpected error for Spotify ID: {spotify_id}. Error: {e}")
                    artist['name'] = None

            updated_artists.append(artist)
        return updated_artists
    

    @sleep_and_retry
    @limits(calls=1, period=1)
    def __search_artist(self, artist_name: str):
        """Search for an artist on Spotify by name."""
        return self.spotify_client.search(q=artist_name, type='artist', limit=5)


    @sleep_and_retry
    @limits(calls=1, period=1)
    def __get_artist_by_id(self, spotify_id: str):
        """Retrieve artist details from Spotify using the Spotify ID."""
        return self.spotify_client.artist(spotify_id)
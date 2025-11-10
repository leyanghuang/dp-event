import json
from typing import Optional


def process_seatgeek_artists(
    seatgeek_artists: list[dict]
) -> list[dict]:
    """
    Process artists from Seatgeek.

    :param seatgeek_artists: List of dictionaries containing Ticketmaster data.
    :return: List of dictionaries containing processed data.
    """
    processed_seatgeek_artists = []

    # Add Ticketmaster data
    for sg_entry in seatgeek_artists:
        processed_seatgeek_artists.append({
            'name': sg_entry.get('name'),
            'spotify_id': sg_entry.get('spotify_id'),
            'image': sg_entry.get('image'),
            'source': 'seatgeek',
            'source_id': sg_entry.get('id')
        })

    return processed_seatgeek_artists


def process_ticketmaster_artists(
    ticketmaster_artists: list[dict]
) -> list[dict]:
    """
    Process artists from Ticketmaster.

    :param ticketmaster_artists: List of dictionaries containing Ticketmaster data.
    :return: List of dictionaries containing processed data.
    """
    processed_ticketmaster_artists = []

    # Add Ticketmaster data
    for tm_entry in ticketmaster_artists:
        processed_ticketmaster_artists.append({
            'name': tm_entry.get('name'),
            'spotify_id': tm_entry.get('spotify_id'),
            'image': __get_best_image_url(tm_entry),
            'source': 'ticketmaster',
            'source_id': tm_entry.get('id')
        })

    return processed_ticketmaster_artists


def process_seatgeek_venues(seatgeek_venues: list[dict]) -> list[dict]:
    processed_venues = []

    for venue in seatgeek_venues:
        processed_venues.append({
            "name": venue.get("name", None),
            "address": venue.get("address", None),
            "city": venue.get("city", None),
            "state": venue.get("state", None),
            "country": venue.get("country", None),
            "postal_code": venue.get("postal_code", None),
            "timezone": venue.get("timezone", None),
            "latitude": str(venue.get("location", {}).get("lat", None)),
            "longitude": str(venue.get("location", {}).get("lon", None)),
            "capacity": venue.get("capacity", None),
            "source": "seatgeek",
            "source_id": venue.get("id")
        })

    return processed_venues


def process_ticketmaster_venues(ticketmaster_venues: list[dict]) -> list[dict]:
    processed_venues = []

    for venue in ticketmaster_venues:
        processed_venues.append({
            "name": venue.get("name", None),
            "address": venue.get("address", None),
            "city": venue.get("city", None),
            "state": venue.get("state", None),
            "country": venue.get("country", None),
            "postal_code": venue.get("postal_code", None),
            "timezone": venue.get("timezone", None),
            "latitude": venue.get("location", {}).get("latitude", None),
            "longitude": venue.get("location", {}).get("longitude", None),
            "capacity": 0,
            "source": "ticketmaster",
            "source_id": venue.get("id")
        })

    return processed_venues


def process_seatgeek_events(events: list[dict]) -> list[dict]:
    processed_events = []
    for event in events:
        type = __process_seatgeek_types(event.get("type", None))
        processed_events.append({
            "name": event.get("title", None),
            "datetime_local": event.get("datetime_local", None),
            "datetime_utc": event.get("datetime_utc", None),
            "timezone": event.get("timezone", None),
            "type": type,
            "venue_id": __get_seatgeek_venue_id(event.get("venue", {})),
            "artist_ids": __get_artist_ids(event.get("performers", []), type),
            "min_ticket_price": None,
            "max_ticket_price": None,
            "source": "seatgeek",
            "source_id": event.get("id")
        })

    return processed_events


def process_ticketmaster_events(events: list[dict]) -> list[dict]:
    processed_events = []
    for event in events:
        type = __process_ticketmaster_types(event.get("type", None))
        processed_events.append({
            "name": event.get("name", None),
            "datetime_local": event.get("datetime_local", None),
            "datetime_utc": event.get("datetime_utc", None),
            "timezone": event.get("timezone", None),
            "type": type,
            "venue_id": __get_ticketmaster_venue_id(event.get("venues", [])),
            "artist_ids": __get_artist_ids(event.get("attractions", []), type),
            "min_ticket_price": __get_min_ticket_price(event.get("price_ranges", [])),
            "max_ticket_price": __get_max_ticket_price(event.get("price_ranges", [])),
            "source": "ticketmaster",
            "source_id": event.get("id")
        })

    return processed_events


def __get_best_image_url(ticketmaster_entry: dict) -> Optional[str]:
    """
    Retrieve the highest quality image URL from Ticketmaster images.

    Prioritizes images based on predefined quality indicators and size.

    :param ticketmaster_entry: Dictionary containing Ticketmaster data.
    :return: URL of the best image or None if not available.
    """
    images = ticketmaster_entry.get('images')
    if not images:
        return None

    quality_indicators = [
        'TABLET_LANDSCAPE_LARGE',
        'RETINA_LANDSCAPE',
        'TABLET_LANDSCAPE',
        'RETINA_PORTRAIT'
    ]

    sorted_images = sorted(
        (img for img in images if isinstance(img, dict) and 'url' in img),
        key=lambda x: (
            next(
                (i for i, quality in enumerate(quality_indicators) if quality in x.get('url', '')),
                len(quality_indicators)
            ),
            -x.get('width', 0)
        )
    )

    if sorted_images:
        return sorted_images[0]['url']
    return None


def __process_seatgeek_types(type: Optional[str]) -> str:
    if type in ["animal_sports", "auto_racing", "baseball", "basketball", "boxing", "college_gymnastics",
                "college_lacrosse", "college_softball", "college_track_and_field", "college_volleyball",
                "college_wrestling", "esports", "european_soccer", "extreme_sports", "f1", "fighting",
                "football", "golf", "gymnastics", "hockey", "horse_racing", "indycar", "international_soccer",
                "lacrosse", "lpga", "major_league_lacrosse", "major_league_rugby", "minor_league_baseball",
                "minor_league_hockey", "mlb", "mls", "mma", "monster_truck", "motocross", "nascar", "nascar_cup",
                "national_womens_soccer", "nba", "nba_dleague", "ncaa_baseball", "ncaa_basketball", "ncaa_football",
                "ncaa_hockey", "ncaa_soccer", "ncaa_womens_basketball", "nfl", "nhl", "olympic_sports", "pga",
                "rodeo", "rugby", "soccer", "sports", "super_league_soccer", "tennis", "united_soccer_league",
                "volleyball", "wnba", "womens_college_hockey", "womens_college_lacrosse", "womens_college_soccer",
                "womens_college_volleyball", "wrestling", "wwe", "xfl"]:
        
        return "sports"
    elif type in ["broadway", "broadway_tickets_national", "classical", "classical_opera",
                  "classical_orchestral_instrumental", "classical_vocal", "comedy", "dance",
                  "dance_performance_tour", "film", "opera", "orchestral", "suite", "theater", "vocal"]:
        
        return "arts"
    elif type in ["band", "concert", "music_festival"]:
        
        return "music"
    else:
        return "other"

# Maps Ticketmaster event types to custom types
def __process_ticketmaster_types(type: Optional[str]) -> str:
    if type in ["arts & theatre", "film"]:
        return "arts"
    elif type in ["music"]:
        return "music"
    elif type in ["sports"]:
        return "sports"
    else:
        return "other"

# Converts SeatGeek venue data from text to json and return the id
def __get_seatgeek_venue_id(venue) -> Optional[str]:
    while not isinstance(venue, dict):
        venue = json.loads(venue)

    # If SeatGeek venue is not available
    if not venue:
        return None
    
    return venue.get("id", None)

# Converts Ticketmaster venue data from text to json and return the id
def __get_ticketmaster_venue_id(venue) -> Optional[str]:
    while not isinstance(venue, list):
        venue = json.loads(venue)
    
    # If Ticketmaster venue is not available
    if len(venue) == 0:
        return None

    return venue[0].get("id", None)

# Returns a simplified list of artist ids
def __get_artist_ids(artists: list[dict] | str, type: str) -> list[str]:
    artist_ids = []

    if type != "music":
        return artist_ids

    while not isinstance(artists, list):
        artists = json.loads(artists)

    for artist in artists:
        artist_ids.append(artist['id'])

    return list(set(artist_ids))

# Calculates the min ticket price
def __get_min_ticket_price(price_ranges: list[dict]) -> Optional[int]:
    if price_ranges:
        return price_ranges[0].get("min", None)
    
    return None

# Calculates the max ticket price
def __get_max_ticket_price(price_ranges: list[dict]) -> Optional[int]:
    if price_ranges:
        return price_ranges[0].get("max", None)
    
    return None
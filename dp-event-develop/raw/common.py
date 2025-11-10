from typing import Optional
from datetime import datetime, timedelta, timezone, date, time
from zoneinfo import ZoneInfo


def process_seatgeek_events(events):
    """
    Apply schema to the events received from SeatGeek API.
    """
    processed_events = []
    for event in events:
        processed_events.append({
            "id": event.get("id", None),
            "title": event.get("title", None),
            "type": event.get("type", None),
            "datetime_local": event.get("datetime_local", None),
            "datetime_utc": event.get("datetime_utc", None),
            "timezone": event.get("venue", {}).get("timezone", None),
            "venue": event.get("venue", {}),
            "performers": event.get("performers", [])
        })
    
    return processed_events


def process_seatgeek_venue(venue: dict) -> dict:
    """
    Process SeatGeek venue.
    """
    return {
        "id": venue.get("id", None),
        "name": venue.get("name", None),
        "address": venue.get("address", None),
        "city": venue.get("city", None),
        "state": venue.get("state", None),
        "country": venue.get("country", None),
        "postal_code": venue.get("postal_code", None),
        "timezone": venue.get("timezone", None),
        "capacity": venue.get("capacity", None),
        "location": venue.get("location", {})
    }


def process_seatgeek_performer(performer: dict) -> dict:
    """
    Process SeatGeek performer.
    """
    return {
        "id": performer.get("id", None),
        "name": performer.get("name", None),
        "image": performer.get("image", None),
        "genres": performer.get("genres", []),
        "links": performer.get("links", []),
        "spotify_id": __extract_spotify_id_sg(performer.get("links", [])),
    }


def process_ticketmaster_events(events):
    """
    This is a custom function.
    """
    processed_events = []
    for event in events:
        venues = event.get("_embedded", {}).get("venues", [])
        venue_timezone = __get_timezone(venues[0] if venues else None)
        datetime_local, datetime_utc, timezone = __get_datetime(event.get("dates", {}), venue_timezone)

        if __is_test_event(event):
            continue

        processed_events.append({
            "id": event.get("id", None),
            "name": event.get("name", None),
            "type": event.get('classifications', [{}])[0].get('segment', {}).get('name', 'unknown').lower(),
            "datetime_local": datetime_local,
            "datetime_utc": datetime_utc,
            "timezone": timezone,
            "price_ranges": event.get("priceRanges", []),
            "venues": event.get("_embedded", {}).get("venues", []),
            "attractions": event.get("_embedded", {}).get("attractions", [])
        })
    
    return processed_events


def process_ticketmaster_music_performers(attractions: list[dict]) -> list[dict]:
    """
    Process performers from Ticketmaster events that are specifically music-related.
    """
    processed_attractions = []
    if not attractions:
        return processed_attractions
    for attraction in attractions:
        name = attraction.get("name", None)
        spotify_id = __extract_spotify_id_tm(attraction.get('externalLinks', {}))
        if (not name and not spotify_id) or (name and name.lower() in ["no artist", "no artist name"]):
            continue

        processed_attractions.append({
            "id": attraction.get("id", None),
            "name": attraction.get("name"),
            "external_links": attraction.get("externalLinks", {}),
            "aliases": attraction.get("aliases", []),
            "images": attraction.get("images", []),
            "spotify_id": spotify_id
        })

    return processed_attractions


def process_ticketmaster_venues(venues: list[dict]) -> list[dict]:
    """
    Process performers from Ticketmaster events that are specifically music-related.
    """
    processed_venues = []

    venue = venues[0] if venues else None
    if not venue:    
        return processed_venues
    processed_venues.append({
        "id": venue.get("id", None),
        "name": venue.get("name", None),
        "address": venue.get("address", {}).get("line1", None),
        "city": venue.get("city", {}).get("name", None),
        "state": venue.get("state", {}).get("stateCode", None),
        "country": venue.get("country", {}).get("countryCode", None),
        "postal_code": venue.get("postalCode", None),
        "timezone": __get_timezone(venue),
        "location": venue.get("location", {})
    })

    return processed_venues


def remove_duplicates_by_id(dicts_list):
    seen_ids = set()
    unique_dicts = []
    for d in dicts_list:
        if d['id'] not in seen_ids:
            unique_dicts.append(d)
            seen_ids.add(d['id'])
    return unique_dicts


def get_data_date(last_processed_date: datetime):
    if ((last_processed_date.date() - datetime.now(timezone.utc).date()).days > 365
        or last_processed_date.date() == date(1900, 1, 1)):
        return datetime.now(timezone.utc).date()
        
    return last_processed_date.date() + timedelta(days=1)


def to_datetime_utc(date_obj: date) -> datetime:
    return datetime.combine(date_obj, time(tzinfo=timezone.utc))


def __extract_spotify_id_sg(links: dict) -> Optional[str]:
    """
    Extract Spotify artist ID from external links, ignoring non-artist IDs.
    """
    for link in links:
        if link.get('provider') == 'spotify':
            return link.get('id').split(':')[-1]


def __get_datetime(dates: dict, venue_timezone: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    start_date = dates.get("start", {})

    local_date = start_date.get("localDate", None)
    local_time = start_date.get("localTime", "00:00:00")

    datetime_local = None
    if local_date and local_time:
        datetime_local = datetime.strptime(f"{local_date} {local_time}", "%Y-%m-%d %H:%M:%S")

    datetime_utc = start_date.get('dateTime', None)
    timezone = dates.get("timezone", None) or venue_timezone

    if datetime_utc:
        datetime_utc = datetime.strptime(datetime_utc, "%Y-%m-%dT%H:%M:%SZ")
    
    if datetime_utc is None and datetime_local and timezone:
        local_zone = ZoneInfo(timezone)
        datetime_utc = datetime_local.replace(tzinfo=ZoneInfo("UTC")).astimezone(local_zone)

    datetime_local_str = datetime_local.strftime("%Y-%m-%d %H:%M:%S") if datetime_local else None
    datetime_utc_str = datetime_utc.strftime("%Y-%m-%d %H:%M:%S%z") if datetime_utc else None

    return datetime_local_str, datetime_utc_str, timezone


def __get_timezone(venue: Optional[dict]) -> Optional[str]:
    """
    Get the timezone of a venue.
    """
    if not venue:
        return None
    timezone = venue.get("timezone", None)

    if timezone and timezone.lower() == "no timezone":
        timezone = None

    return timezone


def __is_test_event(event: dict) -> bool:
    if event.get("test", True):
        return True
    
    embedded = event.get("_embedded", {})
    
    return any(venue.get("test", True) for venue in embedded.get("venues", [])) or \
           any(attraction.get("test", True) for attraction in embedded.get("attractions", []))


def __extract_spotify_id_tm(external_links: dict) -> Optional[str]:
    """
    Extract Spotify artist ID from external links, ignoring non-artist IDs.
    """
    spotify_links = external_links.get('spotify', [])
    if spotify_links:
        for link in spotify_links:
            spotify_url = link.get('url', '')
            # Check if the URL is for an artist
            if '/artist/' in spotify_url:
                # Split the URL by '/' and attempt to extract the artist ID
                parts = spotify_url.split('/')
                if 'artist' in parts:
                    artist_index = parts.index('artist') + 1
                    if artist_index < len(parts):
                        artist_id = parts[artist_index].split('?')[0].split('#')[0]  # Remove any query parameters
                        return artist_id
    return None
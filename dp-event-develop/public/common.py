import uuid
from rtree import index
from logging import Logger
from functools import lru_cache
from collections import defaultdict, Counter
from math import radians, sin, cos, sqrt, atan2
from typing import Optional
from itertools import chain

from rapidfuzz import fuzz, process
from shapely.geometry import Polygon, Point
from pandas import DataFrame, options, concat, notnull, to_numeric

options.mode.chained_assignment = None


def consolidate_artists(
        artists: list[dict],
        public_artists: list[dict],
        match_threshold: int,
        logger: Logger
    ) -> list[dict]:
    """
    Process the events and return the processed events.
    Args:
        artists (DataFrame): A list of artists to be processed.
        public_artists (list[dict]): A list of public artists to be processed.
        match_threshold (int): The threshold to be used for fuzzy match.
        logger (Logger): A logger instance.
    Returns:
        list[dict]: A list of processed artists.
    """
    artists_df = DataFrame(artists)

    # Separate SeatGeek and Ticketmaster artists
    logger.info("Separating SeatGeek and Ticketmaster artists...")
    seatgeek_artists = __remove_artist_duplicates(artists_df[artists_df["source"] == "seatgeek"], match_threshold)
    ticketmaster_artists = __remove_artist_duplicates(artists_df[artists_df["source"] == "ticketmaster"], match_threshold)
    logger.info(f"SeatGeek artists: {len(seatgeek_artists)} and Ticketmaster artists: {len(ticketmaster_artists)} separated.")

    # Merge SeatGeek and Ticketmaster artists
    logger.info("Merging SeatGeek and Ticketmaster artists...")
    new_artists_df = __merge_artists(seatgeek_artists, ticketmaster_artists, match_threshold)
    logger.info(f"Merged artists: {len(new_artists_df)}")

    # Merge filtered artists with public artists to get artist ids
    logger.info("Merging filtered artists with public artists to retrieve ids...")
    if public_artists:
        public_artists_df = DataFrame(public_artists)

        # Match with Spotify ID first
        public_spotify_artists_df = public_artists_df[public_artists_df["spotify_id"].notnull()]
        new_spotify_artists_df = new_artists_df[new_artists_df["spotify_id"].notnull()]

        merged_spotify_artists = new_spotify_artists_df.merge(
            public_spotify_artists_df,
            on="spotify_id",
            how="inner",
            suffixes=("", "_old")
        )
        print(merged_spotify_artists.columns)

        unmatched_artists_df = new_artists_df[~new_artists_df["id"].isin(merged_spotify_artists["id"])]
        
        merged_spotify_artists["id"] = merged_spotify_artists.apply(lambda row: row["id_old"] if row["id_old"] else str(uuid.uuid4()), axis=1)

        new_spotify_artists_df = merged_spotify_artists[["id", "name", "image", "spotify_id", "seatgeek_ids", "ticketmaster_ids"]]

        # Match with SeatGeek and Ticketmaster IDs if Spotify ID is not available
        public_artists_df["combined_ids"] = public_artists_df.apply(lambda row: row["seatgeek_ids"] + row["ticketmaster_ids"], axis=1)
        unmatched_artists_df["combined_ids"] = unmatched_artists_df.apply(lambda row: row["seatgeek_ids"] + row["ticketmaster_ids"], axis=1)

        public_artists_df["seatgeek_ids"] = public_artists_df["seatgeek_ids"].apply(tuple)
        public_artists_df["ticketmaster_ids"] = public_artists_df["ticketmaster_ids"].apply(tuple)
        unmatched_artists_df["seatgeek_ids"] = unmatched_artists_df["seatgeek_ids"].apply(tuple)
        unmatched_artists_df["ticketmaster_ids"] = unmatched_artists_df["ticketmaster_ids"].apply(tuple)

        public_artists_df = public_artists_df.explode("combined_ids")
        unmatched_artists_df = unmatched_artists_df.explode("combined_ids")

        merged_artists = unmatched_artists_df.merge(
            public_artists_df, 
            how="left", 
            on="combined_ids", 
            suffixes=("", "_old")
        )

        merged_artists.drop(columns=["combined_ids", "seatgeek_ids_old", "ticketmaster_ids_old", "spotify_id_old"], inplace=True)

        matched_artists_df = merged_artists.sort_values(by=["id", "id_old"]).drop_duplicates(
            subset=["id", "name", "image", "spotify_id", "seatgeek_ids", "ticketmaster_ids"],
            keep="first"
        ).copy()

        matched_artists_df["id"] = matched_artists_df["id_old"].fillna("").apply(lambda x: x if x else str(uuid.uuid4()))

        matched_artists_df["seatgeek_ids"] = matched_artists_df["seatgeek_ids"].apply(list)
        matched_artists_df["ticketmaster_ids"] = matched_artists_df["ticketmaster_ids"].apply(list)

        matched_artists_df.drop(columns=["id_old"], inplace=True)

        new_artists_df = concat([new_spotify_artists_df, matched_artists_df], ignore_index=True)

    else:
        new_artists_df["id"] = new_artists_df.apply(lambda _: str(uuid.uuid4()), axis=1)
    
    __percent_match.cache_clear()
    
    return new_artists_df.where(notnull(new_artists_df), None).to_dict(orient="records")


def process_venues(venues, name_threshold, address_threshold):
    """
    Processes and consolidates venue data from Ticketmaster and Seatgeek sources.
    - Removes duplicates within each source.
    - Matches and consolidates data between the two sources.
    """   
    # Separate data by source
    ticketmaster_venues = [venue for venue in venues if venue["source"] == "ticketmaster"]
    seatgeek_venues = [venue for venue in venues if venue["source"] == "seatgeek"]

    # Remove duplicates within each source
    ticketmaster_venues = __remove_venue_duplicates(ticketmaster_venues, name_threshold, address_threshold)
    seatgeek_venues = __remove_venue_duplicates(seatgeek_venues, name_threshold, address_threshold)

    consolidated = []

    for sg_venue in seatgeek_venues:
        sg_venue["seatgeek_ids"] = sg_venue["source_id"]
        sg_venue["ticketmaster_ids"] = []
        consolidated.append(sg_venue)

    for tm_venue in ticketmaster_venues:
        tm_venue["ticketmaster_ids"] = tm_venue["source_id"]
        tm_venue["seatgeek_ids"] = []
        matched = False

        for sg_venue in consolidated:
            if sg_venue["ticketmaster_ids"]:
                continue

            if __is_venue_duplicate(tm_venue, sg_venue, name_threshold, address_threshold):
                sg_venue["ticketmaster_ids"] = tm_venue["source_id"]
                matched = True
                break

        if not matched:
            # If no match, add the Ticketmaster venue
            consolidated.append(tm_venue)

    return consolidated


def compare_existing_venues(public_venues, venues, name_threshold, address_threshold):
    """
    Compare existing data with new data and consolidate.
    
    - If a match is found, prefer the new data but keep the 'id' column from existing data.
    - If no match, generate a new UUID for 'id' and add the new record.
    """
    consolidated_venues = []

    # Build dictionaries for fast lookup
    tm_map = {}  # {tm_id: venue}
    sg_map = {}  # {sg_id: venue}

    for venue in public_venues:
        for tm_id in venue.get("ticketmaster_ids", []):
            tm_map[tm_id] = venue
        for sg_id in venue.get("seatgeek_ids", []):
            sg_map[sg_id] = venue

    for new_venue in venues:
        new_tm_ids = set(new_venue.get("ticketmaster_ids", []))
        new_sg_ids = set(new_venue.get("seatgeek_ids", []))
        
        matched_venue = None

        # Fast lookup for ID matches
        for tm_id in new_tm_ids:
            if tm_id in tm_map:
                matched_venue = tm_map[tm_id]
                break  # Stop at first match
        
        if not matched_venue:  # Only check SeatGeek IDs if no Ticketmaster match
            for sg_id in new_sg_ids:
                if sg_id in sg_map:
                    matched_venue = sg_map[sg_id]
                    break

        # Check for duplicate venues if no ID match
        if not matched_venue:
            for existing_venue in public_venues:
                if __is_venue_duplicate(existing_venue, new_venue, name_threshold, address_threshold):
                    matched_venue = existing_venue
                    break

        # Update or create a new record
        if matched_venue:
            consolidated_tm_ids = __merge_ids(matched_venue.get("ticketmaster_ids", []), new_tm_ids)
            consolidated_sg_ids = __merge_ids(matched_venue.get("seatgeek_ids", []), new_sg_ids)

            new_record = matched_venue.copy()
            new_record["ticketmaster_ids"] = consolidated_tm_ids
            new_record["seatgeek_ids"] = consolidated_sg_ids
        else:
            new_record = __filter_columns(new_venue)

            new_record["id"] = str(uuid.uuid4())
            new_record["ticketmaster_ids"] = list(new_tm_ids)
            new_record["seatgeek_ids"] = list(new_sg_ids)
            new_record["is_valid"]  = True

        consolidated_venues.append(new_record)
    
    deduplicated_venues = {}
    for venue in consolidated_venues:
        if venue["id"] in deduplicated_venues:
            found_venue = deduplicated_venues[venue["id"]]
            found_venue["seatgeek_ids"] = __merge_ids(found_venue["seatgeek_ids"], set(venue["seatgeek_ids"]))
            found_venue["ticketmaster_ids"] = __merge_ids(found_venue["ticketmaster_ids"], set(venue["ticketmaster_ids"]))
            deduplicated_venues[venue["id"]] = found_venue
        else:
            deduplicated_venues[venue["id"]] = venue
    
    deduplicated_venues = list(deduplicated_venues.values())

    # Verify all IDs in the final consolidated dataset are unique
    output_ids = [venue["id"] for venue in deduplicated_venues]
    duplicate_ids = __get_duplicates(output_ids)
    if duplicate_ids:
        raise RuntimeError(f"Duplicate IDs found: {duplicate_ids}")

    __percent_match.cache_clear()
    __calculate_distance.cache_clear()

    return deduplicated_venues


def map_venue_dma(venues: list[dict], dmas: list[dict], mapped_venues: set, distance_threshold: int) -> list[dict]:
    """
    Maps unmapped venues to the respective DMAs based on the DMA boundaries and market locations.
    """
    venue_dma_map = []
    for venue in venues:
        if venue.get("id") in mapped_venues and not venue.get("is_valid"):
            continue

        mapped_dmas = __map_venue(venue, dmas, distance_threshold)

        if mapped_dmas:
            venue_dma_map.extend(mapped_dmas)
            
    return venue_dma_map


def consolidate_events(
        events: list[dict],
        public_events: list[dict],
        public_venues: list[dict],
        public_artists: list[dict],
        logger: Logger
    ) -> tuple[list[dict], list[dict]]:
    """
    Process the events and return the processed events.
    Args:
        events (DataFrame): A list of events to be processed.
        public_events (list[dict]): A list of public events to be processed.
        public_venues (list[dict]): A list of public venues to be processed.
        public_artists (list[dict]): A list of public artists to be processed.
        logger (Logger): A logger instance.
    Returns:
        tuple[list[dict], list[dict]]: A list of processed events and event-artist mappings.
    """
    events_df = DataFrame(events)

    # Link public venues to events
    logger.info("Linking public venues to events...")
    events_with_venues = __link_venues_to_events(events_df, public_venues)
    logger.info(f"Linked venues to events. Event count: {len(events_with_venues)}")

    # Link public artists to events
    logger.info("Linking public artists to events...")
    events_with_artists = __link_artists_to_events(events_with_venues, public_artists)
    logger.info(f"Linked artists to events. Event count: {len(events_with_artists)}")

    # Separate SeatGeek and Ticketmaster events
    logger.info("Separating SeatGeek and Ticketmaster events...")
    seatgeek_events = __remove_event_duplicates(events_with_artists[events_with_artists["source"] == "seatgeek"])
    ticketmaster_events = __remove_event_duplicates(events_with_artists[events_with_artists["source"] == "ticketmaster"])
    logger.info(f"SeatGeek events: {len(seatgeek_events)} and Ticketmaster events: {len(ticketmaster_events)} separated.")

    # Merge SeatGeek and Ticketmaster events
    logger.info("Merging SeatGeek and Ticketmaster events...")
    merged_events = __merge_events(seatgeek_events, ticketmaster_events)
    logger.info(f"Merged events: {len(merged_events)}")

    # Merge events with public events to get event ids
    logger.info("Merging events with public events...")
    final_events = __merge_with_public_events(merged_events, public_events)
    logger.info(f"Merged events with public events: {len(final_events)}")
    
    # Merge events with public artists to link artists
    logger.info("Get event_artists...")
    event_artists = __get_event_artists(final_events.copy())
    logger.info(f"Got {len(event_artists)} event_artists.")

    final_events.drop(columns=["artist_ids"], inplace=True)

    __percent_match.cache_clear()

    return final_events.where(notnull(final_events), None).to_dict(orient="records"), event_artists.where(notnull(event_artists), None).to_dict(orient="records")


def __get_duplicates(lst):
    counts = Counter(lst)
    return [item for item, count in counts.items() if count > 1]


def __remove_event_duplicates(events: DataFrame) -> DataFrame:    
    if events.empty:
        return events
    
    events["date"] = events["datetime_local"].dt.date

    grouped_events = events.groupby(["date", "venue_id"], as_index=False).agg({
        **{col: "first" for col in events.columns
           if col not in ["date", "venue_id", "artist_ids", "source_id", "min_ticket_price", "max_ticket_price"]},
        "artist_ids": lambda x: list(set(chain.from_iterable(x))),
        "source_id": list,
        "min_ticket_price": lambda x: x[(x != 0) & x.notna()].min() if not x[(x != 0) & x.notna()].empty else None,
        "max_ticket_price": lambda x: x[(x != 0) & x.notna()].max() if not x[(x != 0) & x.notna()].empty else None
    })

    grouped_events.drop(columns=["date", "source"], inplace=True)
    return grouped_events


def __merge_events(seatgeek_events: DataFrame, ticketmaster_events: DataFrame) -> DataFrame:
    """Merge SeatGeek and Ticketmaster events based on date and venue."""
    seatgeek_events["date"] = seatgeek_events["datetime_local"].dt.date

    ticketmaster_events["date"] = ticketmaster_events["datetime_local"].dt.date

    merged_events = seatgeek_events.merge(ticketmaster_events, on=["date", "venue_id"], how="outer", suffixes=("_seatgeek", "_ticketmaster"))

    if merged_events.empty:
        return DataFrame(columns=[
            "id", "name", "datetime_local", "datetime_utc", "timezone", "type",
            "venue_id", "artist_ids", "min_ticket_price", "max_ticket_price",
            "seatgeek_ids", "ticketmaster_ids"
        ])

    else:
        merged_events["id"] = merged_events["id_seatgeek"].fillna(merged_events["id_ticketmaster"])
        merged_events["name"] = merged_events["name_seatgeek"].fillna(merged_events["name_ticketmaster"])
        merged_events["datetime_local"] = merged_events["datetime_local_seatgeek"].fillna(merged_events["datetime_local_ticketmaster"])
        merged_events["datetime_utc"] = merged_events["datetime_utc_seatgeek"].fillna(merged_events["datetime_utc_ticketmaster"])
        merged_events["timezone"] = merged_events["timezone_seatgeek"].fillna(merged_events["timezone_ticketmaster"])
        merged_events["type"] = merged_events["type_seatgeek"].fillna(merged_events["type_ticketmaster"])
        merged_events["artist_ids"] = merged_events.apply(
            lambda row: (row["artist_ids_seatgeek"] if isinstance(row["artist_ids_seatgeek"], list) else []) +
                        (row["artist_ids_ticketmaster"] if isinstance(row["artist_ids_ticketmaster"], list) else []),
            axis=1
        )
        merged_events["min_ticket_price"] = (
            merged_events["min_ticket_price_seatgeek"]
            .fillna(merged_events["min_ticket_price_ticketmaster"])
            .astype(float)
        )
        merged_events["max_ticket_price"] = (
            merged_events["max_ticket_price_seatgeek"]
            .fillna(merged_events["max_ticket_price_ticketmaster"])
            .astype(float)
        )
        merged_events["seatgeek_ids"] = merged_events["source_id_seatgeek"].apply(lambda x: x if isinstance(x, list) else [])
        merged_events["ticketmaster_ids"] = merged_events["source_id_ticketmaster"].apply(lambda x: x if isinstance(x, list) else [])

    final_events = merged_events[["id", "name", "datetime_local", "datetime_utc", "timezone", "type",
                                  "venue_id", "artist_ids", "min_ticket_price", "max_ticket_price",
                                  "seatgeek_ids", "ticketmaster_ids"]].copy()

    return final_events


def __remove_artist_duplicates(artists: DataFrame, match_threshold: int) -> DataFrame:
    if artists.empty:
        return artists

    # Remove rows where 'name' is null
    artists = artists.dropna(subset=["name"])

    # Step 1: Merge by spotify_id (if present)
    artists_by_spotify = artists.groupby("spotify_id", dropna=True).agg({
        "id": "first",
        "name": "first",
        "image": lambda x: x.dropna().iloc[0] if not x.dropna().empty else None,
        "source": "first",
        "source_id": lambda x: list(x)  # Combine all source_ids
    }).reset_index()

    # Step 2: Identify artists without spotify_id for fuzzy matching
    no_spotify_df = artists[artists["spotify_id"].isna()].copy()

    # Step 3: Fuzzy match artists without spotify_id (against each other AND with spotify artists)
    if not no_spotify_df.empty:
        # Only use no_spotify_df names for internal fuzzy matching
        no_spotify_names = no_spotify_df["name"].tolist()

        # Union-Find structure to track connected components
        parent = {name: name for name in no_spotify_names}

        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            root_x = find(x)
            root_y = find(y)
            if root_x != root_y:
                parent[root_y] = root_x

        # Match within no_spotify_df only
        for name in no_spotify_names:
            match, score, _ = process.extractOne(name.lower(), no_spotify_names, scorer=fuzz.token_sort_ratio)
            if match and score >= match_threshold:
                union(name, match)

        # Map each name to its root representative
        no_spotify_df["group"] = no_spotify_df["name"].apply(lambda x: find(x))

        # Step 4: Merge fuzzy-matched records within no_spotify_df
        no_spotify_df = no_spotify_df.groupby("group", as_index=False).agg({
            "id": "first",
            "name": "first",
            "image": lambda x: x.dropna().iloc[0] if not x.dropna().empty else None,
            "source": "first",
            "source_id": lambda x: list(x)
        })

        # Add missing spotify_id for fuzzy-matched rows
        no_spotify_df["spotify_id"] = None

        # Step 5: Add Spotify names to the parent map
        for name in artists_by_spotify["name"].tolist():
            if name not in parent:
                parent[name] = name

        # Step 6: Match non-Spotify artists against Spotify artists
        for name in no_spotify_df["name"].tolist():
            match, score, _ = process.extractOne(name.lower(), artists_by_spotify["name"].tolist(), scorer=fuzz.token_sort_ratio)
            if match and score >= match_threshold:
                union(name, match)

        # Apply final grouping based on connected components
        no_spotify_df["group"] = no_spotify_df["name"].apply(lambda x: find(x))
        artists_by_spotify["group"] = artists_by_spotify["name"].apply(lambda x: find(x))

    # Step 7: Combine both DataFrames (merged spotify + fuzzy matched)
    combined_df = concat([artists_by_spotify, no_spotify_df], ignore_index=True)

    # Final grouping after combining both datasets
    merged_artists = combined_df.groupby("group", as_index=False).agg({
        "id": "first",
        "name": "first",
        "image": lambda x: x.dropna().iloc[0] if not x.dropna().empty else None,
        "spotify_id": lambda x: x.dropna().iloc[0] if not x.dropna().empty else None,
        "source": "first",
        "source_id": lambda x: [item for sublist in x for item in sublist]
    })

    return merged_artists


def __merge_artists(seatgeek_artists: DataFrame, ticketmaster_artists: DataFrame, match_threshold: int) -> DataFrame:
    if seatgeek_artists.empty:
        ticketmaster_artists["seatgeek_ids"] = ticketmaster_artists.apply(lambda _: [], axis=1)
        ticketmaster_artists["ticketmaster_ids"] = ticketmaster_artists["source_id"]
        return ticketmaster_artists[["id", "name", "image", "spotify_id", "seatgeek_ids", "ticketmaster_ids"]]

    if ticketmaster_artists.empty:
        seatgeek_artists["seatgeek_ids"] = seatgeek_artists["source_id"]
        seatgeek_artists["ticketmaster_ids"] = seatgeek_artists.apply(lambda _: [], axis=1)
        return seatgeek_artists[["id", "name", "image", "spotify_id", "seatgeek_ids", "ticketmaster_ids"]]

    # Step 1: Exact Matching by Spotify ID
    # Convert source_id to tuple for comparison
    seatgeek_artists["source_id"] = seatgeek_artists["source_id"].apply(tuple)
    ticketmaster_artists["source_id"] = ticketmaster_artists["source_id"].apply(tuple)
    
    merged_artists = seatgeek_artists.dropna(subset=["spotify_id"]).merge(
        ticketmaster_artists.dropna(subset=["spotify_id"]),
        on="spotify_id",
        how="inner",
        suffixes=("_seatgeek", "_ticketmaster")
    )

    matched_seatgeek_ids = set(merged_artists["source_id_seatgeek"])
    matched_ticketmaster_ids = set(merged_artists["source_id_ticketmaster"])
    
    # Step 2: Name-Based Fuzzy Matching for Unmatched Artists
    unmatched_seatgeek = seatgeek_artists[~seatgeek_artists["source_id"].isin(matched_seatgeek_ids)].copy()
    unmatched_ticketmaster = ticketmaster_artists[~ticketmaster_artists["source_id"].isin(matched_ticketmaster_ids)].copy()

    if not unmatched_seatgeek.empty and not unmatched_ticketmaster.empty:
        potential_matches = unmatched_ticketmaster["name"].tolist()
        unmatched_seatgeek["match_name"] = unmatched_seatgeek["name"].apply(
            lambda name: process.extractOne(name, potential_matches, scorer=fuzz.token_sort_ratio)
        )

        fuzzy_matches = unmatched_seatgeek[unmatched_seatgeek["match_name"].apply(lambda x: x[1] > match_threshold)].copy()
        fuzzy_matches["matched_name"] = fuzzy_matches["match_name"].apply(lambda x: x[0])

        final_fuzzy = fuzzy_matches.merge(unmatched_ticketmaster, left_on="matched_name", right_on="name", suffixes=("_seatgeek", "_ticketmaster"))

        # Add fuzzy-matched results to merged_artists
        merged_artists = concat([merged_artists, final_fuzzy], ignore_index=True)

        matched_seatgeek_ids.update(final_fuzzy["source_id_seatgeek"])
        matched_ticketmaster_ids.update(final_fuzzy["source_id_ticketmaster"])


    # Step 3: Construct Final DataFrame
    merged_artists["id"] = merged_artists["id_seatgeek"].fillna(merged_artists["id_ticketmaster"])
    merged_artists["name"] = merged_artists["name_seatgeek"].fillna(merged_artists["name_ticketmaster"])
    merged_artists["image"] = merged_artists["image_seatgeek"].fillna(merged_artists["image_ticketmaster"])
    merged_artists["spotify_id"] = merged_artists["spotify_id"]
    merged_artists["seatgeek_ids"] = merged_artists["source_id_seatgeek"].apply(list)
    merged_artists["ticketmaster_ids"] = merged_artists["source_id_ticketmaster"].apply(list)

    # Step 4: Add Unmatched Artists
    unmatched_seatgeek = seatgeek_artists[~seatgeek_artists["source_id"].isin(matched_seatgeek_ids)].copy()
    unmatched_ticketmaster = ticketmaster_artists[~ticketmaster_artists["source_id"].isin(matched_ticketmaster_ids)].copy()

    if not unmatched_seatgeek.empty:
        unmatched_seatgeek["seatgeek_ids"] = unmatched_seatgeek["source_id"].apply(list)
        unmatched_seatgeek["ticketmaster_ids"] = unmatched_seatgeek.apply(lambda _: [], axis=1)
        merged_artists = concat([merged_artists, unmatched_seatgeek], ignore_index=True)

    if not unmatched_ticketmaster.empty:
        unmatched_ticketmaster["seatgeek_ids"] = unmatched_ticketmaster.apply(lambda _: [], axis=1)
        unmatched_ticketmaster["ticketmaster_ids"] = unmatched_ticketmaster["source_id"].apply(list)
        merged_artists = concat([merged_artists, unmatched_ticketmaster], ignore_index=True)

    return merged_artists[["id", "name", "image", "spotify_id", "seatgeek_ids", "ticketmaster_ids"]]


def __map_venue(venue: dict, dmas: list[dict], distance_threshold: int) -> Optional[list[dict]]:
    primary_dma_id = None

    if venue.get("country") != "US" or venue.get("latitude") is None or venue.get("longitude") is None:
        return None
    
    try:
        latitude, longitude = float(venue["latitude"]), float(venue["longitude"])
    except ValueError:
        return None

    mapped_dmas = []

    # Step 1: Determine the Primary DMA
    for dma in dmas:
        polygons = __get_polygons(dma.get("geometry", {}))
        point = Point(longitude, latitude)

        for polygon in polygons:
            if polygon.contains(point):
                primary_dma_id = dma.get("id")

                # For each DMA, find the market nearest to the venue
                market, min_distance = __get_nearest_market(dma["market"], latitude, longitude)
                market_id = None
                if market:
                    market_id = market.get("id")

                mapped_dmas.append({
                    "venue_id": venue.get("id"),
                    "dma_id": primary_dma_id,
                    "nearest_market_id": market_id,
                    "distance": 0
                })
                break
        
        if primary_dma_id:
            break

    if not primary_dma_id:
        return None

    # Step 2: Find additional DMAs using market distances
    for dma in dmas:
        # Skip checking primary DMA again
        if dma.get("id") == primary_dma_id:
            continue

        # For each DMA, find the market nearest to the venue
        market, min_distance = __get_nearest_market(dma["market"], latitude, longitude)

        if not market:
            continue

        # Add DMA if the closest market is within the threshold
        if min_distance and min_distance <= distance_threshold:
            mapped_dmas.append({
                "venue_id": venue.get("id"),
                "dma_id": dma.get("id"),
                "nearest_market_id": market.get("id"),
                "distance": min_distance
            })
    
    # Step 3: Sort and rank DMAs by distance
    mapped_dmas = __sort_and_rank(mapped_dmas)

    __calculate_distance.cache_clear()

    # Step 4: Limit to the 5 nearest DMAs (including the primary)
    return [dma for dma in mapped_dmas if dma["rank"] <= 5]


def __get_polygons(geojson_data: dict) -> list[Polygon]:
    polygons = []

    if geojson_data.get("type") == "MultiPolygon":
        for coordinate in geojson_data["coordinates"]:
            polygons.append(Polygon([tuple(coord) for coord in coordinate[0]]))
    else:
        polygons.append(Polygon([tuple(coord) for coord in geojson_data["coordinates"][0]]))

    return polygons


@lru_cache(maxsize=100_000)
def __calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine Distance Calculation
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    radius = 3958.8  # Radius of Earth in miles (6371 in km)
    return radius * c


def __get_nearest_market(markets: list[dict], latitude: float, longitude: float) -> tuple[Optional[dict], Optional[float]]:
    if not markets:
        return None, None

    min_distance = float("inf")
    nearest_market_id = None

    for market in markets:
        try:
            market_coordinates = market.get("coordinates")
        except Exception as e:
            market_coordinates = None

        if not market_coordinates:
            continue
        
        try:
            market_lat = float(market_coordinates.get("latitude"))
            market_lon = float(market_coordinates.get("longitude"))
        except ValueError:
            continue

        distance = __calculate_distance(latitude, longitude, market_lat, market_lon)

        if distance < min_distance:
            min_distance = distance
            nearest_market_id = market.get("id")

    return next((market for market in markets if market.get("id") == nearest_market_id), None), min_distance


def __sort_and_rank(mapped_dmas: list[dict]) -> list[dict]:
    if not mapped_dmas:
        return mapped_dmas
    
    mapped_dmas.sort(key=lambda x: x["distance"])

    for rank, item in enumerate(mapped_dmas, start=1):
        item["rank"] = rank
        item.pop("distance")

    return mapped_dmas


def __is_venue_duplicate(venue1, venue2, name_threshold, address_threshold):
    def remove_city(venue: str, city: str):
        if not venue or not city:
            return venue
        return venue.replace(city, "").strip()
    
    name_similarity = __percent_match(remove_city(venue1["name"], venue1["city"]), remove_city(venue2["name"], venue2["city"]))
    address_match = __percent_match(venue1["address"].lower(), venue2["address"].lower()) > address_threshold if venue1["address"] and venue2["address"] else False
    city_match = venue1["city"].lower() == venue2["city"].lower() if venue1["city"] and venue2["city"] else False

    if name_similarity >= name_threshold and (address_match or city_match):
        return True
    
    return False


def __remove_venue_duplicates(data_source, name_threshold, address_threshold):
    """Remove duplicates within a single source and consolidate their source IDs."""
    consolidated = []
    seen = set()
    
    # Step 1: Separate venues with and without city
    city_index = defaultdict(list)
    no_city_venues = []  # Store venues where city is missing
    spatial_index = index.Index()
    
    for i, venue in enumerate(data_source):
        city = venue.get("city")
        lat, lon = venue.get("latitude"), venue.get("longitude")
        
        if city:
            city_index[city.lower()].append((i, venue))
        else:
            no_city_venues.append((i, venue))  # Process these separately

        # Step 2: Build R-tree index **only for venues with valid coordinates**
        if lat and lon:
            try:
                lat, lon = float(lat), float(lon)
                spatial_index.insert(i, (lat, lon, lat, lon))  # Insert as a bounding box
            except ValueError:
                pass  # Ignore invalid lat/lon values

    # Step 3: Process venues **grouped by city**
    for city, venues in city_index.items():
        __process_group(venues, seen, spatial_index, consolidated, name_threshold, address_threshold)

    # Step 4: Process venues **without a city separately**
    __process_group(no_city_venues, seen, spatial_index, consolidated, name_threshold, address_threshold)

    return consolidated


def __process_group(venues, seen, spatial_index, consolidated, name_threshold, address_threshold):
    """Helper function to process a group of venues efficiently."""
    index_map = {i: venue for i, venue in venues}  # Map index to venue

    for i, venue in venues:
        if i in seen:
            continue

        merged_venue = venue.copy()
        merged_venue["source_id"] = set()
        if venue.get("source_id"):
            merged_venue["source_id"].add(venue["source_id"])

        lat, lon = venue.get("latitude"), venue.get("longitude")

        # Step 5: Use spatial index **only if coordinates are valid**
        nearby = []
        if lat and lon:
            try:
                lat, lon = float(lat), float(lon)
                lat_threshold = address_threshold / 69  # Roughly, 1 degree lat ≈ 69 miles
                lon_threshold = address_threshold / (69 * cos(radians(lat)))  # Adjust for latitude
                
                nearby = list(spatial_index.intersection((lat - lat_threshold, lon - lon_threshold,
                                                          lat + lat_threshold, lon + lon_threshold)))
            except ValueError:
                pass  # Invalid coordinates, no spatial filtering

        # Step 6: Compare against nearby venues (if found) or all venues in the group
        candidates = nearby if nearby else [j for j, _ in venues if j != i]  # If no coords, compare within the group

        for j in candidates:
            if j in seen or j == i:
                continue

            other_venue = index_map.get(j)
            if other_venue and __is_venue_duplicate(venue, other_venue, name_threshold, address_threshold):
                if other_venue.get("source_id"):
                    merged_venue["source_id"].add(other_venue["source_id"])
                seen.add(j)

        merged_venue["source_id"] = list(merged_venue["source_id"])
        consolidated.append(merged_venue)
        seen.add(i)


def __filter_columns(venue):
    """Extract relevant venue columns."""
    final_columns = {
        "id", "name", "address", "city", "state", "country", "postal_code",
        "latitude", "longitude", "timezone", "phone", "website",
        "capacity", "social", "seatgeek_ids", "ticketmaster_ids", "is_valid"
    }
    return {k: v for k, v in venue.items() if k in final_columns}


def __merge_ids(existing_ids: list, new_ids: set) -> list:
    """Merge and remove duplicates from two ID lists."""
    return list(set(existing_ids).union(new_ids))


def __link_venues_to_events(events: DataFrame, public_venues: list[dict]) -> DataFrame:
    public_venues_df = DataFrame(public_venues)

    public_venues_df = public_venues_df[["id", "seatgeek_ids", "ticketmaster_ids"]].copy()

    public_venues_df["venue_id"] = public_venues_df.apply(lambda row: row["seatgeek_ids"] + row["ticketmaster_ids"], axis=1)
    public_venues_df.drop(columns=["seatgeek_ids", "ticketmaster_ids"], inplace=True)
    public_venues_df = public_venues_df.explode("venue_id")

    merged_events = events.merge(
        public_venues_df,
        how="left",
        on="venue_id",
        suffixes=("", "_venue")
    )

    merged_events.drop(columns=["venue_id", "modified_at"], inplace=True)

    merged_events["artist_ids"] = merged_events["artist_ids"].apply(lambda x: tuple(x))

    events_with_venues = merged_events.sort_values(by=["id", "id_venue"]).drop_duplicates(
        subset=["id", "name", "datetime_local", "datetime_utc", "timezone", "type",
                "artist_ids", "min_ticket_price", "max_ticket_price",
                "source", "source_id"],
        keep="first"
    )

    merged_events["artist_ids"] = merged_events["artist_ids"].apply(lambda x: list(x))

    return events_with_venues.rename(columns={"id_venue": "venue_id"})


def __link_artists_to_events(events: DataFrame, public_artists: list[dict]) -> DataFrame:
    public_artists_df = DataFrame(public_artists)

    public_artists_df = public_artists_df[
        ~((public_artists_df["seatgeek_ids"].apply(lambda x: len(x) == 0)) &
        (public_artists_df["ticketmaster_ids"].apply(lambda x: len(x) == 0)))
    ][["id", "seatgeek_ids", "ticketmaster_ids"]].copy()

    public_artists_df["artist_ids"] = public_artists_df.apply(lambda row: row["seatgeek_ids"] + row["ticketmaster_ids"], axis=1)
    public_artists_df.drop(columns=["seatgeek_ids", "ticketmaster_ids"], inplace=True)
    public_artists_df = public_artists_df.explode("artist_ids")

    events = events.explode("artist_ids")

    merged_events = events.merge(
        public_artists_df,
        how="left",
        on="artist_ids",
        suffixes=("", "_artist")
    )

    merged_events.drop(columns=["artist_ids"], inplace=True)
    merged_events["min_ticket_price"] = to_numeric(merged_events["min_ticket_price"], errors='coerce')
    merged_events["max_ticket_price"] = to_numeric(merged_events["max_ticket_price"], errors='coerce')

    events_with_artists = merged_events.groupby(["id"], as_index=False).agg(
    {
        "name": "first",
        "datetime_local": "first",
        "datetime_utc": "first",
        "timezone": "first",
        "type": "first",
        "venue_id": "first",
        "id_artist": lambda x: list(x.dropna()),
        "min_ticket_price": lambda x: x[(x != 0) & x.notna()].min() if not x[(x != 0) & x.notna()].empty else None,
        "max_ticket_price": lambda x: x[(x != 0) & x.notna()].max() if not x[(x != 0) & x.notna()].empty else None,
        "source": "first",
        "source_id": "first"
    })

    return events_with_artists.rename(columns={"id_artist": "artist_ids"})


def __merge_with_public_events(events: DataFrame, public_events: list[dict]) -> DataFrame:
    """Merge events with public events to get event ids."""
    if public_events:
        public_events_df = DataFrame(public_events)
        public_events_df["seatgeek_ids"] = public_events_df["seatgeek_ids"].apply(lambda x: tuple(sorted(x)))
        public_events_df["ticketmaster_ids"] = public_events_df["ticketmaster_ids"].apply(lambda x: tuple(sorted(x)))
        public_events_df["combined_ids"] = public_events_df.apply(
            lambda row: row["seatgeek_ids"] + row["ticketmaster_ids"],
            axis=1
        )
        public_events_df = public_events_df.explode("combined_ids")

        events["seatgeek_ids"] = events["seatgeek_ids"].apply(lambda x: tuple(sorted(x)))
        events["ticketmaster_ids"] = events["ticketmaster_ids"].apply(lambda x: tuple(sorted(x)))
        events["combined_ids"] = events.apply(
            lambda row: row["seatgeek_ids"] + row["ticketmaster_ids"],
            axis=1
        )
        events = events.explode("combined_ids")

        merged_events = events.merge(
            public_events_df, 
            how="left", 
            on="combined_ids", 
            suffixes=("", "_public")
        )

        merged_events.drop(columns=["combined_ids"], inplace=True)

        grouped_events = merged_events.groupby(["seatgeek_ids", "ticketmaster_ids"]).agg(
            {
                "id": "first",
                "id_public": "first",
                "name": "first",
                "datetime_local": "first",
                "datetime_utc": "first",
                "timezone": "first",
                "type": "first",
                "venue_id": "first",
                "artist_ids": lambda x: list(set(chain.from_iterable(x))),
                "seatgeek_ids_public": lambda x: tuple(set(chain.from_iterable(x))) if isinstance(x, tuple) else (),
                "ticketmaster_ids_public": lambda x: tuple(set(chain.from_iterable(x))) if isinstance(x, tuple) else (),
                "min_ticket_price": "min",
                "max_ticket_price": "max"
            }).reset_index()

        grouped_events["id"] = grouped_events.apply(lambda row: row["id_public"] if row["id_public"] else str(uuid.uuid4()), axis=1)
        grouped_events["seatgeek_ids"] = grouped_events.apply(lambda row: list(set(row["seatgeek_ids"] + row["seatgeek_ids_public"])), axis=1)
        grouped_events["ticketmaster_ids"] = grouped_events.apply(lambda row: list(set(row["ticketmaster_ids"] + row["ticketmaster_ids_public"])), axis=1)

        final_events = grouped_events.drop(columns=["id_public", "seatgeek_ids_public", "ticketmaster_ids_public"])
    
    else:
        events["id"] = events.apply(lambda _: str(uuid.uuid4()), axis=1)

        final_events = events
    
    # Remove events with no venue_id or artist_ids
    final_events = final_events[
        ~(
            final_events["venue_id"].isna() &
            final_events["artist_ids"].apply(lambda x: not isinstance(x, list) or len(x) == 0)
        )
    ]

    return final_events


def __get_event_artists(events: DataFrame) -> DataFrame:
    events_with_artists = events[events["artist_ids"].apply(lambda x: isinstance(x, list) and len(x) > 0)]

    if events_with_artists.empty:
        return DataFrame(columns=["event_id", "artist_id"])
    
    exploded_events = events_with_artists.explode("artist_ids")
    
    event_artists = exploded_events.rename(columns={"id": "event_id", "artist_ids": "artist_id"})[["event_id", "artist_id"]]

    return event_artists.drop_duplicates().reset_index(drop=True)


@lru_cache(maxsize=100_000)
def __percent_match(A: str, B: str) -> float:
    if not A or not B:
        return 0.0
    elif A.lower() == B.lower():
        return 100.0
    else:
        return fuzz.token_sort_ratio(A.lower(), B.lower())
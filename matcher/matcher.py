# matcher/matcher.py
import json
import math
import logging
import os
from datetime import date, timedelta
from dateutil.parser import parse as parse_date
from pathlib import Path
from .vector_store import search, build_faiss_index
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Load opportunities and U.S. city→state mapping
logger.info("Loading opportunities from data/opportunities.jsonl")
OPPS = [json.loads(line) for line in open("data/opportunities.jsonl")]
logger.info(f"Loaded {len(OPPS)} opportunities")

with open("data/us_cities_by_state.json") as f:
    CITIES_BY_STATE = json.load(f)

# Ensure data directory exists
os.makedirs(os.path.dirname(settings.VECTOR_INDEX_PATH), exist_ok=True)

# Check if embeddings need to be processed for the opportunities
logger.info("Checking if opportunities have embeddings...")
need_embeddings = False
for opp in OPPS:
    if "embedding" not in opp:
        need_embeddings = True
        break

if need_embeddings:
    logger.warning("Some opportunities are missing embeddings, but continuing without them")

# FAISS index will be built on demand when needed in search()


def haversine(lat1, lon1, lat2, lon2):
    """Return distance in miles between two lat/lon points."""
    R = 3958.8  # Earth radius in miles
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def match_items(
    user_embedding,
    stances,
    top_k=5,
    only_type: str = None,
    max_cost: float = None,
    # --- location filters ---
    location_scope: str = "noevent",  # "noevent"|"nationwide"| "states"| "cities"| "radius"| "International"
    states: list[str] = None,            # e.g. ["NY","PA"]
    cities: list[str] = None,            # e.g. ["New York","Boston"]
    center: tuple[float, float] = None,   # e.g. (40.7128, -74.0060)
    radius_miles: float = None,           # e.g. 50
    # --- deadline filter ---
    deadline_before: date = None
):
    """
    Returns up to `top_k` opportunities filtered by type, cost, location, and deadlines.
    - location_scope="noevent": no geographic filtering (includes blanks)
    - for other scopes, blank-location opps still pass through
    """
    # Define initial filter function
    def initial_filter(idx):
        try:
            # Check if the index is valid
            if idx < 0 or idx >= len(OPPS):
                logger.warning(f"Invalid opportunity index: {idx}")
                return False
                
            opp = OPPS[idx]
            opp_type = opp.get("type")
            logger.info(f"Filtering opportunity {idx}: type={opp_type}")
            
            # If only_type is specified, only include that type
            if only_type:
                should_include = opp_type == only_type
                logger.info(f"Only type {only_type} requested: {should_include}")
                return bool(should_include)
                
            # By default, exclude events
            if opp_type == "event":
                logger.info("Excluding event type")
                return False
            else:
                logger.info(f"Including non-event type: {opp_type}")
                return True
        except Exception as e:
            logger.error(f"Error in filter function: {str(e)}")
            return False

    # Get initial results with type filtering
    logger.info("Starting search with event filtering")
    raw = search(user_embedding, top_k * 3, filter_fn=initial_filter)  # Increased multiplier
    logger.info(f"Got {len(raw)} initial results")
    
    results = []
    event_count = 0

    for idx, score in raw:
        opp = OPPS[idx]
        opp_type = opp.get("type")
        logger.info(f"Processing result {idx}: type={opp_type}")

        # Double-check event filtering
        if opp_type == "event":
            event_count += 1
            logger.info(f"Skipping event (double-check) - {event_count} events found so far")
            continue

        # 2) Cost filter
        cost = opp.get("cost")
        if max_cost is not None and cost is not None and cost > max_cost:
            logger.info(f"Skipping due to cost: {cost} > {max_cost}")
            continue

        # 3) Geographic filter
        if location_scope == "noevent":
            # Skip events in noevent mode (triple-check)
            if opp_type == "event":
                logger.info("Skipping event in noevent mode (triple-check)")
                continue
        elif location_scope != "nationwide":
            opp_state = opp.get("state")
            opp_city  = opp.get("city")
            lat, lon  = opp.get("latitude"), opp.get("longitude")

            # If the opportunity has *no* location info at all, let it pass
            if not (opp_state or opp_city or (lat is not None and lon is not None)):
                logger.info("No location info, passing through")
                pass

            # Otherwise enforce the chosen scope
            elif location_scope == "states":
                if not states:
                    logger.info("No states specified, skipping")
                    continue
                # state match?
                if opp_state in states:
                    logger.info(f"State match: {opp_state}")
                    pass
                # city-fallback?
                elif any(
                    opp_city in CITIES_BY_STATE.get(s, [])
                    for s in states
                ):
                    logger.info(f"City match in states: {opp_city}")
                    pass
                else:
                    logger.info("No state or city match, skipping")
                    continue

            elif location_scope == "cities":
                # blank-city also passes
                if opp_city and opp_city not in cities:
                    logger.info(f"City not in list: {opp_city}")
                    continue

            elif location_scope == "radius":
                # blank-lat/lon also passes
                if lat is not None and lon is not None:
                    if not center or radius_miles is None:
                        logger.info("Missing center or radius")
                        continue
                    if haversine(center[0], center[1], lat, lon) > radius_miles:
                        logger.info("Outside radius")
                        continue

            elif location_scope == "International":
                # only exclude those with U.S. tags
                if opp_state or opp_city:
                    logger.info("Has US location, skipping")
                    continue

        # 4) Deadline filter with 2-day buffer
        if deadline_before and opp.get("deadline"):
            opp_date    = parse_date(opp["deadline"]).date()
            min_allowed = deadline_before + timedelta(days=2)
            if opp_date < min_allowed:
                logger.info(f"Deadline too early: {opp_date} < {min_allowed}")
                continue

        # passed all filters
        logger.info(f"Adding result: {opp_type} - {opp.get('title')}")
        results.append((opp, score))

    # sort by FAISS score (no boosting) and return top_k items
    results.sort(key=lambda x: x[1], reverse=True)
    final_results = [opp for opp, _ in results[:top_k]]
    logger.info(f"Found {event_count} events, returning {len(final_results)} final results")
    return final_results

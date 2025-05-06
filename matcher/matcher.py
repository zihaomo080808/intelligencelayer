# matcher/matcher.py
import json
import math
from datetime import date, timedelta
from dateutil.parser import parse as parse_date
from .vector_store import search

# Load opportunities and U.S. city→state mapping
OPPS = [json.loads(line) for line in open("data/opportunities.jsonl")]
with open("data/us_cities_by_state.json") as f:
    CITIES_BY_STATE = json.load(f)


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
    location_scope: str = "nationwide",  # "nationwide"| "states"| "cities"| "radius"| "International"
    states: list[str] = None,            # e.g. ["NY","PA"]
    cities: list[str] = None,            # e.g. ["New York","Boston"]
    center: tuple[float, float] = None,   # e.g. (40.7128, -74.0060)
    radius_miles: float = None,           # e.g. 50
    # --- deadline filter ---
    deadline_before: date = None
):
    """
    Returns up to `top_k` opportunities filtered by type, cost, location, and deadlines.
    - location_scope="nationwide": no geographic filtering (includes blanks)
    - for other scopes, blank-location opps still pass through
    """
    raw = search(user_embedding, top_k * 2)
    results = []

    for idx, score in raw:
        opp = OPPS[idx]

        # 1) Type filter
        if only_type and opp.get("type") != only_type:
            continue

        # 2) Cost filter
        cost = opp.get("cost")
        if max_cost is not None and cost is not None and cost > max_cost:
            continue

        # 3) Geographic filter — only if not "nationwide"
        if location_scope != "nationwide":
            opp_state = opp.get("state")
            opp_city  = opp.get("city")
            lat, lon  = opp.get("latitude"), opp.get("longitude")

            # If the opportunity has *no* location info at all, let it pass
            if not (opp_state or opp_city or (lat is not None and lon is not None)):
                pass

            # Otherwise enforce the chosen scope
            elif location_scope == "states":
                if not states:
                    continue
                # state match?
                if opp_state in states:
                    pass
                # city-fallback?
                elif any(
                    opp_city in CITIES_BY_STATE.get(s, [])
                    for s in states
                ):
                    pass
                else:
                    continue

            elif location_scope == "cities":
                # blank-city also passes
                if opp_city and opp_city not in cities:
                    continue

            elif location_scope == "radius":
                # blank-lat/lon also passes
                if lat is not None and lon is not None:
                    if not center or radius_miles is None:
                        continue
                    if haversine(center[0], center[1], lat, lon) > radius_miles:
                        continue

            elif location_scope == "International":
                # only exclude those with U.S. tags
                if opp_state or opp_city:
                    continue

            # unknown scope → no further filtering

        # 4) Deadline filter with 2-day buffer
        if deadline_before and opp.get("deadline"):
            opp_date    = parse_date(opp["deadline"]).date()
            min_allowed = deadline_before + timedelta(days=2)
            if opp_date < min_allowed:
                continue

        # passed all filters
        results.append((opp, score))

    # sort by FAISS score (no boosting) and return top_k items
    results.sort(key=lambda x: x[1], reverse=True)
    return [opp for opp, _ in results[:top_k]]

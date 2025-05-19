import os
from supabase import create_client, Client
from config import settings  # Make sure your config.py is imported

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

def match_opportunities(
    user_id,
    embedding,  # list of 1536 floats
    top_k=5,
    only_type=None,
    max_cost=None,
    deadline_before=None,
    location_scope='noevent',
    center_lon=None,
    center_lat=None,
    radius_miles=None
):
    params = {
        "p_user_id": user_id,
        "p_embedding": embedding,
        "p_top_k": top_k,
        "p_only_type": only_type,
        "p_max_cost": max_cost,
        "p_deadline_before": deadline_before,
        "p_location_scope": location_scope,
        "p_center_lon": center_lon,
        "p_center_lat": center_lat,
        "p_radius_miles": radius_miles,
    }
    # Remove None values (Supabase RPC doesn't like them)
    params = {k: v for k, v in params.items() if v is not None}
    # Call the RPC function
    result = supabase.rpc("match_opportunities", params).execute()
    return result.data

# Example usage:
# matches = match_opportunities(user_id, user_embedding, top_k=5)
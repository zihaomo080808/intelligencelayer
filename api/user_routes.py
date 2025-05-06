# api/user_routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from profiles.profiles import get_profile, update_profile
from classifier.model import predict_stance
from embeddings.embedder import get_embedding
from matcher.matcher import match_items
from generator.generator import generate_recommendation

router = APIRouter()

class ProfileIn(BaseModel):
    user_id: str
    bio: str
    location: Optional[str] = None   # ← new

class ProfileOut(BaseModel):
    user_id: str
    stances: List[str]
    location: Optional[str] = None   # ← new

class RecOut(BaseModel):
    recommendations: str

@router.post("/profile", response_model=ProfileOut)
async def create_profile(inp: ProfileIn):
    # 1) classify
    stances = predict_stance(inp.bio)

    # 2) build embedding from bio + location (if provided)
    text_to_embed = inp.bio
    if inp.location:
        text_to_embed = f"{inp.bio}\n\nLocation: {inp.location}"
    embedding = get_embedding(text_to_embed)

    # 3) store profile (now including location)
    await update_profile(
        user_id=inp.user_id,
        bio=inp.bio,
        stances=stances,
        embedding=embedding,
        location=inp.location       # ← pass it through
    )

    return {
        "user_id": inp.user_id,
        "stances": stances,
        "location": inp.location
    }

@router.get("/recommend/{user_id}", response_model=RecOut)
async def recommend(user_id: str):
    prof = await get_profile(user_id)
    if not prof:
        raise HTTPException(404, "Profile not found")

    # 4) match items, automatically filtering by the user's city if available
    if prof.location:
        # treat location as a city-filter
        items = match_items(
            user_embedding=prof.embedding,
            stances=prof.stances,
            only_type=None,
            location_scope="cities",
            cities=[prof.location]
        )
    else:
        # no location → nationwide
        items = match_items(
            user_embedding=prof.embedding,
            stances=prof.stances,
            only_type=None
        )

    # 5) generate the final recommendation text
    rec = generate_recommendation(
        {"user_id": prof.user_id, "stances": prof.stances, "location": prof.location},
        items
    )
    return {"recommendations": rec}

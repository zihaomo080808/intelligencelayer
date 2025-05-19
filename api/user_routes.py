# api/user_routes.py
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi import Depends

from profiles.profiles import get_profile, update_profile, record_feedback
from classifier.model import predict_stance
from embeddings.embedder import get_embedding
from generator.generator import generate_recommendation
from database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import UserRecommendation
from matcher.supabase_matcher import match_opportunities

router = APIRouter()
logger = logging.getLogger(__name__)

class ProfileIn(BaseModel):
    user_id: str
    username: Optional[str] = None
    bio: str
    location: Optional[str] = None

class ProfileOut(BaseModel):
    user_id: str
    username: Optional[str] = None
    stances: List[str]
    location: Optional[str] = None

class RecOut(BaseModel):
    recommendations: str

class FeedbackIn(BaseModel):
    user_id: str
    item_id: str
    feedback_type: str  # 'like' or 'skip'

@router.post("/profile", response_model=ProfileOut)
async def create_profile(inp: ProfileIn):
    try:
        # Get stances from bio
        stances = predict_stance(inp.bio)
        if not stances:
            logger.warning("Empty stances returned. Using default stances.")
            if "ai" in inp.bio.lower() or "machine learning" in inp.bio.lower():
                stances.append("ai")
            if "social impact" in inp.bio.lower() or "positive impact" in inp.bio.lower():
                stances.append("social_impact")

        # Build embedding from bio + location
        text_to_embed = f"{inp.bio}\n\nLocation: {inp.location}" if inp.location else inp.bio
        embedding = get_embedding(text_to_embed)

        # Store profile
        await update_profile(
            user_id=inp.user_id,
            username=inp.username,
            bio=inp.bio,
            stances=stances,
            embedding=embedding,
            location=inp.location
        )

        return {
            "user_id": inp.user_id,
            "username": inp.username,
            "stances": stances,
            "location": inp.location
        }
    except Exception as e:
        logger.error(f"Error creating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recommend/{user_id}", response_model=RecOut)
async def recommend(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        # Get user profile
        prof = await get_profile(user_id, db)
        if not prof:
            return {"recommendations": "Please create a profile first."}

        # Validate embedding
        if not prof.embedding or (isinstance(prof.embedding, list) and len(prof.embedding) == 0):
            return {"recommendations": "Please update your profile with bio information."}

        # Get recommendations
        items = await match_opportunities(
            user_id=prof.user_id,
            user_embedding=prof.embedding,
            stances=prof.stances,
            top_k=3
        )

        # Generate recommendation text
        profile_data = {"user_id": prof.user_id, "stances": prof.stances, "location": prof.location}
        rec = generate_recommendation(profile_data, items)
        return {"recommendations": rec}

    except Exception as e:
        logger.error(f"Error in recommend: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def handle_feedback(
    feedback: FeedbackIn,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Record feedback
        await record_feedback(
            db=db,
            user_id=feedback.user_id,
            item_id=feedback.item_id,
            feedback_type=feedback.feedback_type
        )

        # Update recommendation status
        recommendation_status = "liked" if feedback.feedback_type == "like" else "skipped"
        
        # Check if recommendation exists
        query = select(UserRecommendation).where(
            UserRecommendation.user_id == feedback.user_id,
            UserRecommendation.item_id == feedback.item_id
        )
        result = await db.execute(query)
        recommendation = result.scalars().first()

        if recommendation:
            # Update existing recommendation
            stmt = update(UserRecommendation).where(
                UserRecommendation.user_id == feedback.user_id,
                UserRecommendation.item_id == feedback.item_id
            ).values(status=recommendation_status)
            await db.execute(stmt)
        else:
            # Create new recommendation
            new_recommendation = UserRecommendation(
                user_id=feedback.user_id,
                item_id=feedback.item_id,
                status=recommendation_status
            )
            db.add(new_recommendation)

        await db.commit()
        return {"status": "success", "message": "Feedback recorded"}
        
    except Exception as e:
        logger.error(f"Error recording feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

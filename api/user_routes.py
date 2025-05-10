# api/user_routes.py
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi import Depends

from profiles.profiles import get_profile, update_profile, record_feedback
from classifier.model import predict_stance
from embeddings.embedder import get_embedding
from matcher.matcher import match_items, match_items_with_history, OPPS
from generator.generator import generate_recommendation
from database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import UserRecommendation

router = APIRouter()
logger = logging.getLogger(__name__)

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

class FeedbackIn(BaseModel):
    user_id: str
    item_id: str
    feedback_type: str  # 'like' or 'skip'

@router.post("/profile", response_model=ProfileOut)
async def create_profile(inp: ProfileIn):
    # 1) classify
    try:
        stances = predict_stance(inp.bio)
        if not stances:
            logger.warning("Empty stances returned. Using default stances.")
            # Extract keywords from bio to create some basic stances
            if "ai" in inp.bio.lower() or "machine learning" in inp.bio.lower():
                stances.append("ai")
            if "social impact" in inp.bio.lower() or "positive impact" in inp.bio.lower():
                stances.append("social_impact")
    except Exception as e:
        logger.error(f"Error predicting stance: {str(e)}")
        stances = []

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
async def recommend(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        # Get the user profile
        prof = await get_profile(user_id, db)
        if not prof:
            # For testing purpose, return a dummy response
            return {"recommendations": "This is a test recommendation for a user that doesn't exist. Please create a profile first."}

        # Check if profile has embedding
        if prof.embedding is None or (isinstance(prof.embedding, list) and len(prof.embedding) == 0) or (hasattr(prof.embedding, 'size') and prof.embedding.size == 0):
            # For testing purpose, return a dummy response
            return {"recommendations": "This user profile has no embedding. Please update the profile with bio information."}

        try:
            # Find new recommendations using history filtering (avoid showing the same opportunities)
            items = await match_items_with_history(
                user_id=prof.user_id,
                user_embedding=prof.embedding,
                stances=prof.stances,
                top_k=3  # Get 3 recommendations
            )

            # If no items were found, fallback to sample items
            if not items:
                logger.warning(f"No new recommendations found for user {user_id}, using fallback items")
                items = [{
                    "title": "AI for Good Hackathon",
                    "description": "A virtual hackathon focused on developing AI solutions for social impact challenges.",
                    "url": "https://example.com/ai-hackathon"
                },
                {
                    "title": "Machine Learning Conference",
                    "description": "Annual conference on machine learning and AI technologies.",
                    "url": "https://example.com/ml-conference"
                },
                {
                    "title": "Data Science Bootcamp",
                    "description": "Intensive training program for data science professionals.",
                    "url": "https://example.com/ds-bootcamp"
                }]

        except Exception as e:
            # Log the error but continue with a default recommendation
            logger.error(f"Error matching items: {str(e)}")

            # Use a sample item if matching fails
            items = [{
                "title": "AI for Good Hackathon",
                "description": "A virtual hackathon focused on developing AI solutions for social impact challenges.",
                "url": "https://example.com/ai-hackathon"
            }]

        try:
            # 5) generate the final recommendation text
            profile_data = {"user_id": prof.user_id, "stances": prof.stances, "location": prof.location}
            # Log what we're sending to the generator
            logger.info(f"Sending profile to generator: {profile_data}")
            logger.info(f"Sending items to generator: {items}")
            
            rec = generate_recommendation(profile_data, items)
            return {"recommendations": rec}
            
        except Exception as e:
            # Log the error and return a default message
            logger.error(f"Error generating recommendation: {str(e)}")
            
            # Fallback response
            return {
                "recommendations": "Based on your profile, here are some opportunities that might interest you:\n\n" + 
                                  "\n".join([f"- {item.get('title', 'Opportunity')}: {item.get('description', 'No description')} ({item.get('url', 'No URL')})" for item in items[:3]])
            }
            
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in recommend: {str(e)}")
        return {"recommendations": f"An error occurred while generating recommendations: {str(e)}. This is a test response."}

@router.post("/feedback")
async def handle_feedback(
    feedback: FeedbackIn,
    db: AsyncSession = Depends(get_db)
):
    """
    Record user feedback for an item and update their embedding.
    """
    try:
        # Get the item embedding from the opportunities
        item_embedding = None
        for opp in OPPS:
            if opp.get("id") == feedback.item_id and "embedding" in opp:
                item_embedding = opp["embedding"]
                break

        # Make sure the embedding is a list for ARRAY(Float) column
        if item_embedding:
            if not isinstance(item_embedding, list):
                item_embedding = list(item_embedding)

        # Record the feedback in UserFeedback table
        await record_feedback(
            db=db,
            user_id=feedback.user_id,
            item_id=feedback.item_id,
            feedback_type=feedback.feedback_type,
            item_embedding=item_embedding
        )

        # Update the recommendation status in UserRecommendation table
        recommendation_status = "liked" if feedback.feedback_type == "like" else "skipped"

        # First check if a recommendation record exists
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
            # Create a new recommendation record if none exists
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
        raise HTTPException(
            status_code=500,
            detail=f"Error recording feedback: {str(e)}"
        )

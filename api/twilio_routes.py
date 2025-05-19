# api/twilio_routes.py
import logging
from datetime import datetime
from fastapi import APIRouter, Form, Request, Response, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from sqlalchemy.ext.asyncio import AsyncSession

from profiles.profiles import get_profile, update_profile
from classifier.model import predict_stance
from embeddings.embedder import get_embedding
from generator.generator import generate_recommendation
from database.session import get_db
from config import settings
from matcher.supabase_matcher import match_opportunities

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()

# Default stances to apply to all new users
DEFAULT_STANCES = ["startup-interested", "tech-positive", "Mission-Driven"]

# Helper function to validate Twilio requests
async def validate_twilio_request(request: Request) -> bool:
    """Validates that incoming requests are from Twilio"""
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    request_url = str(request.url)
    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    form_dict = {key: value for key, value in form_data.items()}
    return validator.validate(request_url, form_dict, signature)

@router.post("/sms")
async def handle_sms(
    request: Request,
    From: str = Form(...),  # Phone number of sender
    Body: str = Form(...),  # Message content
    City: Optional[str] = Form(None)  # Optional location data from Twilio
):
    # Validate the request is from Twilio
    if not settings.DEBUG:
        is_valid = await validate_twilio_request(request)
        if not is_valid:
            return Response("Invalid request", status_code=403)
    
    resp = MessagingResponse()
    user_id = From
    profile = await get_profile(user_id)
    
    if not profile:
        # New user - create profile
        predicted_stances = predict_stance(Body)
        stances = list(set(predicted_stances + DEFAULT_STANCES))
        text_to_embed = f"{Body}\n\nLocation: {City}" if City else Body
        embedding = get_embedding(text_to_embed)
        
        await update_profile(
            user_id=user_id,
            bio=Body,
            stances=stances,
            embedding=embedding,
            location=City
        )
        
        resp.message("Welcome! I've created your profile based on your message.")
    else:
        if Body.lower().startswith("update:"):
            # Update profile
            new_bio = Body[7:].strip()
            predicted_stances = predict_stance(new_bio)
            stances = list(set(predicted_stances + DEFAULT_STANCES))
            text_to_embed = f"{new_bio}\n\nLocation: {profile.location}" if profile.location else new_bio
            embedding = get_embedding(text_to_embed)

            await update_profile(
                user_id=user_id,
                bio=new_bio,
                stances=stances,
                embedding=embedding,
                location=profile.location
            )
            
            resp.message("Your profile has been updated! Text me again for new recommendations.")
        else:
            # Generate recommendations
            items = match_opportunities(
                user_embedding=profile.embedding,
                stances=profile.stances,
                only_type=None,
                location_scope="cities" if profile.location else "noevent",
                cities=[profile.location] if profile.location else None
            )
            
            rec = generate_recommendation(
                {"user_id": profile.user_id, "stances": profile.stances, "location": profile.location},
                items
            )
            
            resp.message(rec)
    
    return Response(content=str(resp), media_type="application/xml")
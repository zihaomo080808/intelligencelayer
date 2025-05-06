# api/twilio_routes.py
from fastapi import APIRouter, Form, Request, Response
from typing import Optional
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
import os

from profiles.profiles import get_profile, update_profile
from classifier.model import predict_stance
from embeddings.embedder import get_embedding
from matcher.matcher import match_items
from generator.generator import generate_recommendation
from config import settings

router = APIRouter()

# Default stances to apply to all new users
DEFAULT_STANCES = ["startup-interested", "tech-positive", "Mission-Driven"]

# Helper function to validate Twilio requests
async def validate_twilio_request(request: Request) -> bool:
    """Validates that incoming requests are from Twilio"""
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    
    # Get the request URL and POST data
    request_url = str(request.url)
    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    
    # Convert form data to dict
    form_dict = {}
    for key, value in form_data.items():
        form_dict[key] = value
        
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
    
    # Create a response object
    resp = MessagingResponse()
    
    # Use phone number as user_id
    user_id = From
    
    # Check if this is an existing user
    profile = await get_profile(user_id)
    
    if not profile:
        # New user - create profile
        predicted_stances = predict_stance(Body)
        
        # Combine predicted stances with default stances
        # Using set to avoid duplicates
        stances = list(set(predicted_stances + DEFAULT_STANCES))
        
        # Build embedding from message content and city if available
        text_to_embed = Body
        if City:
            text_to_embed = f"{Body}\n\nLocation: {City}"
        embedding = get_embedding(text_to_embed)
        
        # Store new profile
        await update_profile(
            user_id=user_id,
            bio=Body,
            stances=stances,
            embedding=embedding,
            location=City
        )
        
        # Welcome message
        resp.message("Welcome! I've created your profile based on your message.")
    else:
        # Existing user - generate recommendations
        if Body.lower().startswith("update:"):
            # Update profile if message starts with "update:"
            new_bio = Body[7:].strip()  # Remove "update:" prefix
            
            # Get stances from the new bio
            predicted_stances = predict_stance(new_bio)
            
            # Ensure default stances are preserved
            stances = list(set(predicted_stances + DEFAULT_STANCES))
            
            # Build embedding
            text_to_embed = new_bio
            location = profile.location
            if location:
                text_to_embed = f"{new_bio}\n\nLocation: {location}"
            embedding = get_embedding(text_to_embed)
            
            # Update profile
            await update_profile(
                user_id=user_id,
                bio=new_bio,
                stances=stances,
                embedding=embedding,
                location=location
            )
            
            resp.message("Your profile has been updated! Text me again for new recommendations.")
        else:
            # Generate recommendations based on existing profile
            if profile.location:
                # Filter by location if available
                items = match_items(
                    user_embedding=profile.embedding,
                    stances=profile.stances,
                    only_type=None,
                    location_scope="cities",
                    cities=[profile.location]
                )
            else:
                items = match_items(
                    user_embedding=profile.embedding,
                    stances=profile.stances,
                    only_type=None
                )
                
            # Generate recommendation text
            rec = generate_recommendation(
                {"user_id": profile.user_id, "stances": profile.stances, "location": profile.location},
                items
            )
            
            # Send recommendation via SMS
            resp.message(rec)
    
    return Response(content=str(resp), media_type="application/xml") 
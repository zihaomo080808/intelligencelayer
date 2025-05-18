import logging
import json
import os
from typing import Dict, Any, Optional, List, Union
from openai import AsyncOpenAI
from config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
from database.session import get_db
from database.models import UserProfile
from perplexity_client import query_user_background

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
logger.info(f"OPENAI_API_KEY set?: {bool(settings.OPENAI_API_KEY)}")
logger.info(f"OPENAI_API_KEY length: {len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0}")

try:
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=20.0
    )
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")
    # Create the client anyway - we'll handle errors during the API call
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# Define the user profile schema - adjust as needed for your application
USER_PROFILE_SCHEMA = {
    "username": "string",  # Changed from "name" to "username" to match database field
    "location": "string",
    "education": "string",
    "occupation": "string",
    "current_projects": "list_of_strings",
    "interests": "list_of_strings",
    "skills": "list_of_strings",
    "goals": "list_of_strings",
    "bio": "string"
}

# System prompt for information extraction
SYSTEM_PROMPT = f"""
You are a helpful AI assistant responsible for extracting structured user profile information from free-form text responses during onboarding.
Extract all possible information from the user's message and format it according to the following schema:

{json.dumps(USER_PROFILE_SCHEMA, indent=2)}

Follow these rules:
1. For fields where no information is provided, use null.
2. Make reasonable inferences for ambiguous information but don't invent facts.
3. For username, extract only their first name if possible (not their full name).
4. For location, extract the most detailed location information available.
5. For list fields, include all relevant items mentioned.
6. Keep all responses concise.

Respond with ONLY a valid JSON object - no explanations or additional text.
"""

async def extract_profile_info(user_message: str, step: int = 0) -> Dict[str, Any]:
    """
    Extract structured profile information from a user message using OpenAI API
    
    Args:
        user_message: The free-form message from the user
        step: The current onboarding step (0 = name, 1 = background, 2 = interests)
        
    Returns:
        Dictionary containing extracted profile information
    """
    try:
        # Create a user-specific message based on onboarding step
        user_specific_prompt = user_message
        if step == 0:
            # First step (name)
            user_specific_prompt = f"My name is {user_message}"
        elif step == 1:
            # Second step (location, education, occupation)
            user_specific_prompt = f"I'm located in {user_message} and that's where I'm from, was educated, and what I'm currently doing."
        elif step == 2:
            # Third step (interests)
            user_specific_prompt = f"My interests include {user_message}"

        logger.info(f"Extracting profile info from message (step {step}): {user_message[:50]}...")
        
        # Call the OpenAI API
        response = await client.chat.completions.create(
            model=settings.CLASSIFIER_MODEL or "gpt-3.5-turbo", # Use a simpler model for cost efficiency
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_specific_prompt}
            ],
        )
        
        # Extract the response
        content = response.choices[0].message.content.strip()
        logger.info(f"Received extraction response (first 100 chars): {content[:100]}...")
        
        # Parse the JSON response
        try:
            profile_data = json.loads(content)
            logger.info(f"Successfully parsed profile data with {len(profile_data)} fields")
            return profile_data
        except json.JSONDecodeError as json_err:
            logger.error(f"Error parsing JSON from API response: {str(json_err)}")
            # Try to extract just the JSON part if there's extra text
            if '{' in content and '}' in content:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_content = content[json_start:json_end]
                try:
                    profile_data = json.loads(json_content)
                    logger.info(f"Successfully parsed profile data after cleanup with {len(profile_data)} fields")
                    return profile_data
                except:
                    pass
            
            # Return empty result if parsing fails
            return {}
        
    except Exception as e:
        logger.error(f"Error extracting profile info: {str(e)}")
        return {}

def merge_profile_updates(existing_profile: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge new profile data into an existing profile
    
    Args:
        existing_profile: The existing user profile
        new_data: New data to merge in
        
    Returns:
        Updated profile with merged data
    """
    merged = existing_profile.copy()
    
    # Merge each field, handling null values and lists appropriately
    for key, value in new_data.items():
        # Skip null/None values
        if value is None:
            continue
            
        # Handle list fields
        if isinstance(value, list) and key in ['interests', 'skills', 'current_projects', 'goals']:
            # Initialize if not exists
            if key not in merged or not merged[key]:
                merged[key] = []
                
            # Add new items that don't already exist
            for item in value:
                if item and item not in merged[key]:
                    merged[key].append(item)
        # Handle string fields - only update if we have a value and the existing one is empty
        elif isinstance(value, str) and value.strip():
            if key not in merged or not merged[key]:
                merged[key] = value
    
    return merged

async def process_onboarding_message(
    message: str,
    step: int,
    current_profile: Dict[str, Any],
    user_id: str,
    db: AsyncSession
) -> tuple[Dict[str, Any], str, bool]:
    """
    Process an onboarding message and update the user profile
    
    Args:
        message: The user's message
        step: The current onboarding step (0 = username, 1 = background, 2 = interests)
        current_profile: The existing user profile
        user_id: The user's ID
        db: Database session
        
    Returns:
        Tuple of (updated_profile, next_question, is_complete)
    """
    try:
        # Extract profile information
        extracted_info = await extract_profile_info(message, step)
        logger.info(f"Extracted info: {extracted_info}")
        
        # Merge with current profile
        updated_profile = {**current_profile, **extracted_info}
        logger.info(f"Updated profile: {updated_profile}")
        
        # If this is the final step, generate bio and embedding
        if step == 2:  # Final step
            # Generate bio using Perplexity
            bio = await query_user_background(updated_profile)
            if bio:
                updated_profile['bio'] = bio
            
            # Generate embedding
            if updated_profile.get('bio'):
                embedding = await get_embedding(updated_profile['bio'])
                if embedding:
                    updated_profile['embedding'] = embedding
        
        # Save to database
        try:
            # Check if profile exists
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            
            if profile:
                # Update existing profile
                for key, value in updated_profile.items():
                    setattr(profile, key, value)
            else:
                # Create new profile
                profile = UserProfile(
                    user_id=user_id,
                    username=updated_profile.get('username'),  # Use username directly
                    bio=updated_profile.get('bio'),
                    location=updated_profile.get('location'),
                    stances=updated_profile.get('stances', {}),
                    embedding=updated_profile.get('embedding')
                )
                db.add(profile)
            
            await db.commit()
            logger.info(f"Profile saved to database for user {user_id}")
        except Exception as db_error:
            import traceback
            db_stack_trace = traceback.format_exc()
            logger.error(f"Error saving profile to database: {str(db_error)}")
            logger.error(f"Database operation stack trace: {db_stack_trace}")
            logger.error(f"User ID: {user_id}, Profile data: {updated_profile}")
            # Continue even if database save fails, but log comprehensive information
        
        # Determine next question and completion status
        next_question = ""
        is_complete = False
        
        if step == 0:  # After username
            next_question = "Great! Could you tell me a bit about your background? Where are you from, what's your education, and what do you do?"
        elif step == 1:  # After background
            next_question = "Thanks! What are your main interests and what kind of opportunities are you looking for?"
        elif step == 2:  # After interests
            is_complete = True
            next_question = "Thanks for sharing all this information! Your profile is now complete."
        
        return updated_profile, next_question, is_complete
        
    except Exception as e:
        import traceback
        stack_trace = traceback.format_exc()
        logger.error(f"Error processing onboarding message: {str(e)}")
        logger.error(f"Stack trace: {stack_trace}")
        # Re-raise with more detailed information
        error_msg = f"Error in process_onboarding_message: {str(e)}\nStep: {step}\nUser ID: {user_id}"
        raise Exception(error_msg) from e

async def generate_bio(profile: Dict[str, Any]) -> str:
    """Generate a bio using OpenAI"""
    try:
        # Create a prompt for bio generation
        prompt = f"""Generate a concise, engaging bio for a user with the following profile:
        Name: {profile.get('name', 'User')}
        Location: {profile.get('location', 'Unknown')}
        Education: {profile.get('education', 'Not specified')}
        Occupation: {profile.get('occupation', 'Not specified')}
        Interests: {', '.join(profile.get('interests', []))}
        
        The bio should be 1-2 sentences, professional but friendly."""
        
        response = await client.chat.completions.create(
            model=settings.GENERATOR_MODEL or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional bio writer."},
                {"role": "user", "content": prompt}
            ],
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating bio: {str(e)}")
        return None

async def get_embedding(text: str) -> List[float]:
    """Get embedding for text using OpenAI"""
    try:
        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL or "text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        return None

# Function for parsing the username from a greeting message (first message)
async def extract_name_from_greeting(message: str) -> str:
    """
    Extract just the username from a greeting message
    
    Args:
        message: The user's first message
        
    Returns:
        Extracted username or empty string
    """
    extracted_info = await extract_profile_info(message, 0)
    return extracted_info.get('username', '')

# API endpoint handlers for Flask/FastAPI integration
async def handle_profile_extraction(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a profile extraction request from the API
    
    Args:
        request_data: The request data containing message and step
        
    Returns:
        Dictionary with extracted profile information
    """
    message = request_data.get('message', '')
    step = request_data.get('step', 0)
    existing_profile = request_data.get('profile', {})
    
    if not message:
        return {'error': 'No message provided'}
    
    updated_profile = await process_onboarding_message(message, step, existing_profile, '')
    return {'profile': updated_profile}
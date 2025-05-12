"""
onboarding_messages.py - Handles intelligent parsing of user onboarding messages

This module uses the OpenAI API to extract structured information from user messages
during the onboarding process. It helps create detailed user profiles from free-form
text responses.
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List, Union
from openai import OpenAI
from config import settings

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
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=20.0
    )
    logger.info("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")
    # Create the client anyway - we'll handle errors during the API call
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Define the user profile schema - adjust as needed for your application
USER_PROFILE_SCHEMA = {
    "name": "string",
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
3. For name, extract only their first name if possible (not their full name).
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
        response = client.chat.completions.create(
            model=settings.CLASSIFIER_MODEL or "gpt-3.5-turbo", # Use a simpler model for cost efficiency
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_specific_prompt}
            ],
            temperature=0.2,  # Lower temperature for more consistent results
            max_tokens=500
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

async def process_onboarding_message(message: str, step: int, existing_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process a message during the onboarding flow and update the user profile
    
    Args:
        message: The user's message
        step: The current onboarding step
        existing_profile: The existing user profile (if any)
        
    Returns:
        Updated user profile
    """
    if existing_profile is None:
        existing_profile = {}
    
    # Extract profile info from the message
    extracted_info = await extract_profile_info(message, step)
    
    # Merge the extracted info into the existing profile
    updated_profile = merge_profile_updates(existing_profile, extracted_info)
    
    return updated_profile

# Function for parsing the name from a greeting message (first message)
async def extract_name_from_greeting(message: str) -> str:
    """
    Extract just the name from a greeting message
    
    Args:
        message: The user's first message
        
    Returns:
        Extracted name or empty string
    """
    extracted_info = await extract_profile_info(message, 0)
    return extracted_info.get('name', '')

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
    
    updated_profile = await process_onboarding_message(message, step, existing_profile)
    return {'profile': updated_profile}
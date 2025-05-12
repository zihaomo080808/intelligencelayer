"""
perplexity_client.py - Client for interacting with the Perplexity API

This module provides functions to query the Perplexity API for generating background
information about users based on their profile data.
"""

import logging
import json
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

# API URL
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

async def query_user_background(profile: Dict[str, Any]) -> str:
    """
    Query Perplexity API to generate a comprehensive background for a user based on their profile

    Args:
        profile: Dictionary containing user profile information
        
    Returns:
        Generated background information as a string
    """
    try:
        # Extract profile elements
        name = profile.get('name', 'the user')
        location = profile.get('location', '')
        education = profile.get('education', '')
        occupation = profile.get('occupation', '')
        current_projects = profile.get('current_projects', [])
        interests = profile.get('interests', [])
        skills = profile.get('skills', [])
        
        # Format profile data
        current_projects_str = ", ".join(current_projects) if current_projects else ""
        interests_str = ", ".join(interests) if interests else ""
        skills_str = ", ".join(skills) if skills else ""
        
        # Create prompt for the API
        prompt = f"""
        Based on the following information about {name}, search for this person on the internet, generating a detailed, professional bio 
        that would describe this person well. Include relevant details to create a coherent, 
        contextual background story:
        
        Name: {name}
        Location: {location}
        Education: {education}
        Occupation: {occupation}
        Current Projects: {current_projects_str}
        Interests: {interests_str}
        Skills: {skills_str}
        
        Make the bio factual based on the provided information. Avoid embellishment or making 
        up additional details not supported by the information provided. The bio should be 
        5-6 sentences and professional in tone.
        """
        
        # Prepare the API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}"
        }
        
        payload = {
            "model": "mixtral-8x7b-instruct",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that creates professional, factual user bios based on profile information."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 300
        }
        
        # Send the request
        logger.info(f"Sending query to Perplexity API for user '{name}'")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                PERPLEXITY_API_URL,
                headers=headers,
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Perplexity API error: {response.status_code} - {response.text}")
                return ""
                
            result = response.json()
            bio = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            logger.info(f"Generated bio for {name} ({len(bio)} chars)")
            return bio
            
    except Exception as e:
        logger.error(f"Error querying Perplexity API: {str(e)}")
        return ""
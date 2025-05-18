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
        can you search on the internet and generate a 5-6 sentence personal bio for me a person called Zikang Jiang who has this profile:
        
        Name: {name}
        Location: {location}
        Education: {education}
        Occupation: {occupation}
        Current Projects: {current_projects_str}
        Interests: {interests_str}
        Skills: {skills_str}

        I want the bio to be accurate and comprehensive to the point that any info the person logs online it will be included. You do not have to use complete sentences, output in the most efficient but still understandable way (example format: time, experience, location, results with data, important details)
        """
        
        # Prepare the API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}"
        }
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that creates professional, factual user bios based on profile information."},
                {"role": "user", "content": prompt}
            ],
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
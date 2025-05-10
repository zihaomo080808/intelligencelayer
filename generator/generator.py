# generator/generator.py
from openai import OpenAI
import logging
import os
from config import settings
from .cot_prompt import build_prompt
import random

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
# Add debugging information
logger.info(f"OPENAI_API_KEY length: {len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0}")
logger.info(f"GENERATOR_MODEL: {settings.GENERATOR_MODEL}")
client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_recommendation(profile, items):
    msgs = build_prompt(profile, items)
    try:
        logger.info(f"Calling OpenAI API for text generation with model: {settings.GENERATOR_MODEL}")
        logger.info(f"Messages being sent (first prompt): {msgs[0]['content'] if msgs else 'No messages'}")

        try:
            # Minimal parameters for compatibility with o4-mini model
            resp = client.chat.completions.create(
                model=settings.GENERATOR_MODEL,
                messages=msgs
            )

            if not resp or not resp.choices or len(resp.choices) == 0:
                logger.error("Empty response from OpenAI API")
                raise ValueError("Empty response from OpenAI API")

            content = resp.choices[0].message.content
            logger.info(f"OpenAI API Response (first 100 chars): {content[:100] if content else 'Empty response'}...")

            if not content or len(content.strip()) < 10:
                raise ValueError("Response content too short or empty")

            return content

        except Exception as api_error:
            logger.error(f"API Error: {str(api_error)}")
            raise api_error
            
    except Exception as e:
        logger.error(f"Error generating recommendation: {str(e)}")
        
        # Generate a default recommendation based on profile and items
        try:
            stances = profile.get('stances', [])
            location = profile.get('location', '')
            
            greetings = [
                "Yo, check this out.",
                "This perfect for you.",
                "Yo, dont miss this one.",
                "Found this."
            ]
            default_rec = f"{random.choice(greetings)}\n\n"

            if location:
                default_rec += f"You're in {location} right, \n\n"
            for item in items[:1]:
                default_rec += f"look at this: {item.get('title', 'Event')}: {item.get('description', 'No description')} ({item.get('url', '#')})\n"
                
            logger.info(f"Generated default recommendation")
            return default_rec
        except Exception as fallback_error:
            logger.error(f"Even fallback recommendation failed: {str(fallback_error)}")
            return f"We're sorry, but we couldn't generate personalized recommendations at this time. Please try again later."

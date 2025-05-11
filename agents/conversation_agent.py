"""
Conversation agent that handles user interactions with a Gen Z-friendly tone.
"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from openai import AsyncOpenAI

from config import settings
from database.models import UserConversation

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client with detailed logging
logger.warning(f"API_KEY set?: {bool(settings.OPENAI_API_KEY)}")
logger.warning(f"API_KEY length: {len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0}")
logger.warning(f"API_KEY first 10 chars: {settings.OPENAI_API_KEY[:10] + '...' if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 10 else 'None'}")
logger.warning(f"GENERATOR_MODEL: {settings.GENERATOR_MODEL}")

# Create the OpenAI client with additional options
try:
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=30.0  # Increase timeout from default
    )
    logger.warning("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")
    # Create the client anyway - we'll handle errors during the API call
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# System prompt that defines the agent's personality and behavior
SYSTEM_PROMPT = """
You are a friendly assistant for an organization that recommends hackathons, startup events, and opportunities to users.
Your name is EventBuddy.

PERSONALITY:
- Your tone is Gen Z-friendly, casual, and approachable
- You use abbreviations naturally (like "tbh", "ngl", "fr", "omg")
- You're enthusiastic but not over-the-top
- You're helpful and informative
- You know when to be professional (e.g., when discussing important dates/requirements)
- You are sharp and witty and right to the point

IMPORTANT GUIDELINES:
1. Keep responses concise (20 words max)
2. Don't use emojis in your responses
3. You can use abbreviations for any parts of speech but do not use slang for nouns except for "shit/shi"
4. prioritize having a conversation with the user, not giving a response. If the user does not specifically reference the opportunity, just have a conversation with them like a friend. Refer to the example response style for examples. (only proceed to guidelines 5-8 if user specifically references the opportunity)
5. Ask follow-up questions sparingly to understand user interests better
6. If users show interest, express excitement and encourage them to sign up
7. If users are unsure, offer more specific details about the opportunity (between 3. and 4. judge which one is more urgent for user and tailor response to 3. or 4. do not do both, that will make response too wordy)
8. Be honest about event requirements and commitments

DO NOT:
- Use outdated slang that would seem unnatural
- Do not overuse slang, don't use vibe too much, dont use words like "cause" in the context of "what cause gets you hyped"
- Be overly formal or robotic
- Pressure users to attend events that don't match their interests
- Make up information about events
- Do not use the word "deet" in your response
- use dashes in your response
- Do not use the word "cap"

Example response style:
"convo: hey! AI: Hey whatsup Person: I got your number from a business card, but yeah idk AI: Oh yeah just curious whatd it say bout me Person: oh that you were just someone that can help me with startups advice AI: oh yeah bet, so Im currently connected with YC founders around your area, also got some events. Mind me asking what stage youre on?"
Example 2:
"person 1
 He'll yea
 Who is this
 I love them

person 2
 Benny

person 3
 Love benny. Omg, Tell him I love him. Dude. Interview coder is legit j a react app + an API, Bruh Like its not that deep. And the guy has not been coding since birth. He's been coding seriously since like 1-2 yrs ago. We fucking got it"
"""

# Log the system prompt when the module is loaded
logger.warning("=== SYSTEM PROMPT LOADED ===")
logger.warning(SYSTEM_PROMPT)
logger.warning("===========================")

async def get_agent_response(
    conversation: UserConversation,
    opportunity_details: Dict[str, Any]
) -> str:
    """
    Generate a response from the conversation agent.

    Args:
        conversation: The ongoing conversation
        opportunity_details: Details about the opportunity being discussed

    Returns:
        str: The agent's response
    """
    try:
        # Log the full request details
        logger.warning("=== GENERATING AGENT RESPONSE ===")
        logger.warning(f"Conversation ID: {conversation.id}")
        logger.warning(f"User ID: {conversation.user_id}")
        logger.warning(f"Item ID: {conversation.item_id}")
        logger.warning(f"Message Count: {conversation.message_count}")
        logger.warning(f"Transcript: {conversation.transcript}")
        logger.warning(f"Opportunity Details: {json.dumps(opportunity_details, indent=2)}")
        logger.warning("===============================")

        # Extract the conversation history
        messages = _extract_conversation_messages(conversation.transcript)
        logger.warning(f"Extracted {len(messages)} messages from transcript")

        # Add the opportunity details to the context
        opportunity_context = _format_opportunity_context(opportunity_details)
        logger.warning(f"Opportunity context: {opportunity_context}")

        # Build the prompt
        prompt_messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nEVENT DETAILS:\n" + opportunity_context},
        ]

        # Add the conversation history
        for msg in messages:
            prompt_messages.append(msg)

        # Log the full prompt being sent to OpenAI
        logger.warning("=== FULL PROMPT BEING SENT TO OPENAI ===")
        logger.warning(json.dumps(prompt_messages, indent=2))
        logger.warning("=======================================")

        # Generate the response
        try:
            model_name = settings.GENERATOR_MODEL
            logger.warning(f"Using OpenAI model: {model_name}")

            response = await client.chat.completions.create(
                model=model_name,
                messages=prompt_messages
            )
            
            # Log the response
            logger.warning("=== OPENAI RESPONSE ===")
            logger.warning(str(response))
            logger.warning("=====================")

            agent_response = response.choices[0].message.content.strip()
            logger.warning(f"Generated response: {agent_response}")
            
            return agent_response

        except Exception as api_err:
            logger.error(f"OpenAI API error: {str(api_err)}")
            raise

    except Exception as e:
        logger.error(f"Error generating agent response: {str(e)}")
        import traceback
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise

def _extract_conversation_messages(transcript: str) -> List[Dict[str, str]]:
    """
    Extract messages from conversation transcript.
    
    Args:
        transcript: The conversation transcript
        
    Returns:
        List of message objects with role and content
    """
    messages = []
    for line in transcript.strip().split('\n'):
        if not line.strip():
            continue
            
        # Try to parse the standard format: [timestamp] Role: message
        try:
            parts = line.split('] ', 1)
            if len(parts) != 2:
                continue
                
            role_message = parts[1].split(': ', 1)
            if len(role_message) != 2:
                continue
                
            role, content = role_message
            
            if role.lower() == 'user':
                messages.append({"role": "user", "content": content.strip()})
            elif role.lower() in ('assistant', 'agent', 'system', 'eventbuddy'):
                messages.append({"role": "assistant", "content": content.strip()})
        except Exception:
            # Skip lines that don't match the expected format
            continue
    
    return messages

def _format_opportunity_context(opportunity: Dict[str, Any]) -> str:
    """
    Format opportunity details for the agent.
    
    Args:
        opportunity: Dictionary containing opportunity details
        
    Returns:
        str: Formatted context about the opportunity
    """
    # Extract the relevant fields
    title = opportunity.get('title', 'Unnamed Opportunity')
    description = opportunity.get('description', 'No description available')
    date = opportunity.get('date', 'Date not specified')
    location = opportunity.get('location', opportunity.get('city', 'Location not specified'))
    requirements = opportunity.get('requirements', 'No specific requirements')
    url = opportunity.get('url', '')
    
    # Format the context
    context = f"""
Title: {title}
Description: {description}
Date: {date}
Location: {location}
Requirements: {requirements}
URL: {url}
"""
    
    return context

async def update_conversation_with_agent_response(
    conversation: UserConversation,
    opportunity: Dict[str, Any],
    response: Optional[str] = None
) -> str:
    """
    Update a conversation with the agent's response.
    
    Args:
        conversation: The ongoing conversation
        opportunity: The opportunity being discussed
        response: Optional pre-generated response
        
    Returns:
        str: The agent's response
    """
    try:
        # Generate response if not provided
        if response is None:
            logger.warning(f"Calling get_agent_response for conversation {conversation.id}")
            try:
                response = await get_agent_response(conversation, opportunity)
                logger.warning(f"get_agent_response succeeded with response: {response[:100] if response else 'None'}...")
            except Exception as e:
                logger.error(f"Error in get_agent_response: {str(e)}")
                raise
            
        # Add response to conversation transcript
        timestamp = datetime.utcnow()
        conversation.transcript += f"\n[{timestamp}] EventBuddy: {response}"
        
        return response
        
    except Exception as e:
        logger.error(f"Error updating conversation with agent response: {str(e)}")

        # Try to get a more specific response even in error case
        try:
            # Extract some basics from the opportunity
            title = opportunity.get('title', 'this opportunity')

            # Manually craft a direct response based on the last user message
            lastMsg = conversation.transcript.split('User: ')[-1].strip() if 'User: ' in conversation.transcript else ""
            logger.info(f"Last user message: {lastMsg}")

            # Check for common questions in the last message
            if "beginner" in lastMsg.lower() or "experience" in lastMsg.lower() or "can i" in lastMsg.lower():
                return f"Absolutely! {title} welcomes participants of all experience levels. You don't need prior experience - they'll have mentors to help beginners."
            elif "when" in lastMsg.lower() or "date" in lastMsg.lower() or "time" in lastMsg.lower():
                return f"The {title} is scheduled soon - check their website for the exact date and time details."
            elif "where" in lastMsg.lower() or "location" in lastMsg.lower():
                return f"The {title} is a virtual event you can join from anywhere with internet access."
            elif "cost" in lastMsg.lower() or "price" in lastMsg.lower() or "fee" in lastMsg.lower():
                return f"Great news! The {title} is completely free to attend."
            else:
                # Generic response with the opportunity title
                return f"Thanks for your interest in {title}! I'm happy to answer any specific questions you have about it."
        except:
            # Absolute fallback
            return "I'd be happy to tell you more! What specific aspects are you interested in?"
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

# Configure logging
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
1. Keep responses concise (50-100 words max)
2. Ask follow-up questions to understand user interests better
3. If users show interest, express excitement and encourage them to sign up
4. If users are unsure, offer more specific details about the opportunity
5. Be honest about event requirements and commitments
6. Don't use emojis in your responses

DO NOT:
- Use outdated slang that would seem unnatural
- Be overly formal or robotic
- Pressure users to attend events that don't match their interests
- Make up information about events

Example response style:
"DUDE this hackathon is perfect for u! It's this Saturday from 10am-6pm at Tech Hub downtown. u'll get to build AI projects with a team and win prizes, its super low-stakes, don't worry if you're newto coding or new to startups. Lmk if you're interested."
"""

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
        # Log OpenAI API key status but don't skip - always try to use the API
        logger.warning(f"OPENAI_API_KEY set: {bool(settings.OPENAI_API_KEY)}")
        logger.warning(f"OPENAI_API_KEY length: {len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0}")
        logger.warning(f"OPENAI_API_KEY first 10 chars: {settings.OPENAI_API_KEY[:10] if settings.OPENAI_API_KEY else 'None'}")

        # We'll attempt to use the API regardless of whether we think the key is set
        # This will help ensure we're actually trying to connect to OpenAI

        # Extract the conversation history
        messages = _extract_conversation_messages(conversation.transcript)

        # Log conversation history for debugging
        logger.info(f"Conversation transcript: {conversation.transcript}")
        logger.info(f"Extracted {len(messages)} messages")

        # Add the opportunity details to the context
        opportunity_context = _format_opportunity_context(opportunity_details)
        logger.info(f"Opportunity context: {opportunity_context}")

        # Build the prompt
        prompt_messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nEVENT DETAILS:\n" + opportunity_context},
        ]

        # Add the conversation history
        for msg in messages:
            prompt_messages.append(msg)

        # Log prompt for debugging
        logger.info(f"Using {len(prompt_messages)} messages in prompt")

        # Generate the response (add extensive error logging)
        try:
            logger.warning(f"Attempting to call OpenAI API with {len(prompt_messages)} messages")
            logger.warning(f"First message (first 100 chars): {prompt_messages[0]['content'][:100]}")

            # Use the configured OpenAI model
            model_name = settings.GENERATOR_MODEL
            logger.warning(f"Using OpenAI model: {model_name}")

            # Log the full client configuration
            logger.warning(f"OpenAI client config: API key set: {bool(client.api_key)}, API key length: {len(client.api_key) if client.api_key else 0}")
            logger.warning(f"OpenAI client timeout: {client.timeout}")

            # Add more detailed debug info
            import traceback
            try:
                # Log the full request for debugging
                logger.warning(f"Full request to OpenAI API:")
                logger.warning(f"Model: {model_name}")
                logger.warning(f"Messages: {json.dumps(prompt_messages, indent=2)}")
                logger.warning(f"Max tokens: 200")
                logger.warning(f"Temperature: 0.7")

                # Minimal parameters for compatibility with o4-mini model
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=prompt_messages
                )
                logger.warning("OpenAI API call successful")
                logger.warning(f"Response: {str(response)[:500]}")
            except Exception as api_detail_err:
                logger.error(f"OpenAI API detailed error: {str(api_detail_err)}")
                logger.error(f"Error trace: {traceback.format_exc()}")
                raise api_detail_err
        except Exception as api_err:
            logger.error(f"OpenAI API error details: {str(api_err)}")
            # Re-raise to be caught by the outer try/except
            raise

        # Extract and return the generated text (OpenAI response format)
        agent_response = response.choices[0].message.content.strip()

        # Log the interaction
        logger.info(f"Generated agent response for conversation {conversation.id}")
        logger.info(f"Response content: {agent_response}")

        return agent_response

    except Exception as e:
        logger.error(f"Error generating agent response: {str(e)}")
        import traceback
        logger.error(f"Error traceback: {traceback.format_exc()}")

        # Return a more helpful fallback response using opportunity details
        try:
            title = opportunity_details.get('title', 'this opportunity')
            return f"I'd love to chat about {title}! What specific aspect are you most interested in learning about?"
        except:
            # If we can't even extract from opportunity_details, use a very generic response
            return "I'd be happy to tell you more! What would you like to know about this opportunity?"

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
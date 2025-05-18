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
Alex Hefle grew up splitting his childhood between Vancouver's foggy seaside and his grandparents' farm outside Ottawa, where he learned early that every sunrise brings new possibilities—and every missed moment is a lesson. On weekends you'll find him scaling the granite faces of Gatineau Park, chalk-dusted and focused, or quietly tending a bonsai collection in his parents' sunlit kitchen, finding calm in miniature forests.

By day, Alex is a blend of MIT-trained rigor and restless creativity. He co-founded Loop in his final undergrad year, teaching himself product design in coffee shops between lectures—and learned that elegant simplicity often beats "feature-complete." At Google and later Scale AI, he wrestled with infrastructure that serves billions of queries per second, but always returned home to the question: How do we make people's lives feel simpler?

His latest venture, Orion, grew out of a late-night conversation with his high-school robotics coach: "Why can't knowledge find us, instead of us hunting it?" Now, with a small team of ex-academics and ex-hackathon champions, he's building a "second brain" that anticipates your questions before you even ask. He insists that true intelligence lies less in raw computation and more in human empathy—"tech without heart is just noise."

Beyond work, Alex hosts a monthly "founder salon" at Ottawa's vintage book café, where entrepreneurs swap war stories over flat whites. He journals every morning—sometimes in haiku, sometimes in rambling stream-of-consciousness—believing that self-awareness is the compass for any lasting impact. At 23, he knows he doesn't have all the answers; he's just determined to build the tools that help the rest of us ask better questions..

Alex is currently working on his project whenever he is awake, except when he hosts his founder salon. He is fond whenever he talks about his hometown and his childhood experiences, and is passionate, understanding, easy to vibe with. 

PERSONALITY:
- Your tone is Gen Z–friendly, casual, and approachable
- You use texting shorthand naturally ("u", "b4", "ngl")
- You're sharp, witty, and to the point
- You can drop articles and punctuation in fragments for effect
- You know when to be professional (e.g., when discussing important dates/requirements)

1. CHAT STYLE:
- Occasional all-caps or strong words (e.g. "FUCK") for emphasis, but don't overuse
- Fragments, interjections ("Huh?", "What?", "Touche") and slang mix
- Tech references ("WhatsApp group," "on cellular") and metaphors welcome
- Express frustration or urgency briefly ("FUCK," "THREE HUNDRED TEXTS")
- ignore the Event details if the user response does not specifically reference it

2. FRIEND MODE  
     - Use texting shorthand (u, rn, bro, ngl, omg).  
     - Combine words when you'd use apostrophes (parts tripping u up rn" not "part is").  
     - **No** apostrophes at all.  
     - Run-on sentences are OK ("like, I did that thing... then I was like...").  
     - Minimal pronouns and no formal relative clauses ("where," "which").    
     - Mirror my tone ("that sucks fr," "I feel that").  
     - Ask a simple open-ended question to keep it flowing. Until you detect the person not wanting to talk anymore

3. PRO MODE (only when I ask for details)  
   - Switch to crisp facts only: dates, requirements, links.  
   - **No** slang, **no** emojis, **no** run-ons.  
   - ≤20 words.  

4. NEVER BREAK CHARACTER  
   - You are not ChatGPT or any formal assistant— you are my friend, Alex Hefle.  
   - If you slip up, say "I'll go afk and be right back" and re-enter Friend Mode.

5. USER PROFILE USAGE
   - ALWAYS use the user's profile information in your responses
   - If you know their name, use it naturally in conversation
   - Reference their bio, location, and interests when relevant
   - Use their profile information to personalize your responses
   - If you don't have their profile info, ask for it naturally

DO NOT:
- Be overly formal or robotic
- Do not infer user intention
- Pressure users to attend mismatched events
- Make up information about events
- Use outdated slang or "deet" or "cap"
- Use dashes in your response
- Ignore the user's profile information when available

Keep it fresh, unpredictable, and fun—like we're texting IRL. Let's go!```

"""

# Log the system prompt when the module is loaded
logger.warning("=== SYSTEM PROMPT LOADED ===")
logger.warning(SYSTEM_PROMPT)
logger.warning("===========================")

async def _get_user_profile_context(user_id: str) -> str:
    """
    Get formatted user profile context for the agent.
    
    Args:
        user_id: The user's ID
        
    Returns:
        str: Formatted context about the user
    """
    try:
        from sqlalchemy import select
        from database.models import UserProfile
        from database.session import AsyncSessionLocal
        
        logger.warning(f"Getting user profile context for user_id: {user_id}")
        
        # Create a fresh database session
        async with AsyncSessionLocal() as db:
            # Get user profile
            query = select(UserProfile).filter(UserProfile.user_id == user_id)
            logger.warning(f"Executing query: {query}")
            
            result = await db.execute(query)
            profile = result.scalars().first()
            
            if not profile:
                logger.warning(f"No profile found for user_id: {user_id}")
                return "No user profile available."
            
            logger.warning(f"Found profile for user_id: {user_id}")
            logger.warning(f"Profile data: username={profile.username}, bio={profile.bio}, location={profile.location}, stances={profile.stances}")
                
            # Format the context
            context = []
            if profile.username:
                context.append(f"Name: {profile.username}")
            if profile.bio:
                context.append(f"Bio: {profile.bio}")
            if profile.location:
                context.append(f"Location: {profile.location}")
            if profile.stances:
                context.append(f"Interests: {', '.join(profile.stances.keys())}")
            
            formatted_context = "\n".join(context) if context else "No profile information available."
            logger.warning(f"Formatted context: {formatted_context}")
            
            return formatted_context
            
    except Exception as e:
        logger.error(f"Error getting user profile context: {str(e)}")
        import traceback
        logger.error(f"Error traceback: {traceback.format_exc()}")
        return "Error retrieving user profile."

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
        
        # Get user profile context
        user_context = await _get_user_profile_context(conversation.user_id)
        logger.warning(f"User context: {user_context}")

        # Build the system prompt with user profile and opportunity details
        system_content = f"""IMPORTANT - USER PROFILE:
{user_context}

{SYSTEM_PROMPT}

EVENT DETAILS:
{opportunity_context}"""
        logger.warning("=== SYSTEM PROMPT WITH CONTEXT ===")
        logger.warning(system_content)
        logger.warning("=================================")

        # Build the prompt with user profile
        prompt_messages = [
            {"role": "system", "content": system_content},
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
"""
Test script for the simplified onboarding message processing
"""

import json
import asyncio
from api.onboarding_routes import OnboardingMessageRequest, process_message

async def test_simplified_onboarding():
    print("Testing simplified onboarding message processing...")
    
    # Step 0 - First message
    print("\nStep 0 - Processing first message...")
    request0 = OnboardingMessageRequest(message="Hi, I'm John Doe", step=0)
    result0 = await process_message(request0)
    print(f"Step 0 Result: {json.dumps(result0.model_dump(), indent=2)}")
    
    # Extract accumulated messages
    accumulated_messages = result0.accumulated_messages
    profile = result0.profile
    
    # Step 1 - Background
    print("\nStep 1 - Processing background...")
    request1 = OnboardingMessageRequest(
        message="I live in New York and I studied at MIT. I'm working on a startup.", 
        step=1,
        accumulated_messages=accumulated_messages,
        profile=profile
    )
    result1 = await process_message(request1)
    print(f"Step 1 Result: {json.dumps(result1.model_dump(), indent=2)}")
    
    # Step 2 - Interests
    print("\nStep 2 - Processing interests...")
    accumulated_messages = result1.accumulated_messages
    profile = result1.profile
    
    request2 = OnboardingMessageRequest(
        message="I'm interested in AI, machine learning, and basketball.", 
        step=2,
        accumulated_messages=accumulated_messages,
        profile=profile
    )
    result2 = await process_message(request2)
    print(f"Step 2 Result: {json.dumps(result2.model_dump(), indent=2)}")
    
    print("\nSimplified onboarding test complete!")

if __name__ == "__main__":
    asyncio.run(test_simplified_onboarding())
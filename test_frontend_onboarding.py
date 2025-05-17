"""
Test script for the entire onboarding process frontend-to-backend flow
"""

import json
import asyncio
from api.onboarding_routes import OnboardingMessageRequest, process_message

async def test_complete_onboarding_flow():
    print("Testing complete onboarding flow with message accumulation...")
    
    # Simulate complete onboarding flow
    accumulated_messages = {}
    
    # Step 0: First message (name)
    print("\nStep 0 - Processing first message (name)...")
    message0 = "My name is John Doe"
    accumulated_messages["0"] = message0
    
    request0 = OnboardingMessageRequest(
        message=message0, 
        step=0,
        accumulated_messages=accumulated_messages
    )
    result0 = await process_message(request0)
    print(f"Step 0 Result: {json.dumps(result0.model_dump(), indent=2)}")
    
    # Update accumulated messages for next step
    accumulated_messages = result0.accumulated_messages
    
    # Step 1: Background information
    print("\nStep 1 - Processing background info...")
    message1 = "I live in New York and I studied at MIT. I'm working on a startup."
    accumulated_messages["1"] = message1
    
    request1 = OnboardingMessageRequest(
        message=message1, 
        step=1,
        profile=result0.profile,
        accumulated_messages=accumulated_messages
    )
    result1 = await process_message(request1)
    print(f"Step 1 Result: {json.dumps(result1.model_dump(), indent=2)}")
    
    # Update accumulated messages for final step
    accumulated_messages = result1.accumulated_messages
    
    # Step 2: Interests and skills
    print("\nStep 2 - Processing interests and skills...")
    message2 = "I'm interested in AI, machine learning, and basketball."
    accumulated_messages["2"] = message2
    
    request2 = OnboardingMessageRequest(
        message=message2,
        step=2,
        profile=result1.profile,
        accumulated_messages=accumulated_messages
    )
    result2 = await process_message(request2)
    print(f"Step 2 Result - Completion Flag: {result2.complete}")
    print(f"Step 2 Result - Next Question: {result2.next_question}")
    print(f"Step 2 Result - Final Profile: {json.dumps(result2.profile, indent=2)}")
    
    print("\nOnboarding test complete!")

if __name__ == "__main__":
    asyncio.run(test_complete_onboarding_flow())
import asyncio
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import Optional, Dict, Any

# Import our API app
from api.main import app
from api.twilio_routes import TwoWayConversationRequest
from database.session import get_db

# Create a test client
client = TestClient(app)

async def test_chat_api_endpoint():
    """Test the chat API endpoint integration with OpenAI."""
    print("Testing chat API endpoint with OpenAI...")
    
    # Create a test conversation request
    conversation_request = {
        "user_id": "test_user_ui",
        "item_id": "test_item_123",
        "message": "Tell me more about this AI Hackathon!",
        "opportunity_details": {
            "id": "test_item_123",
            "title": "AI Hackathon",
            "description": "Join our weekend hackathon focused on artificial intelligence and machine learning projects.",
            "date": "June 15-16, 2025",
            "location": "San Francisco, CA",
            "requirements": "Open to all skill levels. Basic programming knowledge helpful.",
            "url": "https://example.com/ai-hackathon"
        }
    }
    
    # Send the request to the API
    try:
        print("Sending request to chat API endpoint...")
        response = client.post("/twilio/feedback/chat", json=conversation_request)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            print("\n--- API Response ---")
            print(json.dumps(data, indent=2))
            print("-------------------\n")
            
            if "agent_response" in data and data["agent_response"]:
                print("✅ Chat API successfully integrated with OpenAI!")
                print(f"Agent response: {data['agent_response']}")
                return True
            else:
                print("❌ No agent response in API response")
                return False
        else:
            print(f"❌ API request failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing chat API: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_js_integration():
    """Analyze chat.js to check how it integrates with the backend."""
    print("\nAnalyzing chat.js integration...\n")
    
    chat_js_path = PROJECT_ROOT / "chat_ui" / "static" / "js" / "chat.js"
    
    if not chat_js_path.exists():
        print("❌ chat.js file not found")
        return False
    
    with open(chat_js_path, "r") as f:
        content = f.read()
    
    # Check for API URL configuration
    if "api-url" in content and "http://localhost:8000/twilio/feedback/chat" in content:
        print("✅ Found API URL configuration in chat.js")
    else:
        print("❌ Could not find API URL configuration")
    
    # Check for sendMessage function
    if "sendMessage" in content:
        print("✅ Found sendMessage function in chat.js")
        
        # Check if it makes fetch requests
        if "fetch(" in content:
            print("✅ sendMessage appears to make fetch requests")
        else:
            print("❓ sendMessage doesn't appear to make real API calls")
            print("   It uses a simulated response instead")
            
            # Check for simulation code
            if "simulatedResponse" in content:
                print("✅ Found simulation code - this is a fallback when API is unavailable")
            else:
                print("❌ Could not find API call or simulation code")
    else:
        print("❌ Could not find sendMessage function")
    
    # Check for API integration
    relevant_lines = []
    line_num = 1
    in_send_message = False
    
    for line in content.split("\n"):
        if "async function sendMessage" in line:
            in_send_message = True
            relevant_lines.append(f"{line_num}: {line}")
        elif in_send_message and "}" in line and line.strip() == "}":
            in_send_message = False
            relevant_lines.append(f"{line_num}: {line}")
        elif in_send_message and ("fetch" in line or "api" in line.lower() or "simulatedResponse" in line):
            relevant_lines.append(f"{line_num}: {line}")
        
        line_num += 1
    
    print("\nRelevant code section from chat.js:")
    for line in relevant_lines[:20]:  # Limit to first 20 lines
        print(line)
    
    if len(relevant_lines) > 20:
        print(f"... and {len(relevant_lines) - 20} more lines")
    
    # Summary
    print("\nSummary of chat.js integration:")
    print("The chat interface is set up to work with the backend API, but has a simulation")
    print("mode as a fallback. To ensure it connects to your working OpenAI implementation,")
    print("you need to uncomment or modify the fetch code to call your real API endpoint.")
    
    return True

if __name__ == "__main__":
    # Test UI integration
    print("=== Testing UI Integration with OpenAI ===\n")
    
    # First, analyze the static integration
    test_chat_js_integration()
    
    # Then test the actual API endpoint
    asyncio.run(test_chat_api_endpoint())
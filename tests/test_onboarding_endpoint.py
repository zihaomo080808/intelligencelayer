import asyncio
import aiohttp
import json
import sys

async def test_onboarding_endpoint():
    """Test the onboarding process endpoint directly"""
    
    base_url = "http://localhost:8000"  # Change to match your API server
    endpoint = f"{base_url}/api/onboarding/process"
    
    # Test data - using step 0 (name) as it's simplest
    payload = {
        "message": "My name is John",
        "step": 0,
        "profile": {},
        "user_id": "test_user_123"
    }
    
    print(f"Testing endpoint: {endpoint}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload) as response:
                print(f"Response status: {response.status}")
                
                # Get response content
                try:
                    data = await response.json()
                    print(f"Response data: {json.dumps(data, indent=2)}")
                except:
                    text = await response.text()
                    print(f"Response text: {text}")
                
                # Print headers for debugging
                print("Response headers:")
                for header, value in response.headers.items():
                    print(f"  {header}: {value}")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Allow user to specify a different base URL
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
        asyncio.run(test_onboarding_endpoint(base_url))
    else:
        asyncio.run(test_onboarding_endpoint())
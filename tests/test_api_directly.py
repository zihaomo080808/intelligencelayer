import requests
import json

def test_api_directly():
    """Test the API directly without going through the Flask app"""
    
    url = "http://localhost:8001/api/onboarding/process"
    
    payload = {
        "message": "My name is John",
        "step": 0,
        "profile": {},
        "user_id": "test_user_123"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    print(f"Testing API directly at {url}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        
        print(f"Response status code: {response.status_code}")
        
        try:
            # Try to parse as JSON
            json_data = response.json()
            print(f"Response data: {json.dumps(json_data, indent=2)}")
        except:
            # If not JSON, show raw content
            print(f"Raw response: {response.text}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_api_directly()
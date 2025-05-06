#!/usr/bin/env python
"""
Script to simulate Twilio requests to your local server.
This lets you test the Twilio integration without needing to expose your 
local development server to the internet or having real Twilio messages.

Usage:
1. Make sure your FastAPI server is running locally
2. Run this script:
   python tests/simulate_twilio_request.py

You'll be prompted to enter different fields to construct a test request.
"""

import requests
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import configs
sys.path.append(str(Path(__file__).parent.parent))

from config import settings

# Default server URL
SERVER_URL = "http://localhost:8000"
TWILIO_ENDPOINT = f"{SERVER_URL}/twilio/sms"

def send_test_sms(from_number, message_body, city=None):
    """Simulate a Twilio SMS webhook request to your local server."""
    
    # Create form data that Twilio would send
    form_data = {
        "From": from_number,
        "Body": message_body
    }
    
    if city:
        form_data["City"] = city
    
    print("\n---- Request Details ----")
    print(f"Endpoint: {TWILIO_ENDPOINT}")
    print(f"From: {from_number}")
    print(f"Body: {message_body}")
    if city:
        print(f"City: {city}")
    print("------------------------\n")
    
    try:
        # Send the request
        response = requests.post(TWILIO_ENDPOINT, data=form_data)
        
        # Display the response
        print("---- Response ----")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Try to parse as XML (TwiML)
            response_text = response.text
            print("\nResponse Content (TwiML):")
            print(response_text)
            
            # Extract the message content for easier reading
            import re
            message_match = re.search(r'<Message>(.*?)</Message>', response_text)
            if message_match:
                print("\nExtracted Message Content:")
                print(message_match.group(1))
        else:
            print("\nResponse Content:")
            print(response.text)
            
    except requests.RequestException as e:
        print(f"\nError: {e}")
        print("\nMake sure your FastAPI server is running (uvicorn api.main:app --reload)")

def main():
    """Main interactive function to simulate Twilio requests."""
    print("=== Twilio SMS Simulator ===")
    print("This tool helps you test your Twilio SMS integration locally.")
    
    while True:
        print("\nSelect an option:")
        print("1. Simulate a new user's first message")
        print("2. Simulate an existing user asking for recommendations")
        print("3. Simulate a profile update message")
        print("4. Custom message")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == "1":
            phone = input("\nEnter phone number (e.g. +15551234567): ") or "+15551234567"
            message = input("Enter message (or press Enter for default): ") or "I'm interested in AI startups in healthcare"
            city = input("Enter city (optional): ")
            send_test_sms(phone, message, city)
            
        elif choice == "2":
            phone = input("\nEnter existing phone number: ") or "+15551234567"
            message = input("Enter message (or press Enter for default): ") or "What's new?"
            send_test_sms(phone, message)
            
        elif choice == "3":
            phone = input("\nEnter existing phone number: ") or "+15551234567"
            bio = input("Enter new bio (or press Enter for default): ") or "I'm now interested in fintech and blockchain"
            message = f"update: {bio}"
            send_test_sms(phone, message)
            
        elif choice == "4":
            phone = input("\nEnter phone number: ") or "+15551234567"
            message = input("Enter message: ")
            city = input("Enter city (optional): ")
            send_test_sms(phone, message, city)
            
        elif choice == "5":
            print("\nExiting. Goodbye!")
            break
            
        else:
            print("\nInvalid choice. Please enter a number between 1 and 5.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main() 
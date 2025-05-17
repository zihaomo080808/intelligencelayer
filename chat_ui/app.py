from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# API server configuration
API_SERVER = 'http://localhost:8000'

@app.route('/')
def index():
    """Render the chat interface."""
    return render_template('index.html')

@app.route('/api/conversation', methods=['POST'])
def proxy_conversation():
    """
    Proxy the conversation request to the API server.
    This allows the UI server to forward requests to the API server,
    avoiding CORS issues and providing a single endpoint for the frontend.
    """
    try:
        # Forward the request to the API server
        response = requests.post(
            f"{API_SERVER}/api/conversation",
            json=request.json,
            headers={
                'Content-Type': 'application/json'
            }
        )

        # Return the API response to the client
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        # Handle connection error
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to API server: {str(e)}",
            "response": "Sorry, I couldn't connect to the backend. Please try again later."
        }), 500

@app.route('/twilio/feedback/chat', methods=['POST'])
def proxy_twilio_chat():
    """
    Proxy the twilio chat request to the API server.
    This allows the UI server to forward requests to the Twilio endpoint.
    """
    try:
        # Forward the request to the API server
        response = requests.post(
            f"{API_SERVER}/twilio/feedback/chat",
            json=request.json,
            headers={
                'Content-Type': 'application/json'
            }
        )

        # Return the API response to the client
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        # Handle connection error
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to Twilio API endpoint: {str(e)}",
            "agent_response": "Sorry, I couldn't connect to the backend. Please try again later."
        }), 500

@app.route('/api/onboarding/process', methods=['POST'])
def proxy_onboarding():
    """
    Proxy the onboarding process request to the API server.
    This allows the UI server to forward onboarding requests to the API server.
    """
    try:
        # Forward the request to the API server
        response = requests.post(
            f"{API_SERVER}/api/onboarding/process",
            json=request.json,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )

        # Return the API response to the client
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        # Handle connection error
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to onboarding API: {str(e)}",
            "response": "Sorry, I couldn't connect to the onboarding service. Please try again later."
        }), 500

@app.route('/api/onboarding/profile-info/<user_id>', methods=['GET'])
def proxy_profile_info(user_id):
    """
    Proxy the profile info request to the API server.
    This allows the UI server to forward profile info requests to the API server.
    """
    try:
        # Forward the request to the API server
        response = requests.get(
            f"{API_SERVER}/api/onboarding/profile-info/{user_id}",
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )

        # Return the API response to the client
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        # Handle connection error
        return jsonify({
            "status": "error",
            "message": f"Failed to connect to profile info API: {str(e)}",
            "bio_available": False,
            "embedding_available": False
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5050)
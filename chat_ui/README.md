# EventBuddy Chat UI

A simple web interface that simulates an iMessage-style conversation with the EventBuddy agent.

## Features

- iMessage-style chat interface
- Real-time conversations with the EventBuddy AI
- Settings panel to configure user, event, and API details
- Connects to your API's feedback system

## Prerequisites

- Python 3.7+
- Flask
- Your main API server running (by default on `localhost:8000`)

## Installation

1. Install Flask if you haven't already:
```bash
pip install flask
```

2. Make sure your main API is running:
```bash
cd /Users/zihaomo/scrapers/intelligence_layer
uvicorn api.main:app --reload
```

## Running the Chat UI

1. Start the Flask server:
```bash
cd /Users/zihaomo/scrapers/intelligence_layer/chat_ui
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5050
```

3. The chat interface should be displayed, and you can start chatting with EventBuddy.

## Configuration

Click the gear icon in the top right corner to configure:

- User ID and Item ID for tracking
- API endpoint URL
- Event details that EventBuddy will reference in conversations

## How It Works

1. The UI sends your messages to your API's `/twilio/feedback/chat` endpoint
2. Your API stores the message and generates a response using the Gen Z agent
3. The response is displayed in the chat interface
4. Your feedback system tracks all interactions for future recommendations

## Troubleshooting

- If you get connection errors, make sure your main API is running
- Check browser console for any JavaScript errors
- Verify the API endpoint in settings is correct (default: `http://localhost:8000/twilio/feedback/chat`)
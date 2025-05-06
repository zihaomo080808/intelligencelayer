import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app

# Create a test client
client = TestClient(app)

# Sample data
SAMPLE_PHONE = "+15551234567"
SAMPLE_MESSAGE = "I'm interested in AI startups in healthcare in San Francisco"
SAMPLE_CITY = "San Francisco"
SAMPLE_STANCES = ["AI", "healthcare", "tech-positive"]
SAMPLE_EMBEDDING = [0.1] * 1536  # Assuming 1536-dim embeddings
SAMPLE_ITEMS = [
    {
        "title": "HealthTech AI",
        "description": "AI-powered healthcare platform",
        "url": "https://example.com/1"
    },
    {
        "title": "MedBot",
        "description": "Medical chatbot for diagnosis",
        "url": "https://example.com/2"
    }
]
SAMPLE_RECOMMENDATION = "Here are your recommendations: 1. HealthTech AI, 2. MedBot"

# Default stances defined in the application code
DEFAULT_STANCES = ["startup-interested", "tech-positive", "Mission-Driven"]

@patch("api.twilio_routes.get_profile")
@patch("api.twilio_routes.predict_stance")
@patch("api.twilio_routes.get_embedding")
@patch("api.twilio_routes.update_profile")
def test_new_user_sms(
    mock_update_profile, mock_get_embedding, mock_predict_stance, mock_get_profile
):
    """Test handling a new user SMS message"""
    # Setup mocks
    mock_get_profile.return_value = None  # No existing profile
    mock_predict_stance.return_value = SAMPLE_STANCES
    mock_get_embedding.return_value = SAMPLE_EMBEDDING
    mock_update_profile.return_value = None
    
    # Send mock Twilio request
    response = client.post(
        "/twilio/sms",
        data={
            "From": SAMPLE_PHONE,
            "Body": SAMPLE_MESSAGE,
            "City": SAMPLE_CITY
        }
    )
    
    # Assert response
    assert response.status_code == 200
    assert "Welcome" in response.text  # Welcome message should be in the response
    
    # Verify default stances were added
    # The stances should be a combination of predicted stances and default stances
    expected_stances = list(set(SAMPLE_STANCES + DEFAULT_STANCES))
    mock_update_profile.assert_called_once()
    call_args = mock_update_profile.call_args[1]
    assert "stances" in call_args
    assert sorted(call_args["stances"]) == sorted(expected_stances)


@patch("api.twilio_routes.get_profile")
@patch("api.twilio_routes.match_items")
@patch("api.twilio_routes.generate_recommendation")
def test_existing_user_recommendation(
    mock_generate_recommendation, mock_match_items, mock_get_profile
):
    """Test handling an existing user SMS message requesting recommendations"""
    # Setup mocks
    mock_profile = MagicMock()
    mock_profile.user_id = SAMPLE_PHONE
    mock_profile.stances = SAMPLE_STANCES
    mock_profile.embedding = SAMPLE_EMBEDDING
    mock_profile.location = SAMPLE_CITY
    
    mock_get_profile.return_value = mock_profile
    mock_match_items.return_value = SAMPLE_ITEMS
    mock_generate_recommendation.return_value = SAMPLE_RECOMMENDATION
    
    # Send mock Twilio request
    response = client.post(
        "/twilio/sms",
        data={
            "From": SAMPLE_PHONE,
            "Body": "What's new?",
        }
    )
    
    # Assert response
    assert response.status_code == 200
    assert SAMPLE_RECOMMENDATION in response.text
    
    # Verify mocks were called with expected args
    mock_get_profile.assert_called_once_with(SAMPLE_PHONE)
    mock_match_items.assert_called_once()
    mock_generate_recommendation.assert_called_once()


@patch("api.twilio_routes.get_profile")
@patch("api.twilio_routes.predict_stance")
@patch("api.twilio_routes.get_embedding")
@patch("api.twilio_routes.update_profile")
def test_profile_update(
    mock_update_profile, mock_get_embedding, mock_predict_stance, mock_get_profile
):
    """Test handling a profile update message"""
    # Setup mocks
    mock_profile = MagicMock()
    mock_profile.user_id = SAMPLE_PHONE
    mock_profile.stances = SAMPLE_STANCES
    mock_profile.embedding = SAMPLE_EMBEDDING
    mock_profile.location = SAMPLE_CITY
    
    mock_get_profile.return_value = mock_profile
    mock_predict_stance.return_value = ["new", "stances"]
    mock_get_embedding.return_value = SAMPLE_EMBEDDING
    mock_update_profile.return_value = None
    
    # New bio text
    update_message = "update: I'm now interested in fintech startups"
    
    # Send mock Twilio request
    response = client.post(
        "/twilio/sms",
        data={
            "From": SAMPLE_PHONE,
            "Body": update_message,
        }
    )
    
    # Assert response
    assert response.status_code == 200
    assert "updated" in response.text.lower()
    
    # Verify default stances were preserved in update
    expected_stances = list(set(["new", "stances"] + DEFAULT_STANCES))
    mock_update_profile.assert_called_once()
    call_args = mock_update_profile.call_args[1]
    assert "stances" in call_args
    assert sorted(call_args["stances"]) == sorted(expected_stances)


@patch("api.twilio_routes.validate_twilio_request")
@patch("api.twilio_routes.get_profile")
@patch("api.twilio_routes.predict_stance")
@patch("api.twilio_routes.get_embedding")
@patch("api.twilio_routes.update_profile")
def test_twilio_request_validation(
    mock_update_profile, mock_get_embedding, mock_predict_stance, mock_get_profile, mock_validate
):
    """Test that Twilio request validation works"""
    # Mock to avoid database connection
    mock_get_profile.return_value = None
    mock_predict_stance.return_value = SAMPLE_STANCES
    mock_get_embedding.return_value = SAMPLE_EMBEDDING
    mock_update_profile.return_value = None
    
    # First test: validation passes
    mock_validate.return_value = True
    
    response = client.post(
        "/twilio/sms",
        data={
            "From": SAMPLE_PHONE,
            "Body": SAMPLE_MESSAGE,
        }
    )
    assert response.status_code == 200
    
    # Second test: validation fails
    mock_validate.return_value = False
    
    with patch("api.twilio_routes.settings") as mock_settings:
        mock_settings.DEBUG = False  # Ensure debug mode is off
        
        response = client.post(
            "/twilio/sms",
            data={
                "From": SAMPLE_PHONE,
                "Body": SAMPLE_MESSAGE,
            }
        )
        assert response.status_code == 403  # Should be forbidden 
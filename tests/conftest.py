import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Override environment variables for testing
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
os.environ["DEBUG"] = "True"

# Sample mock data for tests
MOCK_LABELS = ["tech-positive", "startup-interested", "AI", "healthcare", "fintech", "blockchain", "Mission-Driven"]

# Create test database fixtures
@pytest.fixture(scope="session")
def test_db():
    """
    Set up a test database for the test session.
    
    This would normally create a test database, but for the sake of simplicity,
    we're just setting the DATABASE_URL to point to a test database.
    
    In a real-world scenario, you would:
    1. Create a test database
    2. Run migrations
    3. Seed with test data
    4. Yield control to tests
    5. Drop the test database after tests
    """
    # Nothing to do here - we've already set DATABASE_URL
    # But in a real project, you'd do database setup and teardown
    pass

@pytest.fixture(autouse=True)
async def setup_test_db(test_db):
    """
    Reset the test database before each test.
    
    This is a simplified version - in a real project,
    you would truncate tables or restore from a snapshot
    between tests to ensure isolation.
    """
    # This would be where you'd reset your test database
    # before each test to ensure test isolation
    pass

# Patch database modules to prevent actual database connections
@pytest.fixture(scope="session", autouse=True)
def mock_database():
    """
    Mock database connections to prevent tests from actually connecting to a database
    """
    # Create patch for database-related functions
    with patch("profiles.profiles.get_profile") as mock_get_profile, \
         patch("profiles.profiles.update_profile") as mock_update_profile, \
         patch("database.Base") as mock_base, \
         patch("database.engine") as mock_engine, \
         patch("database.AsyncSessionLocal") as mock_session:
        
        # Configure mocks
        mock_get_profile.return_value = None
        mock_update_profile.return_value = None
        
        # Apply patch to database validation check
        with patch("database.is_valid_postgresql_url", return_value=True):
            yield {
                "get_profile": mock_get_profile,
                "update_profile": mock_update_profile,
                "Base": mock_base,
                "engine": mock_engine,
                "AsyncSessionLocal": mock_session
            }

# Patch classifier modules to avoid file dependencies
@pytest.fixture(scope="session", autouse=True)
def mock_classifier():
    """
    Mock classifier functions to avoid file dependencies
    """
    with patch("classifier.model.load_labels") as mock_load_labels, \
         patch("classifier.model.LABELS", MOCK_LABELS), \
         patch("classifier.model.predict_stance") as mock_predict_stance:
        
        # Configure mocks
        mock_load_labels.return_value = MOCK_LABELS
        mock_predict_stance.return_value = ["AI", "healthcare", "tech-positive"]
        
        yield {
            "load_labels": mock_load_labels,
            "predict_stance": mock_predict_stance
        }

# Patch OpenAI and embeddings functions
@pytest.fixture(scope="session", autouse=True)
def mock_ai_services():
    """
    Mock AI services to avoid actual API calls during tests
    """
    with patch("embeddings.embedder.get_embedding") as mock_get_embedding, \
         patch("matcher.matcher.match_items") as mock_match_items, \
         patch("generator.generator.generate_recommendation") as mock_generate_recommendation:
        
        # Configure mocks
        mock_get_embedding.return_value = [0.1] * 1536  # Default embedding
        mock_match_items.return_value = [
            {
                "title": "Test Startup",
                "description": "This is a test startup",
                "url": "https://example.com"
            }
        ]
        mock_generate_recommendation.return_value = "Here are your recommendations..."
        
        yield {
            "get_embedding": mock_get_embedding,
            "match_items": mock_match_items,
            "generate_recommendation": mock_generate_recommendation
        } 
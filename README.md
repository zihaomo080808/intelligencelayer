# Intelligence Layer - AI Recommender System

This project is an AI-powered recommendation system that matches users with opportunities based on their interests, skills, and preferences. It includes a chat interface, profile management, and intelligent recommendation generation.

## Project Structure

### Core Components

#### API and Routes (`/api`)
- `main.py` - Main FastAPI application setup and route registration
- `onboarding_routes.py` - Handles user onboarding process with profile creation
- `session_routes.py` - Manages user sessions
- `user_routes.py` - User profile management and recommendation endpoints
- `twilio_routes.py` - Integration with Twilio for messaging
- `feedback_routes.py` - Handles user feedback on recommendations

#### Agent System (`/agents`)
- `conversation_agent.py` - Manages the conversation flow with users through a chat interface

#### Database (`/database`)
- `base.py` - Database connection setup and base models
- `models.py` - SQLAlchemy ORM models for the application
- `session.py` - Session management utilities

#### Embedding System (`/embeddings`)
- `embedder.py` - Generates vector embeddings for user profiles and opportunities

#### Classifier (`/classifier`)
- `model.py` - Classifies user text to extract stances/preferences
- `train.py` - Training script for the classifier model
- `evaluate.py` - Evaluation script for the classifier

#### Matcher (`/matcher`)
- `supabase_matcher.py` - Matches users with opportunities based on embedding similarity

#### Generator (`/generator`)
- `generator.py` - Generates personalized recommendation text
- `cot_prompt.py` - Chain-of-thought prompting templates for recommendation generation

#### Feedback System (`/feedback`)
- `rocchio.py` - Implements the Rocchio algorithm for embedding updates based on feedback
- `enhanced_rocchio.py` - Enhanced version of the algorithm
- `conversation.py` - Processes conversation feedback

#### Profiles (`/profiles`)
- `profiles.py` - Manages user profile data, including CRUD operations
- `enhanced_profiles.py` - Enhanced profile management functionality

#### Ingest (`/ingest`)
- Tools for ingesting and processing opportunity data
- `main.py` - Main entry point for ingestion
- `processors.py` - Data processing utilities
- `tasks.py` - Background tasks for data processing

#### Web UI (`/chat_ui`)
- `app.py` - Web server for the chat interface
- `static/js/chat.js` - Frontend JavaScript for the chat interface
- `templates/index.html` - HTML template for the web UI

### Configuration
- `config.py` - Application configuration settings
- `schema.sql` - Database schema definition
- `init-pgvector.sql` - PostgreSQL vector extension setup

### Tests (`/tests`)
- Comprehensive test suite for various components
- `test_conversation_agent.py`, `test_twilio_handler.py`, etc.
- `conftest.py` - Pytest fixtures

### Docker Configuration
- `Dockerfile` - Main application container
- `docker-compose.yml` - Multi-container setup
- `custom-postgres/` - Custom PostgreSQL setup with pgvector

## Key Features

1. **User Profiling**
   - Creates embeddings from user bios and interests
   - Classifies user stances/preferences from text

2. **Opportunity Matching**
   - Vector similarity search to find relevant opportunities
   - Personalized recommendations based on user profile

3. **Feedback Loop**
   - Rocchio algorithm updates user embeddings based on feedback
   - Improves recommendations over time

4. **Conversation Interface**
   - Interactive chat interface for user engagement
   - Handles multi-step onboarding process

5. **Integration with External Services**
   - Twilio for messaging
   - Perplexity API for enhanced bio generation

## Frontend Chat Interface

The frontend chat interface (`chat_ui/static/js/chat.js`) includes a lot of functions that are designed for the mature project, with features like:
- User onboarding
- Profile management
- Recommendation display
- Feedback collection
- Settings management

Note that some functionalities in the chat.js might not yet be fully implemented in the backend, especially in the Twilio API routes. The system is designed to be progressively enhanced as development continues.

## Getting Started

1. Set up the PostgreSQL database with pgvector:
   ```
   docker-compose up -d custom-postgres
   ```

2. Run database migrations:
   ```
   alembic upgrade head
   ```

3. Start the application:
   ```
   docker-compose up
   ```

4. Access the web interface at http://localhost:8000

## Database Schema

The system uses a PostgreSQL database with pgvector extension for storing and querying embeddings. Key tables include:
- `profiles` - User profile information and embeddings
- `opportunities` - Available opportunities with embeddings
- `user_feedback` - User feedback on recommendations
- `user_conversations` - Conversation history

## Development

When developing, note that the frontend in chat.js contains functionality that might be ahead of or different from what's implemented in the backend. Ensure that when adding new features, both frontend and backend implementations are aligned.
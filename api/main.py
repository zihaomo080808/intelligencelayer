# api/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.user_routes import router as user_router
from api.twilio_routes import router as twilio_router
from api.feedback_routes import router as feedback_router
from database.base import init_db
from profiles.profiles import router as profiles_router
from ingest.routes import router as ingest_router

app = FastAPI(title="AI Startup Recommender")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# async create tables on startup
@app.on_event("startup")
async def on_startup():
    await init_db()

app.include_router(user_router, prefix="/api")
app.include_router(twilio_router, prefix="/twilio")
app.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(feedback_router, prefix="/api", tags=["feedback"])

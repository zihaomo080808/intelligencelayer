# api/main.py
from fastapi import FastAPI
from api.user_routes import router as user_router
from api.twilio_routes import router as twilio_router
from profiles.profiles import init_db

app = FastAPI(title="AI Startup Recommender")

# async create tables on startup
@app.on_event("startup")
async def on_startup():
    await init_db()

app.include_router(user_router, prefix="/api")
app.include_router(twilio_router, prefix="/twilio")

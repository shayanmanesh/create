from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import random
import time
from datetime import datetime

app = FastAPI(
    title="Create.ai API (Demo)",
    description="AI-powered content creation platform - Demo Mode",
    version="1.0.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Demo data
DEMO_STATS = {
    "total_creations": 150234,
    "active_users": 45678,
    "revenue_today": 125678.90,
    "trending_challenges": [
        "#AIMoviePoster",
        "#PetAdventureAI", 
        "#AITimeMachine",
        "#DreamJobAI",
        "#AILoveStory"
    ]
}

class CreateRequest(BaseModel):
    input_type: str
    text_input: Optional[str] = None
    creation_type: str = "general"
    language: str = "en"

@app.get("/")
async def root():
    return {
        "message": "Welcome to Create.ai API (Demo Mode)",
        "version": "1.0.0",
        "status": "operational",
        "note": "Running in demo mode without real AI models"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": "demo",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/stats")
async def get_stats():
    """Get platform statistics with live increments"""
    # Add some randomness for demo effect
    return {
        "total_creations": DEMO_STATS["total_creations"] + random.randint(0, 100),
        "active_users": DEMO_STATS["active_users"] + random.randint(0, 50),
        "revenue_today": DEMO_STATS["revenue_today"] + random.uniform(0, 1000),
        "trending_challenges": DEMO_STATS["trending_challenges"]
    }

@app.get("/api/pricing")
async def get_pricing():
    """Get current pricing with surge status"""
    surge_active = random.random() > 0.7  # 30% chance of surge
    surge_multiplier = 1.2 if surge_active else 1.0
    
    return {
        "pricing": {
            "single": {
                "price": 0.99,
                "current_price": 0.99 * surge_multiplier,
                "surge_active": surge_active,
                "name": "Single Creation"
            },
            "basic": {
                "price": 9.99,
                "current_price": 9.99,
                "surge_active": False,
                "name": "Basic Monthly"
            },
            "pro_pack": {
                "price": 49.99,
                "current_price": 49.99,
                "surge_active": False,
                "name": "Pro Pack"
            }
        },
        "surge_active": surge_active,
        "surge_multiplier": surge_multiplier
    }

@app.post("/api/creations/create")
async def create_content(request: CreateRequest):
    """Demo content creation endpoint"""
    creation_id = f"demo_{int(time.time() * 1000)}"
    
    return {
        "creation_id": creation_id,
        "status": "processing",
        "content_url": None,
        "share_links": {
            "tiktok": f"https://create.ai/share/{creation_id}?platform=tiktok",
            "instagram": f"https://create.ai/share/{creation_id}?platform=instagram",
            "twitter": f"https://create.ai/share/{creation_id}?platform=twitter",
            "youtube": f"https://create.ai/share/{creation_id}?platform=youtube"
        },
        "processing_time": 0,
        "price": 0.99
    }

@app.get("/api/creations/{creation_id}")
async def get_creation(creation_id: str):
    """Get creation details (demo)"""
    # Simulate processing completion after a few seconds
    return {
        "creation_id": creation_id,
        "status": "completed",
        "content_urls": {
            "thumbnail": "https://via.placeholder.com/800x600",
            "video": "https://example.com/demo-video.mp4"
        },
        "metadata": {
            "creation_type": "general",
            "processing_time": 12.5,
            "created_at": datetime.utcnow().isoformat()
        },
        "share_count": random.randint(0, 1000),
        "views": random.randint(100, 10000)
    }

@app.get("/api/challenges/trending")
async def get_trending_challenges():
    """Get trending challenges"""
    challenges = [
        {
            "id": "1",
            "title": "AI Movie Poster Challenge",
            "description": "Create your dream movie poster with AI!",
            "hashtag": "#AIMoviePoster",
            "participant_count": 15234,
            "creation_count": 28456,
            "ends_at": "2024-12-31T23:59:59",
            "is_official": True,
            "is_boosted": True,
            "leaderboard": [
                {"username": "creator123", "score": 9852},
                {"username": "aiartist", "score": 8234},
                {"username": "viral_maker", "score": 7123}
            ],
            "is_participating": False
        },
        {
            "id": "2",
            "title": "Pet Adventure AI",
            "description": "Turn your pet into an epic adventure hero!",
            "hashtag": "#PetAdventureAI",
            "participant_count": 12456,
            "creation_count": 19234,
            "ends_at": "2024-12-31T23:59:59",
            "is_official": True,
            "is_boosted": False,
            "leaderboard": [
                {"username": "petlover99", "score": 8234},
                {"username": "doggoart", "score": 7456},
                {"username": "catcreator", "score": 6234}
            ],
            "is_participating": False
        }
    ]
    
    return {"challenges": challenges}

@app.post("/api/auth/register")
async def register(email: str, password: str, username: str):
    """Demo registration"""
    return {
        "access_token": "demo_token_12345",
        "token_type": "bearer",
        "user": {
            "id": "demo_user_1",
            "email": email,
            "username": username,
            "subscription_tier": "free",
            "creations_remaining": 3
        }
    }

@app.post("/api/auth/login")
async def login(email: str, password: str):
    """Demo login"""
    return {
        "access_token": "demo_token_12345",
        "token_type": "bearer",
        "user": {
            "id": "demo_user_1",
            "email": email,
            "username": "demouser",
            "subscription_tier": "free",
            "creations_remaining": 3
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
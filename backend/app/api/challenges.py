from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from app.services.database import get_db
from app.models import User, Challenge, ChallengeParticipation, Creation
from app.api.auth import get_current_user
import uuid
from sqlalchemy import func, desc

router = APIRouter()


class CreateChallenge(BaseModel):
    title: str
    description: str
    hashtag: str
    theme_prompts: List[str]
    duration_days: int = 7
    prize_description: Optional[str] = None


class JoinChallenge(BaseModel):
    creation_id: str


class ChallengeResponse(BaseModel):
    id: str
    title: str
    description: str
    hashtag: str
    participant_count: int
    creation_count: int
    ends_at: datetime
    leaderboard: List[Dict]
    is_participating: bool


# Predefined viral challenge templates
CHALLENGE_TEMPLATES = {
    "ai_movie_poster": {
        "title": "AI Movie Poster Challenge",
        "description": "Create your dream movie poster with AI!",
        "hashtag": "#AIMoviePoster",
        "theme_prompts": [
            "Create a movie poster for your life story",
            "Design a poster for a movie about your pet",
            "Make a horror movie poster of your daily commute"
        ]
    },
    "pet_adventure": {
        "title": "Pet Adventure AI",
        "description": "Turn your pet into an epic adventure hero!",
        "hashtag": "#PetAdventureAI",
        "theme_prompts": [
            "Your pet as a superhero",
            "Pet's secret double life",
            "Pet saves the world"
        ]
    },
    "ai_time_machine": {
        "title": "AI Time Machine",
        "description": "See yourself in different time periods!",
        "hashtag": "#AITimeMachine",
        "theme_prompts": [
            "You in the Renaissance",
            "Your future self in 2124",
            "You as a 1920s celebrity"
        ]
    },
    "dream_job": {
        "title": "Dream Job AI",
        "description": "Visualize yourself in your dream career!",
        "hashtag": "#DreamJobAI",
        "theme_prompts": [
            "You as a astronaut",
            "Your dream office",
            "You winning a Nobel Prize"
        ]
    },
    "ai_love_story": {
        "title": "AI Love Story",
        "description": "Create your perfect romantic scene!",
        "hashtag": "#AILoveStory",
        "theme_prompts": [
            "Your dream date location",
            "Meeting your soulmate",
            "Your fairy tale wedding"
        ]
    }
}


@router.post("/create", response_model=ChallengeResponse)
async def create_challenge(
    challenge_data: CreateChallenge,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create a new challenge"""
    
    # Check if hashtag already exists
    existing = await db.query(Challenge).filter(
        Challenge.hashtag == challenge_data.hashtag
    ).first()
    
    if existing:
        raise HTTPException(400, "Hashtag already in use")
    
    # Create challenge
    challenge = Challenge(
        id=str(uuid.uuid4()),
        creator_id=current_user.id,
        title=challenge_data.title,
        description=challenge_data.description,
        hashtag=challenge_data.hashtag,
        theme_prompts=challenge_data.theme_prompts,
        prize_description=challenge_data.prize_description,
        starts_at=datetime.utcnow(),
        ends_at=datetime.utcnow() + timedelta(days=challenge_data.duration_days),
        created_at=datetime.utcnow()
    )
    
    db.add(challenge)
    await db.commit()
    
    return await format_challenge_response(challenge, current_user.id, db)


@router.get("/templates")
async def get_challenge_templates():
    """Get predefined challenge templates"""
    return {
        "templates": CHALLENGE_TEMPLATES
    }


@router.post("/launch-template/{template_id}")
async def launch_template_challenge(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Launch a challenge from template"""
    
    template = CHALLENGE_TEMPLATES.get(template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    
    # Check if this template challenge already exists
    existing = await db.query(Challenge).filter(
        Challenge.hashtag == template["hashtag"]
    ).first()
    
    if existing:
        # Return existing challenge
        return await format_challenge_response(existing, current_user.id, db)
    
    # Create new challenge from template
    challenge = Challenge(
        id=str(uuid.uuid4()),
        creator_id=current_user.id,
        title=template["title"],
        description=template["description"],
        hashtag=template["hashtag"],
        theme_prompts=template["theme_prompts"],
        is_official=True,
        starts_at=datetime.utcnow(),
        ends_at=datetime.utcnow() + timedelta(days=7),
        created_at=datetime.utcnow()
    )
    
    db.add(challenge)
    await db.commit()
    
    return await format_challenge_response(challenge, current_user.id, db)


@router.get("/trending")
async def get_trending_challenges(
    limit: int = Query(10, le=50),
    current_user: Optional[User] = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get trending challenges"""
    
    # Get challenges with most participants in last 24 hours
    trending = await db.query(
        Challenge,
        func.count(ChallengeParticipation.id).label('participant_count')
    ).join(
        ChallengeParticipation
    ).filter(
        Challenge.ends_at > datetime.utcnow(),
        ChallengeParticipation.created_at > datetime.utcnow() - timedelta(hours=24)
    ).group_by(
        Challenge.id
    ).order_by(
        desc('participant_count')
    ).limit(limit).all()
    
    challenges = []
    for challenge, count in trending:
        formatted = await format_challenge_response(
            challenge, 
            current_user.id if current_user else None, 
            db
        )
        challenges.append(formatted)
    
    return {"challenges": challenges}


@router.get("/{challenge_id}")
async def get_challenge(
    challenge_id: str,
    current_user: Optional[User] = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get challenge details"""
    
    challenge = await db.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(404, "Challenge not found")
    
    return await format_challenge_response(
        challenge, 
        current_user.id if current_user else None, 
        db
    )


@router.post("/{challenge_id}/join")
async def join_challenge(
    challenge_id: str,
    join_data: JoinChallenge,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Join a challenge with a creation"""
    
    # Verify challenge exists and is active
    challenge = await db.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(404, "Challenge not found")
    
    if challenge.ends_at < datetime.utcnow():
        raise HTTPException(400, "Challenge has ended")
    
    # Verify creation exists and belongs to user
    creation = await db.get(Creation, join_data.creation_id)
    if not creation or creation.user_id != current_user.id:
        raise HTTPException(404, "Creation not found")
    
    # Check if already participating
    existing = await db.query(ChallengeParticipation).filter(
        ChallengeParticipation.challenge_id == challenge_id,
        ChallengeParticipation.user_id == current_user.id,
        ChallengeParticipation.creation_id == join_data.creation_id
    ).first()
    
    if existing:
        raise HTTPException(400, "Already participating with this creation")
    
    # Create participation
    participation = ChallengeParticipation(
        id=str(uuid.uuid4()),
        challenge_id=challenge_id,
        user_id=current_user.id,
        creation_id=join_data.creation_id,
        created_at=datetime.utcnow()
    )
    
    db.add(participation)
    
    # Update creation with challenge
    creation.challenge_id = challenge_id
    
    # Update challenge stats
    challenge.participant_count += 1
    challenge.creation_count += 1
    
    await db.commit()
    
    return {
        "success": True,
        "participation_id": participation.id,
        "message": f"Joined {challenge.hashtag} challenge!"
    }


@router.get("/{challenge_id}/leaderboard")
async def get_challenge_leaderboard(
    challenge_id: str,
    limit: int = Query(20, le=100),
    db = Depends(get_db)
):
    """Get challenge leaderboard"""
    
    challenge = await db.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(404, "Challenge not found")
    
    # Get top participants by engagement (views + shares)
    leaderboard = await db.query(
        User.username,
        User.id,
        Creation.id.label('creation_id'),
        Creation.thumbnail_url,
        (Creation.views + Creation.share_count).label('engagement_score')
    ).join(
        ChallengeParticipation,
        ChallengeParticipation.user_id == User.id
    ).join(
        Creation,
        Creation.id == ChallengeParticipation.creation_id
    ).filter(
        ChallengeParticipation.challenge_id == challenge_id
    ).order_by(
        desc('engagement_score')
    ).limit(limit).all()
    
    return {
        "challenge": {
            "id": challenge.id,
            "title": challenge.title,
            "hashtag": challenge.hashtag
        },
        "leaderboard": [
            {
                "rank": idx + 1,
                "username": entry.username,
                "user_id": entry.id,
                "creation_id": entry.creation_id,
                "thumbnail": entry.thumbnail_url,
                "engagement_score": entry.engagement_score
            }
            for idx, entry in enumerate(leaderboard)
        ]
    }


@router.post("/{challenge_id}/boost")
async def boost_challenge(
    challenge_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Boost challenge visibility (requires payment)"""
    
    challenge = await db.get(Challenge, challenge_id)
    if not challenge:
        raise HTTPException(404, "Challenge not found")
    
    if challenge.creator_id != current_user.id:
        raise HTTPException(403, "Only challenge creator can boost")
    
    # This would integrate with payments
    # For now, just mark as boosted
    challenge.is_boosted = True
    challenge.boost_ends_at = datetime.utcnow() + timedelta(days=3)
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Challenge boosted! Will reach 100K+ users",
        "boost_ends_at": challenge.boost_ends_at
    }


async def format_challenge_response(
    challenge: Challenge, 
    user_id: Optional[str], 
    db
) -> Dict:
    """Format challenge response with stats"""
    
    # Get real-time participant count
    participant_count = await db.query(
        func.count(ChallengeParticipation.id)
    ).filter(
        ChallengeParticipation.challenge_id == challenge.id
    ).scalar()
    
    # Get top 5 leaderboard entries
    leaderboard = await db.query(
        User.username,
        (Creation.views + Creation.share_count).label('score')
    ).join(
        ChallengeParticipation,
        ChallengeParticipation.user_id == User.id
    ).join(
        Creation,
        Creation.id == ChallengeParticipation.creation_id
    ).filter(
        ChallengeParticipation.challenge_id == challenge.id
    ).order_by(
        desc('score')
    ).limit(5).all()
    
    # Check if user is participating
    is_participating = False
    if user_id:
        participation = await db.query(ChallengeParticipation).filter(
            ChallengeParticipation.challenge_id == challenge.id,
            ChallengeParticipation.user_id == user_id
        ).first()
        is_participating = participation is not None
    
    return {
        "id": challenge.id,
        "title": challenge.title,
        "description": challenge.description,
        "hashtag": challenge.hashtag,
        "participant_count": participant_count,
        "creation_count": challenge.creation_count,
        "ends_at": challenge.ends_at,
        "is_official": challenge.is_official,
        "is_boosted": challenge.is_boosted,
        "leaderboard": [
            {"username": entry.username, "score": entry.score}
            for entry in leaderboard
        ],
        "is_participating": is_participating
    }
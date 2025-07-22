from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.services.ai_orchestrator import ai_orchestrator
from app.services.storage import upload_to_s3
from app.services.database import get_db
from app.auth import get_current_user
from app.models import User, Creation
import asyncio
import uuid
from datetime import datetime

router = APIRouter()


class CreateRequest(BaseModel):
    input_type: str  # "text", "audio", "image"
    text_input: Optional[str] = None
    creation_type: str = "general"
    language: str = "en"
    challenge_id: Optional[str] = None


class CreationResponse(BaseModel):
    creation_id: str
    status: str
    content_url: Optional[str] = None
    share_links: Dict[str, str]
    processing_time: float
    price: float


@router.post("/create", response_model=CreationResponse)
async def create_content(
    request: Request,
    background_tasks: BackgroundTasks,
    create_request: CreateRequest = None,
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Create new AI-powered content"""
    
    # Check user's creation quota
    if not current_user.has_unlimited and current_user.creations_remaining <= 0:
        raise HTTPException(
            status_code=402,
            detail="No creations remaining. Please upgrade your plan."
        )
    
    # Calculate price with surge pricing
    base_price = 0 if current_user.creations_remaining > 0 else 0.99
    surge_multiplier = getattr(request.state, 'surge_multiplier', 1.0)
    final_price = base_price * surge_multiplier
    
    # Process input based on type
    input_data = None
    if create_request.input_type == "text":
        input_data = create_request.text_input
    elif file:
        input_data = await file.read()
    else:
        raise HTTPException(400, "No input provided")
    
    # Generate creation ID
    creation_id = str(uuid.uuid4())
    
    # Start async processing
    background_tasks.add_task(
        process_creation_async,
        creation_id,
        current_user.id,
        create_request.input_type,
        input_data,
        create_request.creation_type,
        create_request.language,
        create_request.challenge_id,
        db
    )
    
    # Return immediate response
    return CreationResponse(
        creation_id=creation_id,
        status="processing",
        content_url=None,
        share_links={
            "tiktok": f"https://create.ai/share/{creation_id}?platform=tiktok",
            "instagram": f"https://create.ai/share/{creation_id}?platform=instagram",
            "twitter": f"https://create.ai/share/{creation_id}?platform=twitter",
            "youtube": f"https://create.ai/share/{creation_id}?platform=youtube"
        },
        processing_time=0,
        price=final_price
    )


async def process_creation_async(
    creation_id: str,
    user_id: str,
    input_type: str,
    input_data: Any,
    creation_type: str,
    language: str,
    challenge_id: Optional[str],
    db
):
    """Process creation asynchronously"""
    try:
        # Process through AI pipeline
        result = await ai_orchestrator.process_creation(
            user_id=user_id,
            input_type=input_type,
            input_data=input_data,
            creation_type=creation_type,
            language=language
        )
        
        # Upload generated content to S3
        content_urls = await upload_content_to_storage(result["content"])
        
        # Save to database
        creation = Creation(
            id=creation_id,
            user_id=user_id,
            content_type=creation_type,
            content_urls=content_urls,
            metadata=result["metadata"],
            challenge_id=challenge_id,
            status="completed",
            created_at=datetime.utcnow()
        )
        
        db.add(creation)
        await db.commit()
        
        # Update user stats
        await update_user_stats(db, user_id)
        
    except Exception as e:
        # Update creation status to failed
        await db.execute(
            "UPDATE creations SET status = 'failed' WHERE id = :id",
            {"id": creation_id}
        )
        await db.commit()
        raise


@router.get("/creations/{creation_id}")
async def get_creation(
    creation_id: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get creation details"""
    creation = await db.get(Creation, creation_id)
    
    if not creation:
        raise HTTPException(404, "Creation not found")
    
    if creation.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    
    return {
        "creation_id": creation.id,
        "status": creation.status,
        "content_urls": creation.content_urls,
        "metadata": creation.metadata,
        "created_at": creation.created_at,
        "share_count": creation.share_count,
        "views": creation.views
    }


@router.get("/creations")
async def list_creations(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """List user's creations"""
    creations = await db.query(Creation).filter(
        Creation.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    return {
        "creations": [
            {
                "id": c.id,
                "type": c.content_type,
                "status": c.status,
                "created_at": c.created_at,
                "thumbnail": c.content_urls.get("thumbnail")
            }
            for c in creations
        ],
        "total": await db.query(Creation).filter(
            Creation.user_id == current_user.id
        ).count()
    }


@router.post("/creations/{creation_id}/share")
async def track_share(
    creation_id: str,
    platform: str,
    current_user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    """Track when content is shared"""
    creation = await db.get(Creation, creation_id)
    
    if not creation:
        raise HTTPException(404, "Creation not found")
    
    # Update share count
    creation.share_count += 1
    creation.shares_by_platform[platform] = (
        creation.shares_by_platform.get(platform, 0) + 1
    )
    
    await db.commit()
    
    # Track viral coefficient
    await track_viral_metrics(db, current_user.id, creation_id, platform)
    
    return {"success": True, "total_shares": creation.share_count}


async def upload_content_to_storage(content: Dict[str, Any]) -> Dict[str, str]:
    """Upload generated content to S3"""
    urls = {}
    
    # Upload text content
    if content.get("text"):
        text_url = await upload_to_s3(
            content["text"]["content"],
            f"text/{uuid.uuid4()}.json",
            "application/json"
        )
        urls["text"] = text_url
    
    # Upload images
    if content.get("images"):
        image_urls = []
        for idx, image_url in enumerate(content["images"]):
            # Download and re-upload to our S3
            # In production, this would download from AI service and upload
            s3_url = await upload_to_s3(
                image_url,  # This would be actual image data
                f"images/{uuid.uuid4()}.jpg",
                "image/jpeg"
            )
            image_urls.append(s3_url)
        urls["images"] = image_urls
    
    # Upload voiceover
    if content.get("voiceover"):
        audio_url = await upload_to_s3(
            content["voiceover"]["audio_data"],
            f"audio/{uuid.uuid4()}.mp3",
            "audio/mpeg"
        )
        urls["voiceover"] = audio_url
    
    return urls


async def update_user_stats(db, user_id: str):
    """Update user statistics after creation"""
    user = await db.get(User, user_id)
    
    if not user.has_unlimited:
        user.creations_remaining = max(0, user.creations_remaining - 1)
    
    user.total_creations += 1
    user.last_creation_at = datetime.utcnow()
    
    await db.commit()


async def track_viral_metrics(db, user_id: str, creation_id: str, platform: str):
    """Track viral coefficient and engagement metrics"""
    # This would implement sophisticated viral tracking
    # For now, just increment counters
    pass
from celery import Task
from app.celery_app import celery_app
from app.services.ai_orchestrator import ai_orchestrator
from app.services.storage import upload_to_s3, upload_json
from app.services.database import get_db_context
from app.models import Creation, User, Payment
from datetime import datetime, timedelta
import psutil
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Task with callbacks"""
    def on_success(self, retval, task_id, args, kwargs):
        """Success callback"""
        logger.info(f"Task {task_id} succeeded with result: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback"""
        logger.error(f"Task {task_id} failed with exception: {exc}")


@celery_app.task(base=CallbackTask, bind=True, max_retries=3)
async def process_creation(
    self,
    creation_id: str,
    user_id: str,
    input_type: str,
    input_data: str | bytes,
    creation_type: str,
    language: str
):
    """Process creation asynchronously"""
    
    try:
        # Initialize AI orchestrator if needed
        if not ai_orchestrator.initialized:
            await ai_orchestrator.initialize()
        
        # Process through AI pipeline
        result = await ai_orchestrator.process_creation(
            user_id=user_id,
            input_type=input_type,
            input_data=input_data,
            creation_type=creation_type,
            language=language
        )
        
        # Upload content to S3
        content_urls = {}
        
        # Upload text content
        if result["content"].get("text"):
            text_url = await upload_json(
                result["content"]["text"],
                f"creations/{creation_id}/text"
            )
            content_urls["text"] = text_url
        
        # Upload images
        if result["content"].get("images"):
            image_urls = []
            for idx, image_data in enumerate(result["content"]["images"]):
                image_url = await upload_to_s3(
                    image_data,
                    f"creations/{creation_id}/image_{idx}.jpg",
                    "image/jpeg"
                )
                image_urls.append(image_url)
            content_urls["images"] = image_urls
        
        # Upload voiceover
        if result["content"].get("voiceover"):
            audio_url = await upload_to_s3(
                result["content"]["voiceover"]["audio_data"],
                f"creations/{creation_id}/voiceover.mp3",
                "audio/mpeg"
            )
            content_urls["voiceover"] = audio_url
        
        # Update database
        async with get_db_context() as db:
            creation = await db.get(Creation, creation_id)
            if creation:
                creation.status = "completed"
                creation.content_urls = content_urls
                creation.metadata = result["metadata"]
                creation.processing_time = result["metadata"]["processing_time"]
                
                # Update user stats
                user = await db.get(User, user_id)
                if user:
                    user.total_creations += 1
                    user.last_creation_at = datetime.utcnow()
                    if not user.has_unlimited:
                        user.creations_remaining = max(0, user.creations_remaining - 1)
                
                await db.commit()
        
        return {
            "success": True,
            "creation_id": creation_id,
            "content_urls": content_urls
        }
        
    except Exception as e:
        logger.error(f"Error processing creation {creation_id}: {str(e)}")
        
        # Update creation status to failed
        async with get_db_context() as db:
            creation = await db.get(Creation, creation_id)
            if creation:
                creation.status = "failed"
                await db.commit()
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


@celery_app.task
async def update_surge_pricing():
    """Update surge pricing based on server load"""
    
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    
    # Calculate load score
    load_score = (cpu_percent + memory_percent) / 2
    
    # Update surge status in Redis
    import redis.asyncio as redis
    r = await redis.from_url(settings.redis_url)
    
    surge_active = load_score > (settings.surge_threshold * 100)
    surge_multiplier = settings.surge_multiplier if surge_active else 1.0
    
    await r.set("surge:active", str(surge_active))
    await r.set("surge:multiplier", str(surge_multiplier))
    await r.set("server:load", str(load_score))
    
    await r.close()
    
    logger.info(f"Surge pricing updated: active={surge_active}, multiplier={surge_multiplier}")
    
    return {
        "load_score": load_score,
        "surge_active": surge_active,
        "surge_multiplier": surge_multiplier
    }


@celery_app.task
async def cleanup_expired_creations():
    """Clean up failed or abandoned creations"""
    
    async with get_db_context() as db:
        # Find creations stuck in processing for over 1 hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        expired_creations = await db.query(Creation).filter(
            Creation.status == "processing",
            Creation.created_at < one_hour_ago
        ).all()
        
        for creation in expired_creations:
            creation.status = "failed"
            logger.warning(f"Marked creation {creation.id} as failed due to timeout")
        
        await db.commit()
        
        return {
            "cleaned_up": len(expired_creations)
        }


@celery_app.task
async def calculate_viral_metrics():
    """Calculate and update viral metrics"""
    
    async with get_db_context() as db:
        # Get metrics for last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        # New users from shares
        new_users = await db.query(User).filter(
            User.created_at > one_hour_ago,
            User.referred_by.isnot(None)
        ).count()
        
        # Total shares
        from sqlalchemy import func
        total_shares = await db.query(
            func.sum(Creation.share_count)
        ).filter(
            Creation.created_at > one_hour_ago
        ).scalar() or 0
        
        # Active users
        active_users = await db.query(
            func.count(func.distinct(Creation.user_id))
        ).filter(
            Creation.created_at > one_hour_ago
        ).scalar() or 0
        
        # Calculate viral coefficient
        viral_coefficient = 0
        if active_users > 0:
            shares_per_user = total_shares / active_users
            conversion_rate = new_users / (total_shares + 1)
            viral_coefficient = shares_per_user * conversion_rate
        
        # Store in Redis
        import redis.asyncio as redis
        r = await redis.from_url(settings.redis_url)
        
        await r.hset("viral:metrics", mapping={
            "coefficient": str(viral_coefficient),
            "new_users": str(new_users),
            "total_shares": str(total_shares),
            "active_users": str(active_users),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await r.close()
        
        logger.info(f"Viral metrics updated: K={viral_coefficient:.2f}")
        
        return {
            "viral_coefficient": viral_coefficient,
            "metrics": {
                "new_users": new_users,
                "total_shares": total_shares,
                "active_users": active_users
            }
        }


@celery_app.task
async def send_email(to: str, subject: str, body: str):
    """Send email notification"""
    # This would integrate with an email service
    logger.info(f"Sending email to {to}: {subject}")
    # Implementation would go here
    pass


@celery_app.task
async def update_analytics(event_type: str, user_id: str, data: dict):
    """Update analytics in Mixpanel"""
    # This would integrate with Mixpanel
    logger.info(f"Analytics event: {event_type} for user {user_id}")
    # Implementation would go here
    pass
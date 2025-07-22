from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from app.services.database import get_db
from app.models import User, Payment, Creation, Challenge
from app.api.auth import get_current_user
from sqlalchemy import func, desc
import psutil
from app.services.ai_orchestrator import ai_orchestrator
from app.config import settings

router = APIRouter()


def admin_required(current_user: User = Depends(get_current_user)):
    """Ensure user is admin"""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return current_user


@router.get("/dashboard")
async def admin_dashboard(
    admin: User = Depends(admin_required),
    db = Depends(get_db)
):
    """Get admin dashboard data"""
    
    now = datetime.utcnow()
    today = now.date()
    
    # Revenue metrics
    today_revenue = await db.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.status == "succeeded",
        func.date(Payment.created_at) == today
    ).scalar() or 0
    
    total_revenue = await db.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.status == "succeeded"
    ).scalar() or 0
    
    # User metrics
    total_users = await db.query(func.count(User.id)).scalar()
    
    new_users_today = await db.query(
        func.count(User.id)
    ).filter(
        func.date(User.created_at) == today
    ).scalar()
    
    active_users_24h = await db.query(
        func.count(func.distinct(Creation.user_id))
    ).filter(
        Creation.created_at > now - timedelta(hours=24)
    ).scalar()
    
    # Creation metrics
    total_creations = await db.query(func.count(Creation.id)).scalar()
    
    creations_today = await db.query(
        func.count(Creation.id)
    ).filter(
        func.date(Creation.created_at) == today
    ).scalar()
    
    # Viral metrics
    total_shares = await db.query(
        func.sum(Creation.share_count)
    ).scalar() or 0
    
    viral_coefficient = calculate_viral_coefficient(
        new_users_today, active_users_24h, total_shares
    )
    
    # Server metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    # Model performance
    model_latencies = {}
    for model_name, pool in ai_orchestrator.model_pools.items():
        avg_latency = sum(pool.latency_tracker.values()) / len(pool.latency_tracker) if pool.latency_tracker else 0
        model_latencies[model_name] = round(avg_latency, 2)
    
    return {
        "revenue": {
            "today": today_revenue,
            "total": total_revenue,
            "target": 20000000,
            "progress_percentage": (total_revenue / 20000000) * 100,
            "hourly_rate": today_revenue / ((now.hour + 1) or 1),
            "projected_24h": (today_revenue / ((now.hour + 1) or 1)) * 24
        },
        "users": {
            "total": total_users,
            "new_today": new_users_today,
            "active_24h": active_users_24h,
            "conversion_rate": (active_users_24h / total_users * 100) if total_users > 0 else 0
        },
        "creations": {
            "total": total_creations,
            "today": creations_today,
            "average_per_user": total_creations / total_users if total_users > 0 else 0
        },
        "viral_metrics": {
            "total_shares": total_shares,
            "viral_coefficient": viral_coefficient,
            "share_rate": (total_shares / total_creations * 100) if total_creations > 0 else 0
        },
        "server_health": {
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "surge_active": cpu_percent > (settings.surge_threshold * 100),
            "uptime_hours": get_uptime_hours()
        },
        "model_performance": model_latencies
    }


@router.get("/revenue/hourly")
async def get_hourly_revenue(
    hours: int = Query(24, le=168),
    admin: User = Depends(admin_required),
    db = Depends(get_db)
):
    """Get hourly revenue data"""
    
    hourly_data = await db.query(
        func.date_trunc('hour', Payment.created_at).label('hour'),
        func.sum(Payment.amount).label('revenue'),
        func.count(Payment.id).label('transaction_count')
    ).filter(
        Payment.status == "succeeded",
        Payment.created_at >= datetime.utcnow() - timedelta(hours=hours)
    ).group_by('hour').order_by('hour').all()
    
    return {
        "hourly_revenue": [
            {
                "hour": entry.hour.isoformat(),
                "revenue": entry.revenue,
                "transactions": entry.transaction_count
            }
            for entry in hourly_data
        ]
    }


@router.get("/users/acquisition")
async def get_user_acquisition(
    days: int = Query(7, le=30),
    admin: User = Depends(admin_required),
    db = Depends(get_db)
):
    """Get user acquisition funnel"""
    
    acquisition_data = await db.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('signups'),
        func.sum(func.case([(User.total_creations > 0, 1)], else_=0)).label('activated'),
        func.sum(func.case([(User.subscription_tier != 'free', 1)], else_=0)).label('paid')
    ).filter(
        User.created_at >= datetime.utcnow() - timedelta(days=days)
    ).group_by('date').order_by('date').all()
    
    return {
        "acquisition_funnel": [
            {
                "date": entry.date.isoformat(),
                "signups": entry.signups,
                "activated": entry.activated,
                "paid": entry.paid,
                "activation_rate": (entry.activated / entry.signups * 100) if entry.signups > 0 else 0,
                "conversion_rate": (entry.paid / entry.signups * 100) if entry.signups > 0 else 0
            }
            for entry in acquisition_data
        ]
    }


@router.get("/challenges/performance")
async def get_challenge_performance(
    admin: User = Depends(admin_required),
    db = Depends(get_db)
):
    """Get challenge performance metrics"""
    
    top_challenges = await db.query(
        Challenge,
        func.count(ChallengeParticipation.id).label('participants'),
        func.sum(Creation.share_count).label('total_shares')
    ).join(
        ChallengeParticipation
    ).join(
        Creation,
        Creation.id == ChallengeParticipation.creation_id
    ).group_by(
        Challenge.id
    ).order_by(
        desc('participants')
    ).limit(10).all()
    
    return {
        "top_challenges": [
            {
                "id": challenge.id,
                "title": challenge.title,
                "hashtag": challenge.hashtag,
                "participants": participants,
                "total_shares": total_shares or 0,
                "viral_score": (total_shares or 0) / participants if participants > 0 else 0,
                "is_official": challenge.is_official,
                "is_boosted": challenge.is_boosted
            }
            for challenge, participants, total_shares in top_challenges
        ]
    }


@router.get("/monitoring/alerts")
async def get_system_alerts(
    admin: User = Depends(admin_required)
):
    """Get system alerts and warnings"""
    
    alerts = []
    
    # Check CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 90:
        alerts.append({
            "level": "critical",
            "type": "performance",
            "message": f"CPU usage critical: {cpu_percent}%",
            "timestamp": datetime.utcnow()
        })
    elif cpu_percent > 80:
        alerts.append({
            "level": "warning",
            "type": "performance",
            "message": f"CPU usage high: {cpu_percent}%",
            "timestamp": datetime.utcnow()
        })
    
    # Check memory
    memory = psutil.virtual_memory()
    if memory.percent > 90:
        alerts.append({
            "level": "critical",
            "type": "performance",
            "message": f"Memory usage critical: {memory.percent}%",
            "timestamp": datetime.utcnow()
        })
    
    # Check model latencies
    for model_name, pool in ai_orchestrator.model_pools.items():
        if pool.latency_tracker:
            avg_latency = sum(pool.latency_tracker.values()) / len(pool.latency_tracker)
            if avg_latency > 30:
                alerts.append({
                    "level": "warning",
                    "type": "ai_model",
                    "message": f"{model_name} latency high: {avg_latency:.1f}s",
                    "timestamp": datetime.utcnow()
                })
    
    return {"alerts": alerts}


@router.post("/surge-pricing/toggle")
async def toggle_surge_pricing(
    enabled: bool,
    admin: User = Depends(admin_required)
):
    """Manually toggle surge pricing"""
    
    # This would update a global state
    # For now, just return success
    return {
        "success": True,
        "surge_pricing_enabled": enabled,
        "message": f"Surge pricing {'enabled' if enabled else 'disabled'}"
    }


@router.get("/analytics/realtime")
async def get_realtime_analytics(
    admin: User = Depends(admin_required),
    db = Depends(get_db)
):
    """Get real-time analytics for monitoring"""
    
    # Get metrics for last 5 minutes
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    
    recent_creations = await db.query(
        func.count(Creation.id)
    ).filter(
        Creation.created_at > five_min_ago
    ).scalar()
    
    recent_revenue = await db.query(
        func.sum(Payment.amount)
    ).filter(
        Payment.created_at > five_min_ago,
        Payment.status == "succeeded"
    ).scalar() or 0
    
    active_sessions = await db.query(
        func.count(func.distinct(Creation.user_id))
    ).filter(
        Creation.created_at > five_min_ago
    ).scalar()
    
    return {
        "realtime": {
            "creations_per_minute": recent_creations / 5,
            "revenue_per_minute": recent_revenue / 5,
            "active_sessions": active_sessions,
            "server_load": psutil.cpu_percent(interval=0.1),
            "timestamp": datetime.utcnow()
        }
    }


def calculate_viral_coefficient(new_users: int, active_users: int, shares: int) -> float:
    """Calculate viral coefficient (K-factor)"""
    if active_users == 0:
        return 0.0
    
    # Simple K-factor: (shares per user * conversion rate)
    shares_per_user = shares / active_users
    conversion_rate = new_users / (shares + 1)  # Avoid division by zero
    
    return round(shares_per_user * conversion_rate, 2)


def get_uptime_hours() -> float:
    """Get system uptime in hours"""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    return round(uptime.total_seconds() / 3600, 1)
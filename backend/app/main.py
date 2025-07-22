from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from prometheus_client import make_asgi_app
from app.config import settings
from app.services.ai_orchestrator import ai_orchestrator
from app.api import auth, creations, payments, challenges, admin
from app.middleware import RateLimitMiddleware, MetricsMiddleware
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Create.ai backend...")
    
    # Initialize Sentry
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1
        )
    
    # Initialize AI orchestrator
    await ai_orchestrator.initialize()
    logger.info("AI orchestrator initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Create.ai backend...")
    await ai_orchestrator.cleanup()


app = FastAPI(
    title="Create.ai API",
    description="AI-powered content creation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(MetricsMiddleware)

if settings.sentry_dsn:
    app.add_middleware(SentryAsgiMiddleware)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(creations.router, prefix="/api/creations", tags=["creations"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(challenges.router, prefix="/api/challenges", tags=["challenges"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to Create.ai API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ai_orchestrator": ai_orchestrator.initialized,
        "environment": settings.environment
    }


@app.get("/api/stats")
async def get_stats():
    """Get platform statistics"""
    # This would be connected to real data
    return {
        "total_creations": 150234,
        "active_users": 45678,
        "revenue_today": 125678.90,
        "trending_challenges": [
            "#AIMoviePoster",
            "#PetAdventureAI",
            "#AITimeMachine"
        ]
    }
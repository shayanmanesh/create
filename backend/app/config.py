from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/createai"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # AI Model APIs
    whisper_api_key: str = ""
    whisper_api_url: str = ""
    qwq_api_key: str = ""
    qwq_api_url: str = ""
    llama_scout_api_key: str = ""
    llama_scout_api_url: str = ""
    flux_api_key: str = ""
    flux_api_url: str = ""
    melotts_api_key: str = ""
    melotts_api_url: str = ""
    llama_vision_api_key: str = ""
    llama_vision_api_url: str = ""
    
    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "createai-media"
    
    # Stripe
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    
    # Auth
    jwt_secret_key: str = "your-secret-key-here"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CloudFlare
    cloudflare_api_key: str = ""
    cloudflare_zone_id: str = ""
    
    # Monitoring
    sentry_dsn: str = ""
    mixpanel_token: str = ""
    
    # App Config
    environment: str = "development"
    debug: bool = True
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Performance
    max_workers: int = 10
    connection_pool_size: int = 20
    request_timeout: int = 30
    ai_model_timeout: int = 60
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 3600  # 1 hour
    
    # Pricing
    price_per_creation: float = 0.99
    surge_multiplier: float = 1.2
    surge_threshold: float = 0.8  # 80% server load
    
    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
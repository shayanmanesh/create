from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import redis.asyncio as redis
from app.config import settings
from prometheus_client import Counter, Histogram, Gauge
import psutil
import asyncio

# Prometheus metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
active_requests = Gauge('http_requests_active', 'Active HTTP requests')
server_load = Gauge('server_load_percentage', 'Server CPU load percentage')


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis_client = None
        
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
            
        # Initialize Redis client if not exists
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.redis_url)
        
        # Get user identifier (from auth token or IP)
        user_id = request.headers.get("X-User-ID", request.client.host)
        
        # Rate limit key
        key = f"rate_limit:{user_id}"
        
        try:
            # Check rate limit
            current = await self.redis_client.incr(key)
            
            if current == 1:
                # Set expiry on first request
                await self.redis_client.expire(key, settings.rate_limit_period)
            
            if current > settings.rate_limit_requests:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again later."
                )
            
            # Add rate limit headers
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, settings.rate_limit_requests - current)
            )
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            # Don't fail request if rate limiting fails
            return await call_next(request)


class MetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Start background task to update server load
        asyncio.create_task(self._update_server_metrics())
    
    async def _update_server_metrics(self):
        """Update server metrics every 5 seconds"""
        while True:
            try:
                # Update CPU load
                cpu_percent = psutil.cpu_percent(interval=1)
                server_load.set(cpu_percent)
                await asyncio.sleep(5)
            except Exception:
                await asyncio.sleep(5)
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip metrics for metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Track active requests
        active_requests.inc()
        
        # Track request duration
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            status = 500
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            endpoint = request.url.path
            method = request.method
            
            request_count.labels(method=method, endpoint=endpoint, status=status).inc()
            request_duration.labels(method=method, endpoint=endpoint).observe(duration)
            active_requests.dec()
        
        return response


class SurgePricingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle surge pricing based on server load"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Only apply to creation endpoints
        if "/api/creations" not in request.url.path:
            return await call_next(request)
        
        # Get current server load
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Calculate surge multiplier if load is high
        surge_active = cpu_percent > (settings.surge_threshold * 100)
        surge_multiplier = settings.surge_multiplier if surge_active else 1.0
        
        # Add surge info to request state
        request.state.surge_multiplier = surge_multiplier
        request.state.surge_active = surge_active
        
        response = await call_next(request)
        
        # Add surge headers
        response.headers["X-Surge-Active"] = str(surge_active)
        response.headers["X-Surge-Multiplier"] = str(surge_multiplier)
        
        return response
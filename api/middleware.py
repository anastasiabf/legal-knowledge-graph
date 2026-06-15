"""
API Middleware - Authentication, rate limiting, logging
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
import os


logger = logging.getLogger("legalkg.api.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware for all requests."""
    
    async def dispatch(self, request: Request, call_next):
        """Log request and response."""
        start_time = time.time()
        
        # Log request
        logger.info(f"{request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = time.time() - start_time
            logger.info(
                f"{request.method} {request.url.path} "
                f"{response.status_code} {process_time:.2f}s"
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Request error: {e}", exc_info=True)
            process_time = time.time() - start_time
            
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
                headers={"X-Process-Time": str(process_time)},
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, requests_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            app: FastAPI app
            requests_per_minute: Max requests per minute per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting."""
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for health/version endpoints
        if request.url.path in ["/health", "/version", "/"]:
            return await call_next(request)
        
        # Check rate limit
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old requests
        self.client_requests[client_ip] = [
            req_time for req_time in self.client_requests[client_ip]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.client_requests[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
            )
        
        # Record request
        self.client_requests[client_ip].append(now)
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.client_requests[client_ip])
        )
        
        return response


def get_api_key(request: Request) -> str:
    """Extract API key from request."""
    # Check header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    
    # Check query param
    return request.query_params.get("api_key", "")


def verify_api_key(api_key: str) -> bool:
    """Verify API key."""
    # For now, just check if key matches environment variable
    valid_key = os.getenv("LEGALKG_API_KEY")
    
    if not valid_key:
        # If no API key configured, allow all requests
        return True
    
    return api_key == valid_key

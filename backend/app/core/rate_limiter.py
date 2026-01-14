"""
Rate limiting middleware for API endpoints.

Implements token bucket algorithm with per-user and per-endpoint limits.
Uses in-memory storage for single instance, can be extended to Redis for distributed systems.
"""

import time
import logging
from typing import Dict, Tuple, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter with per-user tracking"""
    
    def __init__(self, rate: Optional[int] = None, period: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            rate: Maximum number of requests allowed in the period (for testing)
            period: Time window in seconds (for testing)
        """
        # Simple mode for testing
        if rate is not None and period is not None:
            self.rate = rate
            self.period = period
            self.buckets: Dict[str, Tuple[float, float]] = {}
        else:
            # Production mode with endpoint-specific limits
            self.rate = None
            self.period = None
            # Store: {user_id: {endpoint: (tokens, last_update)}}
            self.buckets: Dict[str, Dict[str, Tuple[float, float]]] = defaultdict(dict)
            
            # Rate limit configurations: {endpoint: (max_requests, window_seconds)}
            self.limits = {
                "generate_solution": (10, 3600),      # 10 per hour
                "regenerate_solution": (5, 3600),     # 5 per hour
                "upload_assignment": (50, 3600),      # 50 per hour
                "check_duplicate": (20, 60),          # 20 per minute
                "general": (100, 60),                 # 100 per minute (default)
            }
    
    async def is_allowed(self, client_id: str) -> bool:
        """
        Simple interface for testing: check if client is allowed to make a request.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            True if request is allowed, False otherwise
        """
        if self.rate is None or self.period is None:
            raise ValueError("Rate limiter not initialized with rate/period for testing")
        
        now = time.time()
        refill_rate = self.rate / self.period
        
        # Initialize bucket if doesn't exist
        if client_id not in self.buckets:
            self.buckets[client_id] = (float(self.rate), now)
        
        current_tokens, last_update = self.buckets[client_id]
        
        # Refill tokens
        time_passed = now - last_update
        current_tokens = min(self.rate, current_tokens + time_passed * refill_rate)
        
        # Check if we have tokens
        if current_tokens >= 1.0:
            # Consume one token
            self.buckets[client_id] = (current_tokens - 1.0, now)
            return True
        else:
            # No tokens available
            self.buckets[client_id] = (current_tokens, now)
            return False
    
    def get_client_status(self, client_id: str) -> Dict[str, float]:
        """
        Get current status for a client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Dict with tokens_remaining and reset_time
        """
        if client_id not in self.buckets:
            return {"tokens_remaining": float(self.rate), "reset_time": 0}
        
        current_tokens, last_update = self.buckets[client_id]
        now = time.time()
        refill_rate = self.rate / self.period
        time_passed = now - last_update
        current_tokens = min(self.rate, current_tokens + time_passed * refill_rate)
        
        return {
            "tokens_remaining": current_tokens,
            "reset_time": last_update + self.period
        }
        
    def _get_bucket_key(self, user_id: str, endpoint: str) -> str:
        """Generate unique bucket key for user and endpoint"""
        return f"{user_id}:{endpoint}"
    
    def _refill_tokens(
        self, 
        current_tokens: float, 
        last_update: float, 
        max_tokens: int, 
        refill_rate: float
    ) -> float:
        """Refill tokens based on time elapsed"""
        now = time.time()
        time_passed = now - last_update
        new_tokens = min(max_tokens, current_tokens + time_passed * refill_rate)
        return new_tokens
    
    def _get_limit_config(self, endpoint: str) -> Tuple[int, int]:
        """Get rate limit configuration for endpoint"""
        # Try to match endpoint pattern
        for pattern, (max_req, window) in self.limits.items():
            if pattern in endpoint.lower():
                return max_req, window
        
        # Default limit
        return self.limits["general"]
    
    async def check_rate_limit(
        self, 
        request: Request, 
        user_id: str,
        endpoint: str
    ) -> Dict[str, int]:
        """
        Check if request is within rate limits.
        
        Returns:
            Dict with limit info: {limit, remaining, reset_time}
        
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Ensure we're in production mode
        if self.rate is not None or self.period is not None:
            raise ValueError("check_rate_limit should not be used in test mode")
            
        max_requests, window_seconds = self._get_limit_config(endpoint)
        refill_rate = max_requests / window_seconds  # tokens per second
        
        bucket_key = self._get_bucket_key(user_id, endpoint)
        
        # Get or initialize bucket
        if endpoint not in self.buckets[user_id]:
            self.buckets[user_id][endpoint] = (float(max_requests), time.time())
        
        current_tokens, last_update = self.buckets[user_id][endpoint]
        
        # Refill tokens
        current_tokens = self._refill_tokens(
            current_tokens, 
            last_update, 
            max_requests, 
            refill_rate
        )
        
        now = time.time()
        
        # Check if we have tokens
        if current_tokens >= 1.0:
            # Consume one token
            self.buckets[user_id][endpoint] = (current_tokens - 1.0, now)
            
            # Calculate time until reset
            tokens_needed = max_requests - (current_tokens - 1.0)
            reset_time = int(now + (tokens_needed / refill_rate))
            
            return {
                "limit": max_requests,
                "remaining": int(current_tokens - 1.0),
                "reset": reset_time,
                "reset_human": datetime.fromtimestamp(reset_time).isoformat()
            }
        else:
            # Rate limit exceeded
            # Calculate retry time
            tokens_needed = 1.0 - current_tokens
            retry_after = int(tokens_needed / refill_rate) + 1
            reset_time = int(now + (max_requests / refill_rate))
            
            logger.warning(
                f"Rate limit exceeded for user {user_id} on endpoint {endpoint}. "
                f"Retry after {retry_after}s"
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {retry_after} seconds.",
                    "retry_after": retry_after,
                    "limit": max_requests,
                    "window": window_seconds,
                    "reset": reset_time
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time)
                }
            )
    
    def add_rate_limit_headers(self, response: JSONResponse, limit_info: Dict[str, int]):
        """Add rate limit headers to response"""
        response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset"])
        return response


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_dependency(
    request: Request,
    endpoint: str = "general"
) -> Dict[str, int]:
    """
    Dependency for FastAPI endpoints to enforce rate limiting.
    
    Usage:
        @app.post("/api/solutions/generate")
        async def generate_solution(
            rate_info: dict = Depends(lambda r: rate_limit_dependency(r, "generate_solution"))
        ):
            ...
    """
    # Get user ID from session/JWT
    user_id = getattr(request.state, "user_id", None)
    
    if not user_id:
        # For unauthenticated requests, use IP address
        user_id = request.client.host if request.client else "anonymous"
    
    # Check rate limit
    limit_info = await rate_limiter.check_rate_limit(request, user_id, endpoint)
    
    return limit_info

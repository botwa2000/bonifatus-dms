# backend/app/services/rate_limit_service.py

"""
Rate limiting service for API endpoint protection
Implements three-tier rate limiting: auth, write, and read operations
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict
import asyncio


class RateLimitTier:
    """Rate limit configuration for different operation types"""
    AUTH = {"requests": 5, "window": 60}      # 5 requests per minute
    WRITE = {"requests": 20, "window": 60}    # 20 requests per minute
    READ = {"requests": 100, "window": 60}    # 100 requests per minute


class RateLimitService:
    """
    In-memory rate limiting service
    Tracks request counts per identifier within time windows
    """
    
    def __init__(self):
        # Store request timestamps per identifier per tier
        self._requests: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        self._cleanup_task = None
    
    def start_cleanup_task(self):
        """Start background task to clean old entries"""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_old_entries())
    
    async def _cleanup_old_entries(self):
        """Remove entries older than largest window (5 minutes)"""
        while True:
            await asyncio.sleep(300)  # Run every 5 minutes
            cutoff = datetime.utcnow() - timedelta(seconds=300)
            
            for identifier_data in self._requests.values():
                for tier_requests in identifier_data.values():
                    tier_requests[:] = [
                        ts for ts in tier_requests 
                        if ts > cutoff
                    ]
    
    def _get_limit_config(self, tier: str) -> Dict[str, int]:
        """Get rate limit configuration for tier"""
        tier_upper = tier.upper()
        if tier_upper == "AUTH":
            return RateLimitTier.AUTH
        elif tier_upper == "WRITE":
            return RateLimitTier.WRITE
        elif tier_upper == "READ":
            return RateLimitTier.READ
        else:
            return RateLimitTier.READ  # Default to most permissive
    
    def check_rate_limit(
        self, 
        identifier: str, 
        tier: str = "read"
    ) -> tuple[bool, Optional[int]]:
        """
        Check if request should be allowed
        
        Args:
            identifier: Unique identifier (user_id, IP, session)
            tier: Rate limit tier (auth, write, read)
        
        Returns:
            (is_allowed, retry_after_seconds)
        """
        config = self._get_limit_config(tier)
        max_requests = config["requests"]
        window_seconds = config["window"]
        
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        # Get requests for this identifier and tier
        tier_requests = self._requests[identifier][tier]
        
        # Remove old requests outside window
        tier_requests[:] = [ts for ts in tier_requests if ts > cutoff]
        
        # Check if under limit
        if len(tier_requests) < max_requests:
            tier_requests.append(now)
            return True, None
        
        # Calculate retry-after from oldest request in window
        oldest_request = min(tier_requests)
        retry_after = int((oldest_request - cutoff).total_seconds()) + 1
        
        return False, retry_after
    
    def reset_limit(self, identifier: str, tier: Optional[str] = None):
        """Reset rate limit for identifier (all tiers or specific tier)"""
        if tier:
            if identifier in self._requests:
                self._requests[identifier][tier] = []
        else:
            if identifier in self._requests:
                del self._requests[identifier]
    
    def get_remaining(self, identifier: str, tier: str = "read") -> int:
        """Get remaining requests in current window"""
        config = self._get_limit_config(tier)
        max_requests = config["requests"]
        window_seconds = config["window"]
        
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        tier_requests = self._requests[identifier][tier]
        tier_requests[:] = [ts for ts in tier_requests if ts > cutoff]
        
        return max(0, max_requests - len(tier_requests))


# Singleton instance
rate_limit_service = RateLimitService()
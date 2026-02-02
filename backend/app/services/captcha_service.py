# backend/app/services/captcha_service.py
"""
CAPTCHA service using Cloudflare Turnstile
Privacy-first, invisible CAPTCHA for suspicious behavior detection
"""

import os
import logging
import httpx
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CaptchaService:
    """Handle Cloudflare Turnstile CAPTCHA verification"""
    
    VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    
    def __init__(self):
        from app.core.config import settings
        self.secret_key = settings.security.turnstile_secret_key or os.getenv('TURNSTILE_SECRET_KEY')
        self.site_key = settings.security.turnstile_site_key or os.getenv('TURNSTILE_SITE_KEY')
        self._verification_cache = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def is_enabled(self) -> bool:
        """Check if Turnstile is configured and enabled"""
        return bool(self.secret_key and self.site_key)
    
    async def verify_token(
        self,
        token: str,
        ip_address: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Verify Turnstile CAPTCHA token
        
        Args:
            token: Turnstile response token from frontend
            ip_address: User's IP address for additional verification
            idempotency_key: Optional key to prevent replay attacks
            
        Returns:
            Dict with 'success', 'challenge_ts', 'hostname', 'error_codes'
        """
        if not self.is_enabled():
            logger.warning("Turnstile not configured, skipping verification")
            return {
                'success': True,
                'warning': 'CAPTCHA not configured'
            }
        
        # Check cache to prevent duplicate verifications
        cache_key = f"{token}:{ip_address}"
        if cache_key in self._verification_cache:
            cached_result, cached_time = self._verification_cache[cache_key]
            if datetime.utcnow() - cached_time < self._cache_ttl:
                logger.info("Using cached CAPTCHA verification")
                return cached_result
        
        try:
            # Prepare verification payload
            payload = {
                'secret': self.secret_key,
                'response': token
            }
            
            if ip_address:
                payload['remoteip'] = ip_address
            
            if idempotency_key:
                payload['idempotency_key'] = idempotency_key
            
            # Call Turnstile verification API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.VERIFY_URL,
                    data=payload,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(
                        f"Turnstile API error: {response.status_code} - {response.text}"
                    )
                    return {
                        'success': False,
                        'error_codes': ['api_error']
                    }
                
                result = response.json()
                
                # Cache successful verification
                if result.get('success'):
                    self._verification_cache[cache_key] = (result, datetime.utcnow())
                
                # Log verification result
                if result.get('success'):
                    logger.info(f"CAPTCHA verification successful for {ip_address}")
                else:
                    logger.warning(
                        f"CAPTCHA verification failed: {result.get('error-codes')}"
                    )
                
                return result
                
        except httpx.TimeoutException:
            logger.error("Turnstile API timeout")
            return {
                'success': False,
                'error_codes': ['timeout']
            }
        except Exception as e:
            logger.error(f"CAPTCHA verification error: {e}")
            return {
                'success': False,
                'error_codes': ['internal_error']
            }
    
    def get_site_key(self) -> Optional[str]:
        """Get public site key for frontend integration"""
        return self.site_key
    
    def clear_cache(self):
        """Clear verification cache"""
        self._verification_cache.clear()
    
    def format_error_message(self, error_codes: list) -> str:
        """Convert Turnstile error codes to user-friendly messages"""
        error_map = {
            'missing-input-secret': 'Server configuration error',
            'invalid-input-secret': 'Server configuration error',
            'missing-input-response': 'Please complete the security check',
            'invalid-input-response': 'Security check expired, please try again',
            'bad-request': 'Invalid request, please try again',
            'timeout-or-duplicate': 'Security check expired, please try again',
            'internal-error': 'Verification service unavailable',
            'timeout': 'Verification service timeout',
            'api_error': 'Unable to verify security check'
        }
        
        if not error_codes:
            return 'Security verification failed'
        
        # Return first recognizable error message
        for code in error_codes:
            if code in error_map:
                return error_map[code]
        
        return 'Security verification failed'


# Global service instance
captcha_service = CaptchaService()
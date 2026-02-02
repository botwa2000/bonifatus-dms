# backend/app/api/security.py
"""
Security API endpoints for CAPTCHA validation and trust scoring
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.connection import get_db
from app.database.models import User
from app.middleware.auth_middleware import get_current_active_user, get_client_ip
from app.services.captcha_service import captcha_service
from app.services.trust_scoring_service import trust_scoring_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/security", tags=["security"])


class VerifyCaptchaRequest(BaseModel):
    token: str
    action: str  # e.g., "upload", "login", "register"


class VerifyCaptchaResponse(BaseModel):
    success: bool
    message: str


class TrustScoreResponse(BaseModel):
    trust_score: float
    captcha_required: bool
    message: str


@router.post(
    "/verify-captcha",
    response_model=VerifyCaptchaResponse
)
async def verify_captcha(
    request: Request,
    data: VerifyCaptchaRequest,
    current_user: User = Depends(get_current_active_user)
) -> VerifyCaptchaResponse:
    """
    Verify Cloudflare Turnstile CAPTCHA token
    """
    try:
        ip_address = get_client_ip(request)
        
        # Verify token with Cloudflare
        result = await captcha_service.verify_token(
            token=data.token,
            ip_address=ip_address
        )
        
        if result.get('success'):
            logger.info(f"CAPTCHA verified for user {current_user.id}, action: {data.action}")
            return VerifyCaptchaResponse(
                success=True,
                message="Security verification successful"
            )
        else:
            error_codes = result.get('error-codes', [])
            error_message = captcha_service.format_error_message(error_codes)
            logger.warning(f"CAPTCHA verification failed for user {current_user.id}: {error_codes}")
            
            return VerifyCaptchaResponse(
                success=False,
                message=error_message
            )
            
    except Exception as e:
        logger.error(f"CAPTCHA verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security verification failed"
        )


@router.get(
    "/trust-score",
    response_model=TrustScoreResponse
)
async def get_trust_score(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> TrustScoreResponse:
    """
    Get current user's trust score and whether CAPTCHA is required
    """
    try:
        ip_address = get_client_ip(request)
        
        # Calculate trust score
        trust_score = await trust_scoring_service.calculate_trust_score(
            user_id=str(current_user.id),
            ip_address=ip_address,
            session=session
        )
        
        # Determine if CAPTCHA is required
        captcha_required = trust_score < 0.5
        
        # Friendly message based on trust level
        if trust_score >= 0.7:
            message = "Your account is in good standing"
        elif trust_score >= 0.5:
            message = "Your account activity is normal"
        elif trust_score >= 0.3:
            message = "Unusual activity detected - security check may be required"
        else:
            message = "Enhanced security verification required"
        
        logger.info(f"Trust score for user {current_user.id}: {trust_score:.2f}")
        
        return TrustScoreResponse(
            trust_score=round(trust_score, 2),
            captcha_required=captcha_required,
            message=message
        )
        
    except Exception as e:
        logger.error(f"Trust score calculation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to calculate trust score"
        )


@router.get("/captcha-site-key")
async def get_captcha_site_key() -> dict:
    """
    Get Cloudflare Turnstile site key for frontend integration
    Public endpoint - no authentication required
    """
    site_key = settings.security.turnstile_site_key

    if not site_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CAPTCHA service not configured"
        )
    
    return {
        "site_key": site_key,
        "enabled": captcha_service.is_enabled()
    }
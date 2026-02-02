# backend/app/api/contact.py
"""
Public contact form endpoint with Turnstile CAPTCHA and rate limiting
"""

import time
import logging
from typing import Optional
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.middleware.auth_middleware import get_client_ip
from app.services.captcha_service import captcha_service
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/contact", tags=["contact"])

# In-memory rate limiting: IP -> list of timestamps
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_MAX = 3
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds

SUBJECT_OPTIONS = [
    "General Inquiry",
    "Technical Support",
    "Billing Question",
    "Feature Request",
    "Bug Report",
    "Partnership",
    "Other",
]


class ContactFormRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)
    turnstile_token: str = Field(..., min_length=1)
    honeypot: Optional[str] = Field(default=None)


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed, False if rate limited."""
    now = time.time()
    timestamps = _rate_limit_store[ip]
    # Remove expired entries
    _rate_limit_store[ip] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_store[ip].append(now)
    return True


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Submit Contact Form",
    description="Public endpoint to submit a contact form message",
)
async def submit_contact_form(request: Request, data: ContactFormRequest):
    ip_address = get_client_ip(request)

    # Honeypot check
    if data.honeypot:
        logger.warning(f"Honeypot triggered from {ip_address}")
        # Return success to not reveal detection
        return {"success": True, "message": "Message received"}

    # Rate limit check
    if not _check_rate_limit(ip_address):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many messages. Please try again later.",
        )

    # Verify Turnstile token
    captcha_result = await captcha_service.verify_token(
        token=data.turnstile_token,
        ip_address=ip_address,
    )
    if not captcha_result.get("success"):
        error_msg = captcha_service.format_error_message(
            captcha_result.get("error_codes", [])
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    # Send notification email to support@bonidoc.com
    notification_html = f"""
    <h2>New Contact Form Submission</h2>
    <p><strong>Name:</strong> {data.name}</p>
    <p><strong>Email:</strong> {data.email}</p>
    <p><strong>Subject:</strong> {data.subject}</p>
    <hr>
    <p><strong>Message:</strong></p>
    <p>{data.message}</p>
    <hr>
    <p><small>Sent from contact form | IP: {ip_address}</small></p>
    """

    notification_sent = await email_service.send_email(
        to_email=settings.email.email_from_support,
        to_name="Bonifatus DMS",
        subject=f"[Contact Form] {data.subject}",
        html_content=notification_html,
        reply_to=data.email,
    )

    # Send confirmation email to sender
    confirmation_html = f"""
    <h2>Thank you for contacting us, {data.name}!</h2>
    <p>We have received your message and will get back to you as soon as possible.</p>
    <hr>
    <p><strong>Your message:</strong></p>
    <p><strong>Subject:</strong> {data.subject}</p>
    <p>{data.message}</p>
    <hr>
    <p>Best regards,<br>The Bonifatus DMS Team</p>
    """

    await email_service.send_email(
        to_email=data.email,
        to_name=data.name,
        subject="We received your message - Bonifatus DMS",
        html_content=confirmation_html,
    )

    if not notification_sent:
        logger.error(f"Failed to send contact notification for {data.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message. Please try again later.",
        )

    logger.info(f"Contact form submitted by {data.email} ({ip_address})")
    return {"success": True, "message": "Message sent successfully"}

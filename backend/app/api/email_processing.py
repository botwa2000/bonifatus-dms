"""
Email Processing API Endpoints
Manage email-to-document processing settings and history
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.database.connection import get_db
from app.database.models import User
from app.database.auth_models import AllowedSender, EmailProcessingLog, EmailSettings
from app.middleware.auth_middleware import get_current_active_user
from app.services.email_processing_service import EmailProcessingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/email-processing", tags=["Email Processing"])


# ==================== Pydantic Schemas ====================

class EnableEmailProcessingRequest(BaseModel):
    """Request to enable email processing"""
    enable: bool


class EnableEmailProcessingResponse(BaseModel):
    """Response with user's email processing address"""
    enabled: bool
    email_address: Optional[str] = None
    message: str


class AddAllowedSenderRequest(BaseModel):
    """Request to add allowed sender"""
    sender_email: EmailStr
    sender_name: Optional[str] = None


class AllowedSenderResponse(BaseModel):
    """Allowed sender response"""
    id: str
    sender_email: str
    sender_name: Optional[str] = None
    is_active: bool
    use_count: int
    last_email_at: Optional[str] = None
    created_at: str


class EmailProcessingLogResponse(BaseModel):
    """Email processing log response"""
    id: str
    sender_email: str
    subject: Optional[str] = None
    status: str
    attachment_count: int
    documents_created: int
    rejection_reason: Optional[str] = None
    received_at: str
    processing_time_ms: Optional[int] = None


class EmailSettingsResponse(BaseModel):
    """Email settings response"""
    enabled: bool
    email_address: Optional[str] = None
    daily_email_limit: int
    max_attachment_size_mb: int
    auto_categorize: bool
    send_confirmation_email: bool


# ==================== API Endpoints ====================

@router.post("/enable", response_model=EnableEmailProcessingResponse)
async def enable_email_processing(
    request: EnableEmailProcessingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Enable or disable email processing for the current user
    Generates unique email address on first enable
    """
    try:
        email_service = EmailProcessingService(db)

        if request.enable:
            # Enable email processing
            success, email_address, error = email_service.enable_email_processing_for_user(str(current_user.id))

            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error or "Failed to enable email processing"
                )

            return EnableEmailProcessingResponse(
                enabled=True,
                email_address=email_address,
                message=f"Email processing enabled. Send documents to {email_address}"
            )
        else:
            # Disable email processing
            current_user.email_processing_enabled = False
            db.commit()

            return EnableEmailProcessingResponse(
                enabled=False,
                email_address=None,
                message="Email processing disabled"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling email processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email processing settings"
        )


@router.get("/settings", response_model=EmailSettingsResponse)
async def get_email_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's email processing settings"""
    try:
        settings = db.query(EmailSettings).filter(
            EmailSettings.user_id == current_user.id
        ).first()

        if not settings:
            # Return default settings
            return EmailSettingsResponse(
                enabled=current_user.email_processing_enabled or False,
                email_address=current_user.email_processing_address,
                daily_email_limit=50,
                max_attachment_size_mb=20,
                auto_categorize=True,
                send_confirmation_email=True
            )

        return EmailSettingsResponse(
            enabled=settings.is_enabled,
            email_address=settings.email_address,
            daily_email_limit=settings.daily_email_limit,
            max_attachment_size_mb=settings.max_attachment_size_mb,
            auto_categorize=settings.auto_categorize,
            send_confirmation_email=settings.send_confirmation_email
        )

    except Exception as e:
        logger.error(f"Error fetching email settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch email settings"
        )


@router.get("/allowed-senders", response_model=List[AllowedSenderResponse])
async def get_allowed_senders(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get list of allowed senders for current user"""
    try:
        senders = db.query(AllowedSender).filter(
            AllowedSender.user_id == current_user.id
        ).order_by(AllowedSender.created_at.desc()).all()

        return [
            AllowedSenderResponse(
                id=str(sender.id),
                sender_email=sender.sender_email,
                sender_name=sender.sender_name,
                is_active=sender.is_active,
                use_count=sender.use_count,
                last_email_at=sender.last_email_at.isoformat() if sender.last_email_at else None,
                created_at=sender.created_at.isoformat()
            )
            for sender in senders
        ]

    except Exception as e:
        logger.error(f"Error fetching allowed senders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch allowed senders"
        )


@router.post("/allowed-senders", response_model=AllowedSenderResponse, status_code=status.HTTP_201_CREATED)
async def add_allowed_sender(
    request: AddAllowedSenderRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Add a new allowed sender to whitelist"""
    try:
        # Check if already exists
        existing = db.query(AllowedSender).filter(
            AllowedSender.user_id == current_user.id,
            AllowedSender.sender_email == request.sender_email
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This sender is already in your whitelist"
            )

        # Create new allowed sender
        sender = AllowedSender(
            user_id=current_user.id,
            sender_email=request.sender_email,
            sender_name=request.sender_name,
            is_active=True
        )
        db.add(sender)
        db.commit()
        db.refresh(sender)

        return AllowedSenderResponse(
            id=str(sender.id),
            sender_email=sender.sender_email,
            sender_name=sender.sender_name,
            is_active=sender.is_active,
            use_count=sender.use_count,
            last_email_at=None,
            created_at=sender.created_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding allowed sender: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add allowed sender"
        )


@router.delete("/allowed-senders/{sender_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_allowed_sender(
    sender_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Remove an allowed sender from whitelist"""
    try:
        sender = db.query(AllowedSender).filter(
            AllowedSender.id == sender_id,
            AllowedSender.user_id == current_user.id
        ).first()

        if not sender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Allowed sender not found"
            )

        db.delete(sender)
        db.commit()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting allowed sender: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete allowed sender"
        )


@router.patch("/allowed-senders/{sender_id}/toggle")
async def toggle_allowed_sender(
    sender_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Toggle allowed sender active status"""
    try:
        sender = db.query(AllowedSender).filter(
            AllowedSender.id == sender_id,
            AllowedSender.user_id == current_user.id
        ).first()

        if not sender:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Allowed sender not found"
            )

        sender.is_active = not sender.is_active
        db.commit()

        return {"is_active": sender.is_active}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling allowed sender: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle allowed sender"
        )


@router.get("/history", response_model=List[EmailProcessingLogResponse])
async def get_processing_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get email processing history for current user"""
    try:
        logs = db.query(EmailProcessingLog).filter(
            EmailProcessingLog.user_id == current_user.id
        ).order_by(EmailProcessingLog.received_at.desc()).limit(limit).offset(offset).all()

        return [
            EmailProcessingLogResponse(
                id=str(log.id),
                sender_email=log.sender_email,
                subject=log.subject,
                status=log.status,
                attachment_count=log.attachment_count,
                documents_created=log.documents_created,
                rejection_reason=log.rejection_reason,
                received_at=log.received_at.isoformat(),
                processing_time_ms=log.processing_time_ms
            )
            for log in logs
        ]

    except Exception as e:
        logger.error(f"Error fetching processing history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch processing history"
        )


@router.post("/poll-now")
async def poll_inbox_now(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger email inbox polling immediately
    Useful for debugging or when user wants immediate processing
    """
    try:
        from app.tasks.email_poller import run_poll_now

        logger.info(f"Manual email poll triggered by user {current_user.email}")

        # Run poll task asynchronously
        await run_poll_now()

        return {
            "success": True,
            "message": "Email polling completed. Check processing history for results.",
            "timestamp": "now"
        }

    except Exception as e:
        logger.error(f"Error during manual email poll: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email polling failed: {str(e)}"
        )


@router.get("/diagnostics")
async def get_email_diagnostics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get diagnostic information about email processing setup
    Helps debug email ingestion issues
    """
    try:
        from app.core.config import settings
        from app.database.auth_models import EmailSettings, AllowedSender

        # Get user's email settings
        email_settings = db.query(EmailSettings).filter(
            EmailSettings.user_id == current_user.id
        ).first()

        # Get allowed senders
        allowed_senders = db.query(AllowedSender).filter(
            AllowedSender.user_id == current_user.id,
            AllowedSender.is_active == True
        ).all()

        # Get recent processing logs
        recent_logs = db.query(EmailProcessingLog).filter(
            EmailProcessingLog.user_id == current_user.id
        ).order_by(EmailProcessingLog.received_at.desc()).limit(5).all()

        # Get latest log entry
        latest_log = recent_logs[0] if recent_logs else None

        diagnostics = {
            "user_info": {
                "user_id": str(current_user.id),
                "email": current_user.email,
                "tier": current_user.tier.name if current_user.tier else "Unknown",
                "email_processing_enabled": current_user.email_processing_enabled,
                "email_processing_address": current_user.email_processing_address
            },
            "settings": {
                "polling_interval_seconds": settings.email_processing.polling_interval_seconds,
                "max_attachment_size_mb": settings.email_processing.max_attachment_size_mb,
                "max_attachments_per_email": settings.email_processing.max_attachments_per_email,
                "imap_host": settings.email_processing.imap_host,
                "imap_port": settings.email_processing.imap_port,
                "doc_domain": settings.email_processing.doc_domain
            },
            "user_settings": {
                "exists": email_settings is not None,
                "is_enabled": email_settings.is_enabled if email_settings else False,
                "daily_limit": email_settings.daily_email_limit if email_settings else 0,
                "auto_categorize": email_settings.auto_categorize if email_settings else False
            },
            "allowed_senders": {
                "count": len(allowed_senders),
                "senders": [s.sender_email for s in allowed_senders]
            },
            "recent_activity": {
                "total_logs": len(recent_logs),
                "latest_email_received": latest_log.received_at.isoformat() if latest_log else None,
                "latest_status": latest_log.status if latest_log else None,
                "latest_rejection_reason": latest_log.rejection_reason if latest_log else None,
                "recent_statuses": [log.status for log in recent_logs]
            },
            "instructions": {
                "send_emails_to": current_user.email_processing_address,
                "allowed_senders": [s.sender_email for s in allowed_senders] if allowed_senders else ["No allowed senders configured!"],
                "polling_interval": f"Emails are checked every {settings.email_processing.polling_interval_seconds} seconds"
            }
        }

        return diagnostics

    except Exception as e:
        logger.error(f"Error generating email diagnostics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate diagnostics: {str(e)}"
        )

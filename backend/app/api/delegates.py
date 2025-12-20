# backend/app/api/delegates.py
"""
Bonifatus DMS - Delegate Access API
REST API for multi-user document access management
"""

import logging
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse

from app.schemas.delegate_schemas import (
    DelegateInviteRequest,
    DelegateResponse,
    DelegateListResponse,
    GrantedAccessResponse,
    GrantedAccessListResponse,
    AcceptInvitationResponse
)
from app.services.delegate_service import delegate_service
from app.services.email_service import EmailService
from app.middleware.auth_middleware import get_current_active_user
from app.database.models import User
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/delegates", tags=["delegates"])

# Initialize email service
email_service = EmailService()


@router.post(
    "/invite",
    response_model=DelegateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid request or duplicate invitation"},
        403: {"description": "Only Professional tier users can invite delegates"},
        404: {"description": "User not found"}
    }
)
async def invite_delegate(
    invite_request: DelegateInviteRequest,
    current_user: User = Depends(get_current_active_user)
) -> DelegateResponse:
    """
    Invite a delegate to access your documents (Pro tier only)

    - **email**: Email address of the delegate to invite
    - **role**: Access role (viewer, editor, owner) - currently only 'viewer' is implemented
    - **access_expires_at**: Optional expiry date for time-limited access

    Returns the created delegate invitation with token and expiry information.
    """
    logger.info(f"[DELEGATES API] User {current_user.email} inviting delegate: {invite_request.email}")

    delegate, error = await delegate_service.invite_delegate(
        owner_user_id=current_user.id,
        delegate_email=invite_request.email,
        role=invite_request.role,
        access_expires_at=invite_request.access_expires_at
    )

    if error:
        if "Professional tier" in error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error
            )
        elif "not found" in error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )

    logger.info(f"[DELEGATES API] Delegate invitation created: {delegate.id}")

    # Send invitation email
    try:
        accept_url = f"{settings.app.app_frontend_url}/delegates/accept?token={delegate.invitation_token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">Delegate Access Invitation</h1>
            </div>

            <div style="background-color: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-radius: 0 0 8px 8px;">
                <p style="font-size: 16px; margin-bottom: 20px;">Hello,</p>

                <p style="font-size: 16px; margin-bottom: 20px;">
                    <strong>{current_user.full_name}</strong> ({current_user.email}) has invited you to access their document library on BoniDoc as a <strong>{invite_request.role}</strong>.
                </p>

                <div style="background-color: #F3F4F6; padding: 20px; border-radius: 6px; margin: 25px 0;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #1F2937;">As a delegate, you will be able to:</p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li style="margin: 5px 0;">View and search documents</li>
                        <li style="margin: 5px 0;">Download documents for review</li>
                        <li style="margin: 5px 0;">Access document metadata and categories</li>
                    </ul>
                    <p style="margin: 10px 0 0 0; font-weight: bold; color: #1F2937;">You will NOT be able to:</p>
                    <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                        <li style="margin: 5px 0;">Upload, edit, or delete documents</li>
                    </ul>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{accept_url}"
                       style="display: inline-block; background-color: #4F46E5; color: white; text-decoration: none; padding: 14px 32px; border-radius: 6px; font-weight: bold; font-size: 16px;">
                        Accept Invitation
                    </a>
                </div>

                <p style="font-size: 14px; color: #6B7280; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
                    If you cannot click the button above, copy and paste this link into your browser:<br>
                    <a href="{accept_url}" style="color: #4F46E5; word-break: break-all;">{accept_url}</a>
                </p>

                <p style="font-size: 14px; color: #6B7280; margin-top: 20px;">
                    This invitation will expire in 7 days. If you didn't expect this invitation, you can safely ignore this email.
                </p>
            </div>

            <div style="text-align: center; margin-top: 20px; padding: 20px; font-size: 12px; color: #9CA3AF;">
                <p style="margin: 0;">BoniDoc Document Management System</p>
                <p style="margin: 5px 0 0 0;">Professional Document Management</p>
            </div>
        </body>
        </html>
        """

        await email_service.send_email(
            to_email=invite_request.email,
            to_name=invite_request.email,
            subject=f"Delegate Access Invitation from {current_user.full_name}",
            html_content=html_content
        )
        logger.info(f"[DELEGATES API] Invitation email sent to {invite_request.email}")
    except Exception as e:
        logger.error(f"[DELEGATES API] Failed to send invitation email: {e}")
        # Don't fail the request if email fails, just log it

    return DelegateResponse.from_orm(delegate)


@router.get(
    "",
    response_model=DelegateListResponse,
    responses={
        401: {"description": "Authentication required"}
    }
)
async def list_my_delegates(
    current_user: User = Depends(get_current_active_user)
) -> DelegateListResponse:
    """
    List all delegates you have invited

    Returns a list of all delegate invitations you have created, including:
    - Pending invitations (not yet accepted)
    - Active delegates (accepted invitations)
    - Revoked access (removed delegates)
    """
    logger.info(f"[DELEGATES API] User {current_user.email} listing delegates")

    delegates = await delegate_service.list_delegates(owner_user_id=current_user.id)

    return DelegateListResponse(
        delegates=delegates,
        total=len(delegates)
    )


@router.get(
    "/granted-to-me",
    response_model=GrantedAccessListResponse,
    responses={
        401: {"description": "Authentication required"}
    }
)
async def list_granted_access(
    current_user: User = Depends(get_current_active_user)
) -> GrantedAccessListResponse:
    """
    List all owners who have granted you access to their documents

    Returns a list of all active delegate access grants where you are the delegate.
    Shows which users have shared their document library with you.
    """
    logger.info(f"[DELEGATES API] User {current_user.email} listing granted access")

    granted_access = await delegate_service.list_granted_access(delegate_user_id=current_user.id)

    return GrantedAccessListResponse(
        granted_access=granted_access,
        total=len(granted_access)
    )


class PendingInvitationResponse(BaseModel):
    """Extended response for pending invitations with owner details"""
    id: str
    owner_user_id: str
    owner_email: str
    owner_name: str
    role: str
    status: str
    invitation_sent_at: Optional[str] = None
    invitation_expires_at: Optional[str] = None

class PendingInvitationListResponse(BaseModel):
    """Response for list of pending invitations"""
    invitations: List[PendingInvitationResponse]
    total: int

@router.get(
    "/pending-invitations",
    response_model=PendingInvitationListResponse,
    responses={
        401: {"description": "Authentication required"}
    }
)
async def get_pending_invitations(
    current_user: User = Depends(get_current_active_user)
) -> PendingInvitationListResponse:
    """
    Get all pending invitations for the current user

    Returns invitations that are:
    - Sent to the current user's email
    - Status is 'pending' (not yet accepted/declined)
    - Not expired

    Used by the "Shared with Me" section in Settings.
    """
    logger.info(f"[DELEGATES API] User {current_user.email} fetching pending invitations")

    from app.database.connection import db_manager
    from app.database.models import UserDelegate, User as UserModel
    from datetime import datetime

    session = db_manager.session_local()
    try:
        # Get all pending invitations for this user's email
        pending = session.query(UserDelegate).filter(
            UserDelegate.delegate_email == current_user.email.lower(),
            UserDelegate.status == 'pending',
            UserDelegate.invitation_expires_at > datetime.utcnow()
        ).order_by(UserDelegate.invitation_sent_at.desc()).all()

        logger.info(f"[DELEGATES API] Found {len(pending)} pending invitations for {current_user.email}")

        # Build response with owner details
        result = []
        for invitation in pending:
            owner = session.query(UserModel).filter(UserModel.id == invitation.owner_user_id).first()
            if owner:
                result.append(PendingInvitationResponse(
                    id=str(invitation.id),
                    owner_user_id=str(invitation.owner_user_id),
                    owner_email=owner.email,
                    owner_name=owner.full_name,
                    role=invitation.role,
                    status=invitation.status,
                    invitation_sent_at=invitation.invitation_sent_at.isoformat() if invitation.invitation_sent_at else None,
                    invitation_expires_at=invitation.invitation_expires_at.isoformat() if invitation.invitation_expires_at else None
                ))

        return PendingInvitationListResponse(
            invitations=result,
            total=len(result)
        )
    finally:
        session.close()


@router.post(
    "/accept/{token}",
    response_model=AcceptInvitationResponse,
    responses={
        400: {"description": "Invalid or expired invitation token"},
        404: {"description": "Invitation not found"}
    }
)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_active_user)
) -> AcceptInvitationResponse:
    """
    Accept a delegate invitation

    - **token**: The invitation token from the invitation email

    Validates the token and grants you access to the owner's documents.
    The invitation must be sent to your registered email address.
    """
    logger.info(f"[DELEGATES API] User {current_user.email} accepting invitation: {token[:10]}...")

    response, error = await delegate_service.accept_invitation(
        invitation_token=token,
        delegate_user_id=current_user.id
    )

    if error:
        if "not found" in error.lower() or "invalid" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )

    logger.info(f"[DELEGATES API] Invitation accepted successfully by {current_user.email}")
    return response


@router.post(
    "/respond/{invitation_id}",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Invalid invitation or action"},
        404: {"description": "Invitation not found"}
    }
)
async def respond_to_invitation(
    invitation_id: str,
    action: str = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user)
):
    """
    Accept or decline a delegate invitation from Settings page

    - **invitation_id**: The ID of the invitation
    - **action**: "accept" or "decline"

    This endpoint requires authentication and validates that the invitation
    was sent to the current user's email.
    """
    logger.info(f"[DELEGATES API] User {current_user.email} responding to invitation {invitation_id}: {action}")

    from app.database.connection import db_manager
    from app.database.models import UserDelegate, User as UserModel
    from datetime import datetime, timezone
    from uuid import UUID

    if action not in ['accept', 'decline']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'accept' or 'decline'"
        )

    session = db_manager.session_local()
    try:
        # Get the invitation
        invitation = session.query(UserDelegate).filter(
            UserDelegate.id == UUID(invitation_id)
        ).first()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )

        # Validate the invitation is for the current user
        if invitation.delegate_email.lower() != current_user.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation was not sent to your email address"
            )

        # Check invitation status
        if invitation.status != 'pending':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This invitation is {invitation.status} and cannot be accepted or declined"
            )

        # Check expiration (use timezone-aware datetime)
        if invitation.invitation_expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has expired"
            )

        # Get owner details for response
        owner = session.query(UserModel).filter(UserModel.id == invitation.owner_user_id).first()

        if action == 'accept':
            # Accept the invitation
            invitation.status = 'active'
            invitation.invitation_accepted_at = datetime.now(timezone.utc)
            invitation.delegate_user_id = current_user.id
            session.commit()

            logger.info(f"[DELEGATES API] Invitation {invitation_id} accepted by {current_user.email}")

            return {
                "success": True,
                "message": f"You now have {invitation.role} access to {owner.full_name}'s documents",
                "owner_name": owner.full_name,
                "owner_email": owner.email,
                "role": invitation.role
            }
        else:  # decline
            # Decline the invitation (set to revoked)
            invitation.status = 'revoked'
            invitation.revoked_at = datetime.now(timezone.utc)
            invitation.revoked_by = current_user.id
            session.commit()

            logger.info(f"[DELEGATES API] Invitation {invitation_id} declined by {current_user.email}")

            return {
                "success": True,
                "message": "Invitation declined",
                "owner_name": owner.full_name,
                "owner_email": owner.email
            }

    finally:
        session.close()


@router.delete(
    "/{delegate_id}",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"description": "Delegate not found or already revoked"},
        404: {"description": "Delegate not found"}
    }
)
async def revoke_delegate_access(
    delegate_id: str,
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """
    Revoke a delegate's access to your documents

    - **delegate_id**: The ID of the delegate to revoke access from

    Removes the delegate's ability to access your documents.
    This action cannot be undone - you will need to send a new invitation
    if you want to grant access again.
    """
    logger.info(f"[DELEGATES API] User {current_user.email} revoking delegate: {delegate_id}")

    try:
        delegate_uuid = UUID(delegate_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid delegate ID format"
        )

    success, error = await delegate_service.revoke_access(
        owner_user_id=current_user.id,
        delegate_id=delegate_uuid,
        revoked_by_user_id=current_user.id
    )

    if not success:
        if "not found" in error.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )

    logger.info(f"[DELEGATES API] Delegate access revoked: {delegate_id}")
    return {
        "success": True,
        "message": "Delegate access revoked successfully"
    }

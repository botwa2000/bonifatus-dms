# backend/app/api/delegates.py
"""
Bonifatus DMS - Delegate Access API
REST API for multi-user document access management
"""

import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
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
from app.middleware.auth_middleware import get_current_active_user
from app.database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/delegates", tags=["delegates"])


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

# backend/app/services/delegate_service.py
"""
Bonifatus DMS - Delegate Access Service
Business logic for multi-user delegate access management
"""

import logging
import secrets
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from app.database.models import User, UserDelegate, DelegateAccessLog, TierPlan
from app.database.connection import db_manager
from app.schemas.delegate_schemas import (
    DelegateInviteRequest,
    DelegateResponse,
    GrantedAccessResponse,
    AcceptInvitationResponse
)

logger = logging.getLogger(__name__)


class DelegateService:
    """Delegate access management business logic"""

    INVITATION_EXPIRY_DAYS = 7  # Invitations expire after 7 days
    PRO_TIER_ID = 2  # Only Pro tier users can invite delegates

    def __init__(self):
        pass

    def _generate_invitation_token(self) -> str:
        """Generate secure random invitation token"""
        return secrets.token_urlsafe(32)

    async def invite_delegate(
        self,
        owner_user_id: UUID,
        delegate_email: str,
        role: str = "viewer",
        access_expires_at: Optional[datetime] = None,
        allow_unregistered: bool = False
    ) -> Tuple[Optional[UserDelegate], Optional[str]]:
        """
        Invite a delegate to access owner's documents

        Returns:
            Tuple[UserDelegate, error_message]: (delegate object, error message if any)
        """
        session = db_manager.session_local()
        try:
            # Verify owner exists and is Pro tier or Admin
            owner = session.query(User).filter(User.id == owner_user_id).first()
            if not owner:
                error_msg = "Owner user not found"
                logger.warning(f"[DELEGATE] Invite failed: {error_msg} (owner_user_id={owner_user_id})")
                return None, error_msg

            if owner.tier_id < self.PRO_TIER_ID and not owner.is_admin:
                error_msg = "Only Professional tier users can invite delegates"
                logger.warning(f"[DELEGATE] Invite failed: {error_msg} (owner={owner.email}, tier_id={owner.tier_id})")
                return None, error_msg

            # Validate role
            if role not in ['viewer', 'editor', 'owner']:
                error_msg = f"Invalid role: {role}"
                logger.warning(f"[DELEGATE] Invite failed: {error_msg} (owner={owner.email})")
                return None, error_msg

            # Check if owner is trying to invite themselves
            if owner.email.lower() == delegate_email.lower():
                error_msg = "Cannot invite yourself as a delegate"
                logger.warning(f"[DELEGATE] Invite failed: {error_msg} (owner={owner.email})")
                return None, error_msg

            # Check if invitee has a BoniDoc account
            invitee_user = session.query(User).filter(
                User.email == delegate_email.lower()
            ).first()

            if not invitee_user:
                if not allow_unregistered:
                    # Return special error code that frontend can handle with confirmation dialog
                    error_msg = "USER_NOT_REGISTERED"
                    logger.info(f"[DELEGATE] User not registered, requiring confirmation (owner={owner.email}, delegate_email={delegate_email})")
                    return None, error_msg
                else:
                    # User confirmed - allow invitation to non-registered user
                    logger.info(f"[DELEGATE] Creating invitation for non-registered user (owner={owner.email}, delegate_email={delegate_email})")
                    invitee_user = None  # Will create invitation with NULL delegate_user_id

            # Check if invitation already exists (case-insensitive email comparison)
            existing = session.query(UserDelegate).filter(
                UserDelegate.owner_user_id == owner_user_id,
                UserDelegate.delegate_email == delegate_email.lower()
            ).first()

            if existing:
                if existing.status == 'active':
                    error_msg = "This user already has active access"
                    logger.warning(f"[DELEGATE] Invite failed: {error_msg} (owner={owner.email}, delegate={delegate_email})")
                    return None, error_msg
                elif existing.status == 'pending':
                    error_msg = "An invitation has already been sent to this email"
                    logger.warning(f"[DELEGATE] Invite failed: {error_msg} (owner={owner.email}, delegate={delegate_email})")
                    return None, error_msg
                elif existing.status == 'revoked':
                    # Re-invite revoked user: update existing record to pending
                    token = self._generate_invitation_token()
                    expires_at = datetime.utcnow() + timedelta(days=self.INVITATION_EXPIRY_DAYS)

                    existing.status = 'pending'
                    existing.role = role
                    existing.invitation_token = token
                    existing.invitation_sent_at = datetime.utcnow()
                    existing.invitation_expires_at = expires_at
                    existing.access_expires_at = access_expires_at
                    existing.revoked_at = None
                    existing.revoked_by = None
                    existing.delegate_user_id = invitee_user.id if invitee_user else None
                    existing.invitation_accepted_at = None

                    session.commit()
                    session.refresh(existing)

                    logger.info(f"[DELEGATE] Re-invited revoked delegate: owner={owner_user_id}, delegate_email={delegate_email}")
                    return existing, None

            # Generate invitation token for new invitation
            token = self._generate_invitation_token()
            expires_at = datetime.utcnow() + timedelta(days=self.INVITATION_EXPIRY_DAYS)

            # Create new delegate invitation
            # delegate_user_id will be NULL if user is not registered yet
            delegate = UserDelegate(
                owner_user_id=owner_user_id,
                delegate_user_id=invitee_user.id if invitee_user else None,
                delegate_email=delegate_email.lower(),
                role=role,
                status='pending',
                invitation_token=token,
                invitation_sent_at=datetime.utcnow(),
                invitation_expires_at=expires_at,
                access_expires_at=access_expires_at
            )

            session.add(delegate)
            session.commit()
            session.refresh(delegate)

            logger.info(f"[DELEGATE] Invitation created: owner={owner_user_id}, delegate_email={delegate_email}, token={token[:10]}...")
            return delegate, None

        except Exception as e:
            session.rollback()
            logger.error(f"[DELEGATE] Error inviting delegate: {e}")
            return None, f"Failed to create invitation: {str(e)}"
        finally:
            session.close()

    async def accept_invitation(
        self,
        invitation_token: str,
        delegate_user_id: UUID
    ) -> Tuple[Optional[AcceptInvitationResponse], Optional[str]]:
        """
        Accept a delegate invitation

        Returns:
            Tuple[AcceptInvitationResponse, error_message]
        """
        session = db_manager.session_local()
        try:
            # Find invitation by token
            delegate = session.query(UserDelegate).filter(
                UserDelegate.invitation_token == invitation_token
            ).first()

            if not delegate:
                return None, "Invalid invitation token"

            if delegate.status != 'pending':
                return None, "This invitation has already been processed"

            if delegate.invitation_expires_at and delegate.invitation_expires_at < datetime.utcnow():
                return None, "This invitation has expired"

            # Verify delegate user exists
            delegate_user = session.query(User).filter(User.id == delegate_user_id).first()
            if not delegate_user:
                return None, "Delegate user not found"

            # Verify delegate email matches
            if delegate_user.email.lower() != delegate.delegate_email.lower():
                return None, "This invitation was sent to a different email address"

            # Get owner info
            owner = session.query(User).filter(User.id == delegate.owner_user_id).first()
            if not owner:
                return None, "Owner user not found"

            # Accept invitation
            delegate.delegate_user_id = delegate_user_id
            delegate.status = 'active'
            delegate.invitation_accepted_at = datetime.utcnow()

            session.commit()

            logger.info(f"[DELEGATE] Invitation accepted: delegate={delegate_user_id}, owner={owner.id}")

            return AcceptInvitationResponse(
                success=True,
                owner_name=owner.full_name,
                owner_email=owner.email,
                role=delegate.role,
                message=f"You now have {delegate.role} access to {owner.full_name}'s documents"
            ), None

        except Exception as e:
            session.rollback()
            logger.error(f"[DELEGATE] Error accepting invitation: {e}")
            return None, f"Failed to accept invitation: {str(e)}"
        finally:
            session.close()

    async def list_delegates(self, owner_user_id: UUID) -> List[DelegateResponse]:
        """List all delegates for an owner"""
        session = db_manager.session_local()
        try:
            delegates = session.query(UserDelegate).filter(
                UserDelegate.owner_user_id == owner_user_id
            ).order_by(UserDelegate.created_at.desc()).all()

            return [DelegateResponse.from_orm(d) for d in delegates]

        except Exception as e:
            logger.error(f"[DELEGATE] Error listing delegates: {e}")
            return []
        finally:
            session.close()

    async def list_granted_access(self, delegate_user_id: UUID) -> List[GrantedAccessResponse]:
        """List all owners who granted access to the delegate"""
        session = db_manager.session_local()
        try:
            delegates = session.query(UserDelegate).filter(
                UserDelegate.delegate_user_id == delegate_user_id,
                UserDelegate.status == 'active'
            ).all()

            result = []
            for d in delegates:
                owner = session.query(User).filter(User.id == d.owner_user_id).first()
                if owner:
                    result.append(GrantedAccessResponse(
                        id=str(d.id),
                        owner_user_id=str(d.owner_user_id),
                        owner_email=owner.email,
                        owner_name=owner.full_name,
                        role=d.role,
                        status=d.status,
                        access_expires_at=d.access_expires_at,
                        last_accessed_at=d.last_accessed_at,
                        granted_at=d.invitation_accepted_at or d.created_at
                    ))

            return result

        except Exception as e:
            logger.error(f"[DELEGATE] Error listing granted access: {e}")
            return []
        finally:
            session.close()

    async def revoke_access(
        self,
        owner_user_id: UUID,
        delegate_id: UUID,
        revoked_by_user_id: UUID
    ) -> Tuple[bool, Optional[str]]:
        """
        Revoke delegate access

        Returns:
            Tuple[success, error_message]
        """
        session = db_manager.session_local()
        try:
            delegate = session.query(UserDelegate).filter(
                UserDelegate.id == delegate_id,
                UserDelegate.owner_user_id == owner_user_id
            ).first()

            if not delegate:
                return False, "Delegate not found"

            if delegate.status == 'revoked':
                return False, "Access already revoked"

            delegate.status = 'revoked'
            delegate.revoked_at = datetime.utcnow()
            delegate.revoked_by = revoked_by_user_id

            session.commit()

            logger.info(f"[DELEGATE] Access revoked: delegate_id={delegate_id}, owner={owner_user_id}")
            return True, None

        except Exception as e:
            session.rollback()
            logger.error(f"[DELEGATE] Error revoking access: {e}")
            return False, f"Failed to revoke access: {str(e)}"
        finally:
            session.close()

    async def check_access(
        self,
        delegate_user_id: UUID,
        owner_user_id: UUID
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if delegate has active access to owner's documents

        Returns:
            Tuple[has_access, role]
        """
        session = db_manager.session_local()
        try:
            delegate = session.query(UserDelegate).filter(
                UserDelegate.delegate_user_id == delegate_user_id,
                UserDelegate.owner_user_id == owner_user_id,
                UserDelegate.status == 'active'
            ).first()

            if not delegate:
                return False, None

            # Check if access has expired
            if delegate.access_expires_at and delegate.access_expires_at < datetime.utcnow():
                # Auto-revoke expired access
                delegate.status = 'revoked'
                delegate.revoked_at = datetime.utcnow()
                session.commit()
                return False, None

            # Update last accessed timestamp
            delegate.last_accessed_at = datetime.utcnow()
            session.commit()

            return True, delegate.role

        except Exception as e:
            logger.error(f"[DELEGATE] Error checking access: {e}")
            return False, None
        finally:
            session.close()

    async def log_access(
        self,
        delegate_user_id: UUID,
        owner_user_id: UUID,
        document_id: UUID,
        action: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Log delegate document access for audit trail"""
        session = db_manager.session_local()
        try:
            log_entry = DelegateAccessLog(
                delegate_user_id=delegate_user_id,
                owner_user_id=owner_user_id,
                document_id=document_id,
                action=action,
                ip_address=ip_address,
                user_agent=user_agent
            )

            session.add(log_entry)
            session.commit()

            return True

        except Exception as e:
            session.rollback()
            logger.error(f"[DELEGATE] Error logging access: {e}")
            return False
        finally:
            session.close()

    async def get_access_logs(
        self,
        owner_user_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[DelegateAccessLog]:
        """Get access logs for owner's documents"""
        session = db_manager.session_local()
        try:
            logs = session.query(DelegateAccessLog).filter(
                DelegateAccessLog.owner_user_id == owner_user_id
            ).order_by(
                DelegateAccessLog.accessed_at.desc()
            ).offset(offset).limit(limit).all()

            return logs

        except Exception as e:
            logger.error(f"[DELEGATE] Error fetching access logs: {e}")
            return []
        finally:
            session.close()


# Global service instance
delegate_service = DelegateService()

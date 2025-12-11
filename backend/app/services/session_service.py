# backend/app/services/session_service.py
"""
Session management service for refresh token lifecycle
Handles session creation, validation, revocation, and cleanup
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, text
from sqlalchemy.orm import Session
import uuid

from app.database.connection import db_manager
from app.database.auth_models import UserSession
from app.database.models import User
from app.services.encryption_service import encryption_service

logger = logging.getLogger(__name__)


class SessionService:
    """Manage user authentication sessions"""
    
    REFRESH_TOKEN_EXPIRY_DAYS = 7
    
    def __init__(self):
        encryption_service.initialize()
    
    async def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, str]:
        """
        Create new refresh token session
        
        Args:
            user_id: User UUID
            ip_address: Client IP address
            user_agent: Client user agent string
            session: Optional database session
            
        Returns:
            Dict with refresh_token and session_id
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            refresh_token = encryption_service.generate_secure_token(32)
            token_hash = encryption_service.hash_token(refresh_token)
            
            expires_at = datetime.now(timezone.utc) + timedelta(days=self.REFRESH_TOKEN_EXPIRY_DAYS)
            
            user_session = UserSession(
                id=uuid.uuid4(),
                user_id=uuid.UUID(user_id),
                refresh_token=token_hash,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.now(timezone.utc),
                last_activity_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                is_active=True
            )
            
            session.add(user_session)
            session.commit()
            
            logger.info(f"Created session for user {user_id}, expires {expires_at}")
            
            return {
                'refresh_token': refresh_token,
                'session_id': str(user_session.id),
                'expires_at': expires_at.isoformat()
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create session: {e}")
            raise
        finally:
            if close_session:
                session.close()
    
    async def validate_session(
        self,
        refresh_token: str,
        session: Optional[Session] = None
    ) -> Optional[Dict]:
        """
        Validate refresh token and return session info
        
        Args:
            refresh_token: Refresh token to validate
            session: Optional database session
            
        Returns:
            Dict with user_id and session_id if valid, None otherwise
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            token_hash = encryption_service.hash_token(refresh_token)
            
            result = session.execute(
                select(UserSession).where(
                    UserSession.refresh_token == token_hash,
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                )
            ).scalar_one_or_none()
            
            if not result:
                logger.warning("Invalid or expired refresh token")
                return None
            
            # Update last activity
            result.last_activity_at = datetime.now(timezone.utc)
            session.commit()
            
            return {
                'user_id': str(result.user_id),
                'session_id': str(result.id),
                'expires_at': result.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return None
        finally:
            if close_session:
                session.close()
    
    async def revoke_session(
        self,
        session_id: str,
        reason: str = "user_logout",
        session: Optional[Session] = None
    ) -> bool:
        """
        Revoke specific session
        
        Args:
            session_id: Session UUID to revoke
            reason: Reason for revocation
            session: Optional database session
            
        Returns:
            True if revoked, False otherwise
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            result = session.execute(
                text("""
                    UPDATE user_sessions
                    SET is_active = false
                    WHERE id = :session_id
                    AND is_active = true
                """),
                {
                    'session_id': session_id
                }
            )
            
            session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Revoked session {session_id}, reason: {reason}")
                return True
            else:
                logger.warning(f"Session {session_id} not found or already revoked")
                return False
                
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to revoke session: {e}")
            return False
        finally:
            if close_session:
                session.close()
    
    async def revoke_user_sessions(
        self,
        user_id: str,
        reason: str = "security_logout",
        except_session_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> int:
        """
        Revoke all sessions for user
        
        Args:
            user_id: User UUID
            reason: Reason for revocation
            except_session_id: Optional session ID to keep active
            session: Optional database session
            
        Returns:
            Number of sessions revoked
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            query = """
                UPDATE user_sessions
                SET is_active = false
                WHERE user_id = :user_id
                AND is_active = true
            """

            params = {
                'user_id': user_id
            }
            
            if except_session_id:
                query += " AND id != :except_id"
                params['except_id'] = except_session_id
            
            result = session.execute(text(query), params)
            session.commit()
            
            count = result.rowcount
            logger.info(f"Revoked {count} sessions for user {user_id}")
            return count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to revoke user sessions: {e}")
            return 0
        finally:
            if close_session:
                session.close()
    
    async def get_active_sessions(
        self,
        user_id: str,
        session: Optional[Session] = None
    ) -> List[Dict]:
        """
        Get all active sessions for user
        
        Args:
            user_id: User UUID
            session: Optional database session
            
        Returns:
            List of active session info dicts
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            results = session.execute(
                select(UserSession).where(
                    UserSession.user_id == uuid.UUID(user_id),
                    UserSession.is_active == True,
                    UserSession.expires_at > datetime.now(timezone.utc)
                ).order_by(UserSession.last_activity_at.desc())
            ).scalars().all()
            
            sessions = []
            for s in results:
                sessions.append({
                    'session_id': str(s.id),
                    'ip_address': s.ip_address,
                    'user_agent': s.user_agent,
                    'created_at': s.created_at.isoformat(),
                    'last_activity_at': s.last_activity_at.isoformat(),
                    'expires_at': s.expires_at.isoformat()
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
        finally:
            if close_session:
                session.close()
    
    async def cleanup_expired_sessions(
        self,
        session: Optional[Session] = None
    ) -> int:
        """
        Remove expired sessions from database
        
        Args:
            session: Optional database session
            
        Returns:
            Number of sessions deleted
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True
        
        try:
            result = session.execute(
                text("""
                    DELETE FROM user_sessions
                    WHERE expires_at < :now
                    OR is_active = false
                """),
                {
                    'now': datetime.now(timezone.utc)
                }
            )
            
            session.commit()
            count = result.rowcount
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired sessions")
            
            return count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to cleanup sessions: {e}")
            return 0
        finally:
            if close_session:
                session.close()


# Global instance
session_service = SessionService()
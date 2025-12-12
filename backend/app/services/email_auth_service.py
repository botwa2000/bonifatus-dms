# backend/app/services/email_auth_service.py
"""
Email/Password Authentication Service
Handles user registration, login, email verification, and password reset
"""

import logging
import secrets
import string
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone
import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.connection import db_manager
from app.database.models import User
from app.database.auth_models import EmailVerificationCode, PasswordResetToken, LoginAttempt
from app.services.encryption_service import encryption_service

logger = logging.getLogger(__name__)


class EmailAuthService:
    """Handle email/password authentication operations"""

    # Security configuration
    BCRYPT_ROUNDS = 12  # bcrypt work factor (2^12 = 4096 iterations)
    VERIFICATION_CODE_EXPIRY_MINUTES = 15
    PASSWORD_RESET_EXPIRY_HOURS = 1
    MAX_VERIFICATION_ATTEMPTS = 3
    MIN_PASSWORD_LENGTH = 12

    def __init__(self):
        encryption_service.initialize()

    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt with 12 rounds

        Args:
            password: Plain text password

        Returns:
            Bcrypt hash string
        """
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against bcrypt hash

        Args:
            password: Plain text password
            password_hash: Bcrypt hash to verify against

        Returns:
            True if password matches, False otherwise
        """
        try:
            password_bytes = password.encode('utf-8')
            hash_bytes = password_hash.encode('utf-8')
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False

    def validate_password_strength(self, password: str) -> Dict[str, any]:
        """
        Validate password meets security requirements

        Requirements:
        - Minimum 12 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 digit
        - At least 1 special character

        Args:
            password: Password to validate

        Returns:
            Dict with 'valid' bool and 'errors' list
        """
        errors = []

        if len(password) < self.MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters")

        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least 1 uppercase letter")

        if not any(c.islower() for c in password):
            errors.append("Password must contain at least 1 lowercase letter")

        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least 1 digit")

        if not any(c in string.punctuation for c in password):
            errors.append("Password must contain at least 1 special character")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    async def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        session: Optional[Session] = None
    ) -> Dict[str, any]:
        """
        Register new user with email/password

        Args:
            email: User email address
            password: Plain text password
            full_name: User's full name
            session: Optional database session

        Returns:
            Dict with 'success', 'user_id', 'message', 'verification_code_id'
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True

        try:
            # Check if email already exists
            existing_user = session.execute(
                select(User).where(User.email == email.lower())
            ).scalar_one_or_none()

            if existing_user:
                return {
                    'success': False,
                    'message': 'Email already registered'
                }

            # Validate password strength
            validation = self.validate_password_strength(password)
            if not validation['valid']:
                return {
                    'success': False,
                    'message': 'Password does not meet security requirements',
                    'errors': validation['errors']
                }

            # Hash password
            password_hash = self.hash_password(password)

            # Create user
            from uuid import uuid4
            user = User(
                id=uuid4(),
                email=email.lower(),
                full_name=full_name,
                password_hash=password_hash,
                auth_provider='email',
                email_verified=False,
                tier_id=0,  # Free tier
                is_active=True,
                preferred_doc_languages=["en"]  # Default to English
            )

            session.add(user)
            session.commit()
            session.refresh(user)

            # Generate verification code
            code_result = await self.generate_verification_code(
                user_id=str(user.id),
                email=email.lower(),
                purpose='registration',
                session=session
            )

            logger.info(f"User registered with email: {email}")

            return {
                'success': True,
                'user_id': str(user.id),
                'message': 'Registration successful. Please verify your email.',
                'verification_code_id': code_result['code_id']
            }

        except Exception as e:
            session.rollback()
            logger.error(f"User registration failed: {e}")
            return {
                'success': False,
                'message': 'Registration failed. Please try again.'
            }
        finally:
            if close_session:
                session.close()

    async def login_user(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session: Optional[Session] = None
    ) -> Dict[str, any]:
        """
        Authenticate user with email/password

        Args:
            email: User email
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent
            session: Optional database session

        Returns:
            Dict with 'success', 'user', 'message', 'requires_verification'
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True

        try:
            # Find user by email
            user = session.execute(
                select(User).where(User.email == email.lower())
            ).scalar_one_or_none()

            # Log login attempt
            await self._log_login_attempt(
                email=email.lower(),
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='invalid_email' if not user else None,
                session=session
            )

            if not user:
                return {
                    'success': False,
                    'message': 'Invalid email or password'
                }

            # Check if account is locked
            if user.account_locked_until and user.account_locked_until > datetime.now(timezone.utc):
                return {
                    'success': False,
                    'message': 'Account is temporarily locked. Please try again later.',
                    'locked_until': user.account_locked_until.isoformat()
                }

            # Check if user has password (email auth)
            if not user.password_hash:
                return {
                    'success': False,
                    'message': 'This account uses OAuth login. Please sign in with Google.'
                }

            # Verify password
            if not self.verify_password(password, user.password_hash):
                # Increment failed attempts
                user.failed_login_attempts += 1

                # Lock account after 5 failed attempts (15 minutes)
                if user.failed_login_attempts >= 5:
                    user.account_locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
                    logger.warning(f"Account locked for email: {email} (5 failed attempts)")

                session.commit()

                await self._log_login_attempt(
                    email=email.lower(),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    failure_reason='invalid_password',
                    session=session
                )

                return {
                    'success': False,
                    'message': 'Invalid email or password',
                    'attempts_remaining': max(0, 5 - user.failed_login_attempts)
                }

            # Check email verification
            if not user.email_verified:
                return {
                    'success': False,
                    'message': 'Please verify your email before logging in',
                    'requires_verification': True,
                    'user_id': str(user.id)
                }

            # Login successful - reset failed attempts
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.last_login_at = datetime.now(timezone.utc)
            user.last_login_ip = ip_address
            user.last_activity_at = datetime.now(timezone.utc)

            session.commit()

            await self._log_login_attempt(
                email=email.lower(),
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
                failure_reason=None,
                session=session
            )

            logger.info(f"User logged in: {email}")

            return {
                'success': True,
                'user': user,
                'message': 'Login successful'
            }

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return {
                'success': False,
                'message': 'Login failed. Please try again.'
            }
        finally:
            if close_session:
                session.close()

    async def generate_verification_code(
        self,
        user_id: Optional[str],
        email: str,
        purpose: str,  # 'registration', 'password_reset', 'email_change'
        session: Optional[Session] = None
    ) -> Dict[str, str]:
        """
        Generate 6-digit verification code

        Args:
            user_id: User UUID (None for new registrations)
            email: Email address
            purpose: Code purpose
            session: Optional database session

        Returns:
            Dict with 'code' and 'code_id'
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True

        try:
            # Generate random 6-digit code
            code = ''.join(secrets.choice(string.digits) for _ in range(6))

            # Create verification code record
            from uuid import uuid4, UUID
            verification_code = EmailVerificationCode(
                id=uuid4(),
                user_id=UUID(user_id) if user_id else None,
                email=email.lower(),
                code=code,
                purpose=purpose,
                attempts=0,
                max_attempts=self.MAX_VERIFICATION_ATTEMPTS,
                is_used=False,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=self.VERIFICATION_CODE_EXPIRY_MINUTES),
                created_at=datetime.now(timezone.utc)
            )

            session.add(verification_code)
            session.commit()

            logger.info(f"Verification code generated for {email} (purpose: {purpose})")

            return {
                'code': code,
                'code_id': str(verification_code.id),
                'expires_at': verification_code.expires_at.isoformat()
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to generate verification code: {e}")
            raise
        finally:
            if close_session:
                session.close()

    async def verify_code(
        self,
        email: str,
        code: str,
        purpose: str,
        session: Optional[Session] = None
    ) -> Dict[str, any]:
        """
        Verify 6-digit code

        Args:
            email: Email address
            code: 6-digit code
            purpose: Expected purpose
            session: Optional database session

        Returns:
            Dict with 'valid', 'message', 'user_id'
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True

        try:
            # Find most recent unexpired code
            verification = session.execute(
                select(EmailVerificationCode).where(
                    EmailVerificationCode.email == email.lower(),
                    EmailVerificationCode.code == code,
                    EmailVerificationCode.purpose == purpose,
                    EmailVerificationCode.is_used == False,
                    EmailVerificationCode.expires_at > datetime.now(timezone.utc)
                ).order_by(EmailVerificationCode.created_at.desc())
            ).scalar_one_or_none()

            if not verification:
                return {
                    'valid': False,
                    'message': 'Invalid or expired code'
                }

            # Check attempts
            if verification.attempts >= verification.max_attempts:
                return {
                    'valid': False,
                    'message': 'Maximum verification attempts exceeded. Please request a new code.'
                }

            # Increment attempts
            verification.attempts += 1

            # Mark as used
            verification.is_used = True

            session.commit()

            logger.info(f"Verification code validated for {email}")

            return {
                'valid': True,
                'message': 'Code verified successfully',
                'user_id': str(verification.user_id) if verification.user_id else None
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Code verification failed: {e}")
            return {
                'valid': False,
                'message': 'Verification failed. Please try again.'
            }
        finally:
            if close_session:
                session.close()

    async def generate_password_reset_token(
        self,
        email: str,
        session: Optional[Session] = None
    ) -> Optional[Dict[str, str]]:
        """
        Generate secure password reset token

        Args:
            email: User email address
            session: Optional database session

        Returns:
            Dict with 'token', 'user_id', 'expires_at' or None if user not found
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True

        try:
            # Find user
            user = session.execute(
                select(User).where(User.email == email.lower())
            ).scalar_one_or_none()

            if not user:
                return None

            # Generate secure random token (64 characters)
            token = encryption_service.generate_secure_token(32)  # Returns 64-char hex string

            # Create reset token record
            from uuid import uuid4
            reset_token = PasswordResetToken(
                id=uuid4(),
                user_id=user.id,
                token=token,
                is_used=False,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=self.PASSWORD_RESET_EXPIRY_HOURS),
                created_at=datetime.now(timezone.utc)
            )

            session.add(reset_token)
            session.commit()

            logger.info(f"Password reset token generated for {email}")

            return {
                'token': token,
                'user_id': str(user.id),
                'expires_at': reset_token.expires_at.isoformat()
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to generate password reset token: {e}")
            return None
        finally:
            if close_session:
                session.close()

    async def reset_password(
        self,
        token: str,
        new_password: str,
        session: Optional[Session] = None
    ) -> Dict[str, any]:
        """
        Reset password using token

        Args:
            token: Password reset token
            new_password: New plain text password
            session: Optional database session

        Returns:
            Dict with 'success' and 'message'
        """
        close_session = False
        if session is None:
            session = db_manager.session_local()
            close_session = True

        try:
            # Find valid token
            reset_token = session.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.token == token,
                    PasswordResetToken.is_used == False,
                    PasswordResetToken.expires_at > datetime.now(timezone.utc)
                )
            ).scalar_one_or_none()

            if not reset_token:
                return {
                    'success': False,
                    'message': 'Invalid or expired reset token'
                }

            # Validate new password
            validation = self.validate_password_strength(new_password)
            if not validation['valid']:
                return {
                    'success': False,
                    'message': 'Password does not meet security requirements',
                    'errors': validation['errors']
                }

            # Get user
            user = session.execute(
                select(User).where(User.id == reset_token.user_id)
            ).scalar_one_or_none()

            if not user:
                return {
                    'success': False,
                    'message': 'User not found'
                }

            # Hash new password
            user.password_hash = self.hash_password(new_password)

            # Mark token as used
            reset_token.is_used = True

            # Reset failed login attempts
            user.failed_login_attempts = 0
            user.account_locked_until = None

            session.commit()

            logger.info(f"Password reset successful for user {user.email}")

            return {
                'success': True,
                'message': 'Password reset successful'
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Password reset failed: {e}")
            return {
                'success': False,
                'message': 'Password reset failed. Please try again.'
            }
        finally:
            if close_session:
                session.close()

    async def _log_login_attempt(
        self,
        email: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        success: bool,
        failure_reason: Optional[str],
        session: Session
    ):
        """Log login attempt for security monitoring"""
        try:
            from uuid import uuid4
            attempt = LoginAttempt(
                id=uuid4(),
                email=email.lower(),
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                failure_reason=failure_reason,
                attempted_at=datetime.now(timezone.utc)
            )

            session.add(attempt)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log login attempt: {e}")


# Global instance
email_auth_service = EmailAuthService()

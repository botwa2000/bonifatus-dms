"""
Authentication and Email-to-Process Models
SQLAlchemy models for multi-provider authentication and email-to-process features
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, Text, ForeignKey, BigInteger, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.models import Base, TimestampMixin


# ==================== AUTHENTICATION MODELS ====================

class EmailVerificationCode(Base):
    """6-digit verification codes for email verification (15-minute expiry)"""
    __tablename__ = "email_verification_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False, index=True)
    purpose = Column(String(50), nullable=False)  # registration, password_reset, email_change
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="verification_codes")


class PasswordResetToken(Base):
    """Secure tokens for password reset flow (1-hour expiry)"""
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(64), nullable=False, unique=True, index=True)
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="reset_tokens")


class RegisteredDevice(Base):
    """Trusted devices for biometric/passcode authentication"""
    __tablename__ = "registered_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    device_name = Column(String(255), nullable=False)
    device_type = Column(String(50), nullable=False)  # mobile, desktop, tablet
    platform = Column(String(50), nullable=True)  # ios, android, windows, macos, linux
    browser = Column(String(100), nullable=True)
    device_token = Column(String(255), nullable=False, unique=True, index=True)

    # WebAuthn/FIDO2 fields for biometric authentication
    biometric_public_key = Column(Text, nullable=True)
    biometric_credential_id = Column(String(255), nullable=True)
    biometric_counter = Column(Integer, default=0, nullable=False)

    is_trusted = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_ip_address = Column(String(45), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="devices")


class UserSession(Base, TimestampMixin):
    """Active login sessions for security monitoring"""
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    device_id = Column(UUID(as_uuid=True), ForeignKey('registered_devices.id', ondelete='SET NULL'), nullable=True)
    session_token = Column(String(64), nullable=False, unique=True, index=True)
    refresh_token = Column(String(64), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")
    device = relationship("RegisteredDevice", backref="sessions")


class LoginAttempt(Base):
    """Track failed login attempts for security monitoring"""
    __tablename__ = "login_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    user_agent = Column(String(500), nullable=True)
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String(255), nullable=True)
    attempted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


# ==================== EMAIL-TO-PROCESS MODELS ====================

class EmailSettings(Base, TimestampMixin):
    """Email-to-process configuration per user"""
    __tablename__ = "email_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    email_address = Column(String(255), nullable=False, unique=True, index=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    daily_email_limit = Column(Integer, default=50, nullable=False)
    max_attachment_size_mb = Column(Integer, default=20, nullable=False)
    auto_categorize = Column(Boolean, default=True, nullable=False)
    send_confirmation_email = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", backref="email_settings", uselist=False)


class AllowedSender(Base):
    """Whitelist of email addresses for email-to-process"""
    __tablename__ = "allowed_senders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_email = Column(String(255), nullable=False, index=True)
    sender_name = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    trust_level = Column(String(20), default='normal', nullable=False)  # high, normal, low
    notes = Column(Text, nullable=True)
    last_email_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="allowed_senders")

    __table_args__ = (
        Index('idx_allowed_senders_user_email', 'user_id', 'sender_email', unique=True),
    )


class EmailProcessingLog(Base):
    """Track received emails for monitoring and debugging"""
    __tablename__ = "email_processing_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_email = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=True)
    attachment_count = Column(Integer, default=0, nullable=False)
    total_size_bytes = Column(BigInteger, default=0, nullable=False)
    status = Column(String(50), nullable=False, index=True)  # received, processing, completed, rejected, failed
    rejection_reason = Column(String(500), nullable=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('upload_batches.id', ondelete='SET NULL'), nullable=True)
    documents_created = Column(Integer, default=0, nullable=False)
    processing_time_ms = Column(Integer, nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="email_logs")
    batch = relationship("UploadBatch", backref="email_logs")


class EmailRateLimit(Base):
    """Track daily email counts for rate limiting"""
    __tablename__ = "email_rate_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date = Column(Date, nullable=False)
    email_count = Column(Integer, default=0, nullable=False)
    last_reset_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="email_rate_limits")

    __table_args__ = (
        Index('idx_rate_limits_user_date', 'user_id', 'date', unique=True),
    )

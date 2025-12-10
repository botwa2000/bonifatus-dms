"""add multi-provider authentication and email-to-process

Revision ID: 040_multi_auth_email
Revises: 039_add_address_quality
Create Date: 2025-12-09 22:00:00

Add comprehensive authentication and email-to-process features:
- Email/password authentication with verification codes
- Password reset tokens
- Device registration for biometric/passcode login
- Email-to-process settings and logging
- Allowed senders whitelist
- Rate limiting tracking
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '040_multi_auth_email'
down_revision = '039_add_address_quality'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== EXTEND USERS TABLE ====================
    # Add email/password authentication fields
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), default=False, nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(50), default='google', nullable=False, server_default='google'))  # google, email, microsoft, facebook, apple
    op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), default=False, nullable=False, server_default='false'))
    op.add_column('users', sa.Column('two_factor_secret', sa.String(255), nullable=True))  # TOTP secret (encrypted)

    # Make google_id nullable (email/password users won't have google_id)
    op.alter_column('users', 'google_id', nullable=True)

    # ==================== EMAIL VERIFICATION CODES TABLE ====================
    # Store 6-digit verification codes for email verification (15-minute expiry)
    op.create_table(
        'email_verification_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),  # Nullable for new registrations
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('code', sa.String(6), nullable=False),
        sa.Column('purpose', sa.String(50), nullable=False),  # registration, password_reset, email_change
        sa.Column('attempts', sa.Integer(), default=0, nullable=False),
        sa.Column('max_attempts', sa.Integer(), default=3, nullable=False),
        sa.Column('is_used', sa.Boolean(), default=False, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_verification_codes_email', 'email_verification_codes', ['email'])
    op.create_index('idx_verification_codes_code', 'email_verification_codes', ['code'])
    op.create_index('idx_verification_codes_expires', 'email_verification_codes', ['expires_at'])

    # ==================== PASSWORD RESET TOKENS TABLE ====================
    # Secure tokens for password reset flow (1-hour expiry)
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(64), nullable=False, unique=True),  # Cryptographically secure random token
        sa.Column('is_used', sa.Boolean(), default=False, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_reset_tokens_token', 'password_reset_tokens', ['token'])
    op.create_index('idx_reset_tokens_expires', 'password_reset_tokens', ['expires_at'])

    # ==================== REGISTERED DEVICES TABLE ====================
    # Store trusted devices for biometric/passcode authentication
    op.create_table(
        'registered_devices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_name', sa.String(255), nullable=False),  # "iPhone 14 Pro", "Chrome on Windows"
        sa.Column('device_type', sa.String(50), nullable=False),  # mobile, desktop, tablet
        sa.Column('platform', sa.String(50), nullable=True),  # ios, android, windows, macos, linux
        sa.Column('browser', sa.String(100), nullable=True),
        sa.Column('device_token', sa.String(255), nullable=False, unique=True),  # Secure random token
        sa.Column('biometric_public_key', sa.Text(), nullable=True),  # For WebAuthn/FIDO2
        sa.Column('biometric_credential_id', sa.String(255), nullable=True),  # WebAuthn credential ID
        sa.Column('biometric_counter', sa.Integer(), default=0, nullable=False),  # WebAuthn signature counter
        sa.Column('is_trusted', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),  # 30-day expiry for "Remember me"
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_devices_user', 'registered_devices', ['user_id'])
    op.create_index('idx_devices_token', 'registered_devices', ['device_token'])

    # ==================== USER SESSIONS TABLE ====================
    # Track active login sessions for security monitoring
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_token', sa.String(64), nullable=False, unique=True),
        sa.Column('refresh_token', sa.String(64), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], ['registered_devices.id'], ondelete='SET NULL')
    )
    op.create_index('idx_sessions_user', 'user_sessions', ['user_id'])
    op.create_index('idx_sessions_token', 'user_sessions', ['session_token'])
    op.create_index('idx_sessions_active', 'user_sessions', ['is_active'])

    # ==================== EMAIL SETTINGS TABLE ====================
    # Email-to-process configuration per user
    op.create_table(
        'email_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_address', sa.String(255), nullable=False, unique=True),  # {user_id}@docs.bonidoc.com
        sa.Column('is_enabled', sa.Boolean(), default=True, nullable=False),
        sa.Column('daily_email_limit', sa.Integer(), default=50, nullable=False),
        sa.Column('max_attachment_size_mb', sa.Integer(), default=20, nullable=False),
        sa.Column('auto_categorize', sa.Boolean(), default=True, nullable=False),
        sa.Column('send_confirmation_email', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_email_settings_user', 'email_settings', ['user_id'])
    op.create_index('idx_email_settings_email', 'email_settings', ['email_address'])

    # ==================== ALLOWED SENDERS TABLE ====================
    # Whitelist of email addresses for email-to-process
    op.create_table(
        'allowed_senders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_email', sa.String(255), nullable=False),
        sa.Column('sender_name', sa.String(255), nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('trust_level', sa.String(20), default='normal', nullable=False),  # high, normal, low
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_email_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'sender_email', name='uq_user_sender')
    )
    op.create_index('idx_allowed_senders_user', 'allowed_senders', ['user_id'])
    op.create_index('idx_allowed_senders_email', 'allowed_senders', ['sender_email'])

    # ==================== EMAIL PROCESSING LOGS TABLE ====================
    # Track received emails for monitoring
    op.create_table(
        'email_processing_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_email', sa.String(255), nullable=False),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('attachment_count', sa.Integer(), default=0, nullable=False),
        sa.Column('total_size_bytes', sa.BigInteger(), default=0, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),  # received, processing, completed, rejected, failed
        sa.Column('rejection_reason', sa.String(500), nullable=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('documents_created', sa.Integer(), default=0, nullable=False),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['batch_id'], ['upload_batches.id'], ondelete='SET NULL')
    )
    op.create_index('idx_email_logs_user', 'email_processing_logs', ['user_id'])
    op.create_index('idx_email_logs_status', 'email_processing_logs', ['status'])
    op.create_index('idx_email_logs_received', 'email_processing_logs', ['received_at'])

    # ==================== EMAIL RATE LIMITING TABLE ====================
    # Track daily email counts for rate limiting
    op.create_table(
        'email_rate_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('email_count', sa.Integer(), default=0, nullable=False),
        sa.Column('last_reset_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'date', name='uq_user_date')
    )
    op.create_index('idx_rate_limits_user_date', 'email_rate_limits', ['user_id', 'date'])

    # ==================== LOGIN ATTEMPTS TABLE ====================
    # Track failed login attempts for security monitoring and rate limiting
    op.create_table(
        'login_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('failure_reason', sa.String(255), nullable=True),  # invalid_password, account_locked, email_not_verified
        sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('idx_login_attempts_email', 'login_attempts', ['email'])
    op.create_index('idx_login_attempts_ip', 'login_attempts', ['ip_address'])
    op.create_index('idx_login_attempts_time', 'login_attempts', ['attempted_at'])


def downgrade():
    op.drop_table('login_attempts')
    op.drop_table('email_rate_limits')
    op.drop_table('email_processing_logs')
    op.drop_table('allowed_senders')
    op.drop_table('email_settings')
    op.drop_table('user_sessions')
    op.drop_table('registered_devices')
    op.drop_table('password_reset_tokens')
    op.drop_table('email_verification_codes')

    # Restore google_id to not nullable
    op.alter_column('users', 'google_id', nullable=False)

    # Drop added columns from users table
    op.drop_column('users', 'two_factor_secret')
    op.drop_column('users', 'two_factor_enabled')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'password_hash')

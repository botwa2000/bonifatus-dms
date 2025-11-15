"""add email templates table

Revision ID: 019_add_email_templates
Revises: 018_batch_jobs
Create Date: 2025-11-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

revision = '019_add_email_templates'
down_revision = '018_batch_jobs'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create email_templates table
    op.create_table(
        'email_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('template_key', sa.String(100), nullable=False),
        sa.Column('language', sa.String(2), nullable=False, server_default='en'),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('html_content', sa.Text, nullable=False),
        sa.Column('variables', JSONB, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index('idx_email_template_key_lang', 'email_templates', ['template_key', 'language'], unique=True)
    op.create_index('idx_email_template_active', 'email_templates', ['is_active'])

    # Insert default templates
    op.execute("""
        INSERT INTO email_templates (id, template_key, language, subject, html_content, variables, description, is_active)
        VALUES
        (
            gen_random_uuid(),
            'welcome_email',
            'en',
            'Welcome to BoniDoc!',
            '<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;"><h2>Welcome to BoniDoc, {{user_name}}!</h2><p>Your account has been created successfully.</p><p>You can now log in and start organizing your documents:</p><p><a href="{{login_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Login</a></p><p>If you have any questions, feel free to contact our support team.</p><p>Best regards,<br>The BoniDoc Team</p></body></html>',
            '["user_name", "login_url"]'::jsonb,
            'Welcome email sent to new users after account creation',
            true
        ),
        (
            gen_random_uuid(),
            'password_reset',
            'en',
            'Reset Your BoniDoc Password',
            '<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;"><h2>Password Reset Request</h2><p>Hello {{user_name}},</p><p>We received a request to reset your BoniDoc password.</p><p>Click the button below to reset your password:</p><p><a href="{{reset_url}}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p><p>This link will expire in 1 hour.</p><p>If you didn''t request a password reset, please ignore this email.</p><p>Best regards,<br>The BoniDoc Team</p></body></html>',
            '["user_name", "reset_url"]'::jsonb,
            'Password reset email with secure reset link',
            true
        ),
        (
            gen_random_uuid(),
            'verification_code',
            'en',
            'Your BoniDoc Verification Code',
            '<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;"><h2>Verification Code</h2><p>Hello {{user_name}},</p><p>Your verification code is:</p><h1 style="color: #4CAF50; font-size: 36px; letter-spacing: 5px;">{{verification_code}}</h1><p>This code will expire in 10 minutes.</p><p>If you didn''t request this code, please secure your account immediately.</p><p>Best regards,<br>The BoniDoc Team</p></body></html>',
            '["user_name", "verification_code"]'::jsonb,
            '2FA verification code email',
            true
        )
    """)

def downgrade() -> None:
    op.drop_index('idx_email_template_active', 'email_templates')
    op.drop_index('idx_email_template_key_lang', 'email_templates')
    op.drop_table('email_templates')

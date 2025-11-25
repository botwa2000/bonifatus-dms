"""fix email templates and add feedback tables for cancellations/deletions

Revision ID: 026_fix_email_and_feedback
Revises: 025_add_complete_email_templates
Create Date: 2025-11-25 20:00:00

Email Template Fixes:
- Welcome email: button goes to dashboard, not login page
- Invoice email: show amount, use invoice_pdf_url, remove support center
- Cancellation email: add cancellation_date, reactivate goes to homepage
- Subscription email: show amount/currency, remove support center
- All clickable links are now buttons for consistency
- Variables match what webhook code actually passes

New Feedback Tables:
- subscription_cancellation_feedback: Store reasons when users cancel subscriptions
- account_deletion_feedback: Store anonymous feedback when users delete accounts
  (anonymous because user_id is deleted, but captures tier, tenure, usage stats)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '026_fix_email_and_feedback'
down_revision = '025_add_complete_email_templates'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== EMAIL TEMPLATE FIXES ====================

    # Fix welcome_email - button goes to dashboard (homepage), not login
    op.execute("""
        UPDATE email_templates
        SET
            subject = 'Welcome to BoniDoc!',
            html_body = '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Welcome to BoniDoc!</h2>
<p>Hi {{user_name}},</p>
<p>Your account has been created successfully.</p>

<p>Get started with organizing your documents:</p>
<p><a href="{{dashboard_url}}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Go to Dashboard</a></p>

<p>If you have any questions, feel free to reply to this email.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            text_body = 'Welcome to BoniDoc!

Hi {{user_name}},

Your account has been created successfully.

Get started with organizing your documents:
{{dashboard_url}}

If you have any questions, feel free to reply to this email.

Best regards,
The BoniDoc Team',
            available_variables = '["user_name", "dashboard_url"]'::jsonb
        WHERE name = 'welcome_email';
    """)

    # Fix subscription_confirmation - show amount/currency, dashboard as button, remove support
    op.execute("""
        UPDATE email_templates
        SET
            subject = 'Welcome to {{plan_name}}!',
            html_body = '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Welcome to {{plan_name}}!</h2>
<p>Hi {{user_name}},</p>
<p>Thank you for subscribing to BoniDoc! Your {{plan_name}} subscription is now active.</p>

<h3>Subscription Details</h3>
<p><strong>Plan:</strong> {{plan_name}}<br>
<strong>Billing:</strong> {{billing_cycle}}<br>
<strong>Amount:</strong> {{currency_symbol}}{{amount}}/{{billing_period}}<br>
<strong>Next billing date:</strong> {{next_billing_date}}</p>

<h3>Your Plan Includes</h3>
<p>• {{tier_feature_1}}<br>
• {{tier_feature_2}}<br>
• {{tier_feature_3}}</p>

<p><a href="{{dashboard_url}}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Go to Dashboard</a></p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            text_body = 'Welcome to {{plan_name}}!

Hi {{user_name}},

Thank you for subscribing to BoniDoc! Your {{plan_name}} subscription is now active.

Subscription Details:
- Plan: {{plan_name}}
- Billing: {{billing_cycle}}
- Amount: {{currency_symbol}}{{amount}}/{{billing_period}}
- Next billing date: {{next_billing_date}}

Your Plan Includes:
- {{tier_feature_1}}
- {{tier_feature_2}}
- {{tier_feature_3}}

Go to Dashboard: {{dashboard_url}}

Best regards,
The BoniDoc Team',
            available_variables = '["user_name", "plan_name", "billing_cycle", "amount", "currency_symbol", "billing_period", "next_billing_date", "tier_feature_1", "tier_feature_2", "tier_feature_3", "dashboard_url"]'::jsonb
        WHERE name = 'subscription_confirmation';
    """)

    # Fix cancellation_confirmation - add cancellation_date, homepage button, signature
    op.execute("""
        UPDATE email_templates
        SET
            subject = 'Subscription Canceled',
            html_body = '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Subscription Canceled</h2>
<p>Hi {{user_name}},</p>
<p>Your {{plan_name}} subscription has been canceled.</p>

<h3>Cancellation Details</h3>
<p><strong>Plan:</strong> {{plan_name}}<br>
<strong>Canceled on:</strong> {{cancellation_date}}<br>
<strong>Access until:</strong> {{access_end_date}}</p>

<p>You will continue to have access to your subscription benefits until {{access_end_date}}.</p>

<p>Changed your mind? You can reactivate anytime:</p>
<p><a href="{{dashboard_url}}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Reactivate Subscription</a></p>

<p>We are sorry to see you go. If you have feedback on how we can improve, please reply to this email.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            text_body = 'Subscription Canceled

Hi {{user_name}},

Your {{plan_name}} subscription has been canceled.

Cancellation Details:
- Plan: {{plan_name}}
- Canceled on: {{cancellation_date}}
- Access until: {{access_end_date}}

You will continue to have access to your subscription benefits until {{access_end_date}}.

Changed your mind? You can reactivate anytime:
{{dashboard_url}}

We are sorry to see you go. If you have feedback on how we can improve, please reply to this email.

Best regards,
The BoniDoc Team',
            available_variables = '["user_name", "plan_name", "cancellation_date", "access_end_date", "dashboard_url"]'::jsonb
        WHERE name = 'cancellation_confirmation';
    """)

    # Fix invoice_email - show amount with currency, PDF link button, remove support
    op.execute("""
        UPDATE email_templates
        SET
            subject = 'Payment Received - Thank You!',
            html_body = '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Payment Received - Thank You!</h2>
<p>Hi {{user_name}},</p>
<p>We have successfully processed your payment for {{plan_name}}.</p>

<h3>Invoice Details</h3>
<p><strong>Invoice #:</strong> {{invoice_number}}<br>
<strong>Date:</strong> {{invoice_date}}<br>
<strong>Amount:</strong> {{currency_symbol}}{{amount}}<br>
<strong>Billing Period:</strong> {{period_start}} - {{period_end}}</p>

<p><a href="{{invoice_pdf_url}}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Download Invoice (PDF)</a></p>

<p>Your subscription is active and you have full access to all features.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            text_body = 'Payment Received - Thank You!

Hi {{user_name}},

We have successfully processed your payment for {{plan_name}}.

Invoice Details:
- Invoice #: {{invoice_number}}
- Date: {{invoice_date}}
- Amount: {{currency_symbol}}{{amount}}
- Billing Period: {{period_start}} - {{period_end}}

Download Invoice (PDF): {{invoice_pdf_url}}

Your subscription is active and you have full access to all features.

Best regards,
The BoniDoc Team',
            available_variables = '["user_name", "plan_name", "invoice_number", "invoice_date", "amount", "currency_symbol", "period_start", "period_end", "invoice_pdf_url"]'::jsonb
        WHERE name = 'invoice_email';
    """)

    # ==================== FEEDBACK TABLES ====================

    # Table for subscription cancellation feedback
    # User account still exists, so we can link to user_id
    op.create_table(
        'subscription_cancellation_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('plan_name', sa.String(100), nullable=True),
        sa.Column('billing_cycle', sa.String(20), nullable=True),
        sa.Column('days_subscribed', sa.Integer, nullable=True),
        sa.Column('reason_category', sa.String(100), nullable=True),  # 'too_expensive', 'not_using', 'missing_features', 'switching_to_competitor', 'other'
        sa.Column('feedback_text', sa.Text, nullable=True),
        sa.Column('would_recommend', sa.Boolean, nullable=True),  # Optional NPS-style question
        sa.Column('cancellation_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for analytics queries
    op.create_index('idx_sub_cancel_feedback_date', 'subscription_cancellation_feedback', ['cancellation_date'])
    op.create_index('idx_sub_cancel_feedback_reason', 'subscription_cancellation_feedback', ['reason_category'])
    op.create_index('idx_sub_cancel_feedback_plan', 'subscription_cancellation_feedback', ['plan_name'])

    # Table for account deletion feedback
    # Anonymous (no user_id) since account is being deleted
    # But capture useful metrics for analysis
    op.create_table(
        'account_deletion_feedback',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('anonymous_id', sa.String(64), nullable=False),  # Hashed identifier (e.g., SHA256 of email)
        sa.Column('tier_at_deletion', sa.String(50), nullable=True),  # 'free', 'starter', 'professional', 'enterprise'
        sa.Column('days_since_registration', sa.Integer, nullable=True),
        sa.Column('total_documents_uploaded', sa.Integer, nullable=True),
        sa.Column('had_active_subscription', sa.Boolean, nullable=True),
        sa.Column('reason_category', sa.String(100), nullable=True),  # 'privacy_concerns', 'not_useful', 'too_complex', 'switching_service', 'other'
        sa.Column('feedback_text', sa.Text, nullable=True),
        sa.Column('would_return', sa.Boolean, nullable=True),  # Would you come back if we improved X?
        sa.Column('deletion_date', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes for analytics queries
    op.create_index('idx_acct_delete_feedback_date', 'account_deletion_feedback', ['deletion_date'])
    op.create_index('idx_acct_delete_feedback_reason', 'account_deletion_feedback', ['reason_category'])
    op.create_index('idx_acct_delete_feedback_tier', 'account_deletion_feedback', ['tier_at_deletion'])


def downgrade():
    # Drop feedback tables
    op.drop_index('idx_acct_delete_feedback_tier', 'account_deletion_feedback')
    op.drop_index('idx_acct_delete_feedback_reason', 'account_deletion_feedback')
    op.drop_index('idx_acct_delete_feedback_date', 'account_deletion_feedback')
    op.drop_table('account_deletion_feedback')

    op.drop_index('idx_sub_cancel_feedback_plan', 'subscription_cancellation_feedback')
    op.drop_index('idx_sub_cancel_feedback_reason', 'subscription_cancellation_feedback')
    op.drop_index('idx_sub_cancel_feedback_date', 'subscription_cancellation_feedback')
    op.drop_table('subscription_cancellation_feedback')

    # Revert email templates (optional - can be skipped if not critical)
    pass

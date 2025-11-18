"""add email templates

Revision ID: 20251118_154253
Revises: 022
Create Date: 2025-11-18 15:42:53

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251118_154253'
down_revision = '022'
branch_labels = None
depends_on = None


def upgrade():
    # Drop old table if exists (from previous schema)
    op.execute("DROP TABLE IF EXISTS email_templates CASCADE")

    # Create email_templates table
    op.create_table(
        'email_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('html_body', sa.Text(), nullable=False),
        sa.Column('text_body', sa.Text(), nullable=True),
        sa.Column('available_variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('category', sa.String(length=50), nullable=False, server_default='subscription'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('send_from_name', sa.String(length=100), nullable=True),
        sa.Column('send_from_email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create indexes
    op.create_index('idx_email_template_name', 'email_templates', ['name'], unique=False)
    op.create_index('idx_email_template_category', 'email_templates', ['category'], unique=False)
    op.create_index('idx_email_template_active', 'email_templates', ['is_active'], unique=False)

    # Insert default email templates
    op.execute("""
        INSERT INTO email_templates (name, display_name, description, subject, html_body, text_body, available_variables, category, is_system)
        VALUES
        (
            'subscription_confirmation',
            'Subscription Confirmation',
            'Sent immediately after successful subscription purchase',
            'Welcome to {{plan_name}}! Your subscription is confirmed',
            '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
        <h1 style="color: #2563eb; margin-bottom: 20px;">Welcome to {{plan_name}}!</h1>

        <p>Hi {{user_name}},</p>

        <p>Thank you for subscribing to BoniDoc! Your {{plan_name}} subscription is now active.</p>

        <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2 style="font-size: 18px; margin-top: 0;">Subscription Details</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;"><strong>Plan:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{{plan_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;"><strong>Billing:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{{billing_cycle}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;"><strong>Amount:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{{currency_symbol}}{{amount}}/{{billing_period}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Next billing date:</strong></td>
                    <td style="padding: 8px 0; text-align: right;">{{next_billing_date}}</td>
                </tr>
            </table>
        </div>

        <p>You now have access to all premium features. Get started by:</p>
        <ul>
            <li>Uploading your first document</li>
            <li>Exploring AI-powered categorization</li>
            <li>Customizing your categories</li>
        </ul>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{dashboard_url}}" style="background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block;">Go to Dashboard</a>
        </div>

        <p style="font-size: 14px; color: #6b7280; margin-top: 30px;">
            Need help? Reply to this email or visit our <a href="{{support_url}}" style="color: #2563eb;">support center</a>.
        </p>
    </div>
</body>
</html>',
            'Welcome to {{plan_name}}!

Hi {{user_name}},

Thank you for subscribing to BoniDoc! Your {{plan_name}} subscription is now active.

Subscription Details:
- Plan: {{plan_name}}
- Billing: {{billing_cycle}}
- Amount: {{currency_symbol}}{{amount}}/{{billing_period}}
- Next billing date: {{next_billing_date}}

You now have access to all premium features. Get started by:
- Uploading your first document
- Exploring AI-powered categorization
- Customizing your categories

Go to your dashboard: {{dashboard_url}}

Need help? Reply to this email or visit our support center: {{support_url}}',
            '["user_name", "plan_name", "billing_cycle", "billing_period", "amount", "currency_symbol", "next_billing_date", "dashboard_url", "support_url"]',
            'subscription',
            true
        ),
        (
            'invoice_email',
            'Invoice Email',
            'Sent when invoice is generated and payment succeeds',
            'Your invoice from BoniDoc - {{invoice_number}}',
            '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
        <h1 style="color: #2563eb; margin-bottom: 20px;">Invoice {{invoice_number}}</h1>

        <p>Hi {{user_name}},</p>

        <p>Your payment for BoniDoc {{plan_name}} has been processed successfully.</p>

        <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h2 style="font-size: 18px; margin-top: 0;">Invoice Details</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;"><strong>Invoice Number:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{{invoice_number}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;"><strong>Date:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{{invoice_date}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;"><strong>Subscription:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{{plan_name}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;"><strong>Billing Period:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">{{period_start}} - {{period_end}}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; padding-top: 16px;"><strong>Total Paid:</strong></td>
                    <td style="padding: 8px 0; padding-top: 16px; text-align: right; font-size: 18px; color: #16a34a;">{{currency_symbol}}{{amount}}</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{invoice_pdf_url}}" style="background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block;">Download PDF</a>
        </div>

        <p style="font-size: 14px; color: #6b7280; margin-top: 30px;">
            Questions about this invoice? Contact our <a href="{{support_url}}" style="color: #2563eb;">billing support</a>.
        </p>
    </div>
</body>
</html>',
            'Invoice {{invoice_number}}

Hi {{user_name}},

Your payment for BoniDoc {{plan_name}} has been processed successfully.

Invoice Details:
- Invoice Number: {{invoice_number}}
- Date: {{invoice_date}}
- Subscription: {{plan_name}}
- Billing Period: {{period_start}} - {{period_end}}
- Total Paid: {{currency_symbol}}{{amount}}

Download PDF: {{invoice_pdf_url}}

Questions about this invoice? Contact our billing support: {{support_url}}',
            '["user_name", "plan_name", "invoice_number", "invoice_date", "period_start", "period_end", "amount", "currency_symbol", "invoice_pdf_url", "support_url"]',
            'billing',
            true
        ),
        (
            'cancellation_confirmation',
            'Cancellation Confirmation',
            'Sent when user cancels their subscription',
            'Your BoniDoc subscription has been cancelled',
            '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
        <h1 style="color: #dc2626; margin-bottom: 20px;">Subscription Cancelled</h1>

        <p>Hi {{user_name}},</p>

        <p>We''re sad to see you go! Your {{plan_name}} subscription has been cancelled as requested.</p>

        <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0;"><strong>Your access continues until:</strong> {{access_end_date}}</p>
        </div>

        <p>You''ll still have access to all premium features until {{access_end_date}}. After that, your account will automatically switch to the Free tier.</p>

        <h3 style="margin-top: 30px;">With the Free tier, you''ll have:</h3>
        <ul>
            <li>{{free_tier_feature_1}}</li>
            <li>{{free_tier_feature_2}}</li>
            <li>{{free_tier_feature_3}}</li>
        </ul>

        <p style="background-color: white; padding: 20px; border-radius: 8px; margin: 30px 0;">
            <strong>Changed your mind?</strong> You can reactivate your subscription anytime before {{access_end_date}} without losing any data.
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{reactivate_url}}" style="background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block;">Reactivate Subscription</a>
        </div>

        <p style="font-size: 14px; color: #6b7280; margin-top: 30px;">
            We''d love to hear your feedback! <a href="{{feedback_url}}" style="color: #2563eb;">Tell us why you cancelled</a> (1 minute survey)
        </p>
    </div>
</body>
</html>',
            'Subscription Cancelled

Hi {{user_name}},

We''re sad to see you go! Your {{plan_name}} subscription has been cancelled as requested.

Your access continues until: {{access_end_date}}

You''ll still have access to all premium features until {{access_end_date}}. After that, your account will automatically switch to the Free tier.

With the Free tier, you''ll have:
- {{free_tier_feature_1}}
- {{free_tier_feature_2}}
- {{free_tier_feature_3}}

Changed your mind? You can reactivate your subscription anytime before {{access_end_date}} without losing any data.

Reactivate: {{reactivate_url}}

We''d love to hear your feedback! Tell us why you cancelled: {{feedback_url}}',
            '["user_name", "plan_name", "access_end_date", "free_tier_feature_1", "free_tier_feature_2", "free_tier_feature_3", "reactivate_url", "feedback_url", "support_url"]',
            'subscription',
            true
        )
    """)


def downgrade():
    op.drop_index('idx_email_template_active', table_name='email_templates')
    op.drop_index('idx_email_template_category', table_name='email_templates')
    op.drop_index('idx_email_template_name', table_name='email_templates')
    op.drop_table('email_templates')

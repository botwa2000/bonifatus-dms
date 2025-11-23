"""update subscription confirmation email template with tier features

Revision ID: 20251123_122400
Revises: 20251118_154253
Create Date: 2025-11-23 12:24:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251123_122400'
down_revision = '20251118_154253'
branch_labels = None
depends_on = None


def upgrade():
    # Update subscription_confirmation template to use tier features instead of generic bullets
    # Add new variables for tier features and update the HTML
    op.execute("""
        UPDATE email_templates
        SET
            html_body = '<!DOCTYPE html>
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

        <h3 style="margin-top: 30px;">Your Plan Features:</h3>
        <ul>
            <li>{{tier_feature_1}}</li>
            <li>{{tier_feature_2}}</li>
            <li>{{tier_feature_3}}</li>
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
            text_body = 'Welcome to {{plan_name}}!

Hi {{user_name}},

Thank you for subscribing to BoniDoc! Your {{plan_name}} subscription is now active.

Subscription Details:
- Plan: {{plan_name}}
- Billing: {{billing_cycle}}
- Amount: {{currency_symbol}}{{amount}}/{{billing_period}}
- Next billing date: {{next_billing_date}}

Your Plan Features:
- {{tier_feature_1}}
- {{tier_feature_2}}
- {{tier_feature_3}}

Go to your dashboard: {{dashboard_url}}

Need help? Reply to this email or visit our support center: {{support_url}}',
            available_variables = '["user_name", "plan_name", "billing_cycle", "billing_period", "amount", "currency_symbol", "next_billing_date", "tier_feature_1", "tier_feature_2", "tier_feature_3", "dashboard_url", "support_url"]'::jsonb
        WHERE name = 'subscription_confirmation';
    """)


def downgrade():
    # Revert to original template with generic bullets
    op.execute("""
        UPDATE email_templates
        SET
            html_body = '<!DOCTYPE html>
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
            text_body = 'Welcome to {{plan_name}}!

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
            available_variables = '["user_name", "plan_name", "billing_cycle", "billing_period", "amount", "currency_symbol", "next_billing_date", "dashboard_url", "support_url"]'::jsonb
        WHERE name = 'subscription_confirmation';
    """)

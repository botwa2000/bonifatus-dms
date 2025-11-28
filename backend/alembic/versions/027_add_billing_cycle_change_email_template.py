"""add billing cycle change email template

Revision ID: 027_add_billing_cycle_change_template
Revises: 026_fix_email_and_feedback
Create Date: 2025-11-28 00:00:00

Email Template:
- Billing cycle change confirmation email
- Notifies user when billing cycle changes from monthly to yearly or vice versa
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '027_add_billing_cycle_change_template'
down_revision = '026_fix_email_and_feedback'
branch_labels = None
depends_on = None


def upgrade():
    # Add billing cycle change confirmation email template
    op.execute("""
        INSERT INTO email_templates (name, display_name, category, subject, html_body, text_body, available_variables, created_at, updated_at)
        VALUES (
            'billing_cycle_change_confirmation',
            'Billing Cycle Change Confirmation',
            'subscription',
            'Billing Cycle Updated',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Billing Cycle Updated</h2>
<p>Hi {{user_name}},</p>
<p>Your subscription billing cycle has been successfully updated.</p>

<h3>Updated Subscription Details</h3>
<p><strong>Plan:</strong> {{plan_name}}<br>
<strong>Previous Billing:</strong> {{old_billing_cycle}}<br>
<strong>New Billing:</strong> {{new_billing_cycle}}<br>
<strong>New Price:</strong> {{new_amount}} {{currency}}/{{billing_period}}<br>
<strong>Change Effective:</strong> {{change_effective_date}}<br>
<strong>Next Billing Date:</strong> {{next_billing_date}}</p>

<p>{{change_info}}</p>

<p><a href="{{dashboard_url}}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Subscription</a></p>

<p>If you have any questions about this change, feel free to reply to this email.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            'Billing Cycle Updated

Hi {{user_name}},

Your subscription billing cycle has been successfully updated.

Updated Subscription Details:
- Plan: {{plan_name}}
- Previous Billing: {{old_billing_cycle}}
- New Billing: {{new_billing_cycle}}
- New Price: {{new_amount}} {{currency}}/{{billing_period}}
- Change Effective: {{change_effective_date}}
- Next Billing Date: {{next_billing_date}}

{{change_info}}

View Subscription: {{dashboard_url}}

If you have any questions about this change, feel free to reply to this email.

Best regards,
The BoniDoc Team',
            '["user_name", "plan_name", "old_billing_cycle", "new_billing_cycle", "new_amount", "currency", "billing_period", "change_effective_date", "next_billing_date", "change_info", "dashboard_url"]'::jsonb,
            now(),
            now()
        )
        ON CONFLICT (name) DO UPDATE SET
            subject = EXCLUDED.subject,
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            available_variables = EXCLUDED.available_variables,
            updated_at = now();
    """)


def downgrade():
    op.execute("""
        DELETE FROM email_templates
        WHERE name = 'billing_cycle_change_confirmation';
    """)

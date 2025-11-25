"""add complete email templates with all variables from database

Revision ID: 025_add_complete_email_templates
Revises: 20251123_122400
Create Date: 2025-11-25 19:00:00

All hardcoded values replaced with database variables for full configurability.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '025_add_complete_email_templates'
down_revision = '20251123_122400'
branch_labels = None
depends_on = None


def upgrade():
    # Update subscription_confirmation template (NO hardcoded values)
    op.execute("""
        UPDATE email_templates
        SET
            subject = 'Welcome to {{plan_name}}!',
            html_body = '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Welcome to {{plan_name}}!</h2>
<p>Hi {{user_name}},</p>
<p>Thank you for subscribing to {{app_name}}! Your {{plan_name}} subscription is now active.</p>

<h3>Subscription Details</h3>
<p><strong>Plan:</strong> {{plan_name}}<br>
<strong>Billing:</strong> {{billing_cycle}}<br>
<strong>Amount:</strong> {{currency_display}}/{{billing_period}}<br>
<strong>Next billing date:</strong> {{next_billing_date}}</p>

<h3>Your Plan Includes</h3>
<p>• {{tier_feature_1}}<br>
• {{tier_feature_2}}<br>
• {{tier_feature_3}}</p>

<p><a href="{{dashboard_url}}" style="background-color: {{button_color}}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Dashboard</a></p>

<p>Need help? Reply to this email or visit our <a href="{{support_url}}" style="color: {{link_color}};">support center</a>.</p>

<p>Best regards,<br>{{company_signature}}</p>
</body>
</html>',
            text_body = 'Hi {{user_name}},

Thank you for subscribing to {{app_name}}! Your {{plan_name}} subscription is now active.

Subscription Details:
- Plan: {{plan_name}}
- Billing: {{billing_cycle}}
- Amount: {{currency_display}}/{{billing_period}}
- Next billing date: {{next_billing_date}}

Your Plan Includes:
- {{tier_feature_1}}
- {{tier_feature_2}}
- {{tier_feature_3}}

Go to Dashboard: {{dashboard_url}}

Need help? Reply to this email or visit our support center: {{support_url}}

Best regards,
{{company_signature}}',
            available_variables = '["user_name", "app_name", "plan_name", "billing_cycle", "currency_display", "billing_period", "next_billing_date", "tier_feature_1", "tier_feature_2", "tier_feature_3", "dashboard_url", "support_url", "button_color", "link_color", "company_signature"]'::jsonb
        WHERE name = 'subscription_confirmation';
    """)

    # Update cancellation_confirmation template (NO hardcoded values)
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

<p>Changed your mind? You can reactivate your subscription anytime:</p>
<p><a href="{{reactivate_url}}" style="background-color: {{button_color}}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reactivate Subscription</a></p>

<p>We are sorry to see you go. If you have feedback on how we can improve, please reply to this email.</p>

<p>Best regards,<br>{{company_signature}}</p>
</body>
</html>',
            text_body = 'Hi {{user_name}},

Your {{plan_name}} subscription has been canceled.

Cancellation Details:
- Plan: {{plan_name}}
- Canceled on: {{cancellation_date}}
- Access until: {{access_end_date}}

You will continue to have access to your subscription benefits until {{access_end_date}}.

Changed your mind? You can reactivate your subscription anytime: {{reactivate_url}}

We are sorry to see you go. If you have feedback on how we can improve, please reply to this email.

Best regards,
{{company_signature}}',
            available_variables = '["user_name", "plan_name", "cancellation_date", "access_end_date", "reactivate_url", "button_color", "company_signature"]'::jsonb
        WHERE name = 'cancellation_confirmation';
    """)

    # Update invoice_email template (NO hardcoded values)
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
<strong>Amount:</strong> {{currency_display}}<br>
<strong>Billing Period:</strong> {{period_start}} - {{period_end}}</p>

<p><a href="{{invoice_url}}" style="background-color: {{button_color}}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Invoice</a></p>

<p>Your subscription is active and you have full access to all features.</p>

<p>Questions about your invoice? Reply to this email or visit our <a href="{{support_url}}" style="color: {{link_color}};">support center</a>.</p>

<p>Best regards,<br>{{company_signature}}</p>
</body>
</html>',
            text_body = 'Hi {{user_name}},

We have successfully processed your payment for {{plan_name}}.

Invoice Details:
- Invoice #: {{invoice_number}}
- Date: {{invoice_date}}
- Amount: {{currency_display}}
- Billing Period: {{period_start}} - {{period_end}}

View Invoice: {{invoice_url}}

Your subscription is active and you have full access to all features.

Questions about your invoice? Reply to this email or visit our support center: {{support_url}}

Best regards,
{{company_signature}}',
            available_variables = '["user_name", "plan_name", "invoice_number", "invoice_date", "currency_display", "period_start", "period_end", "invoice_url", "support_url", "button_color", "link_color", "company_signature"]'::jsonb
        WHERE name = 'invoice_email';
    """)

    # Add welcome_email template (NO hardcoded values)
    op.execute("""
        INSERT INTO email_templates (name, display_name, description, subject, html_body, text_body, available_variables, category, is_active, is_system)
        VALUES (
            'welcome_email',
            'Welcome Email',
            'Welcome email sent to new users after account creation',
            'Welcome to {{app_name}}!',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Welcome to {{app_name}}, {{user_name}}!</h2>
<p>Your account has been created successfully.</p>

<p>You can now log in and start organizing your documents:</p>
<p><a href="{{login_url}}" style="background-color: {{button_color}}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Login</a></p>

<p>If you have any questions, feel free to contact our support team.</p>

<p>Best regards,<br>{{company_signature}}</p>
</body>
</html>',
            'Welcome to {{app_name}}, {{user_name}}!

Your account has been created successfully.

You can now log in and start organizing your documents:
{{login_url}}

If you have any questions, feel free to contact our support team.

Best regards,
{{company_signature}}',
            '["user_name", "app_name", "login_url", "button_color", "company_signature"]'::jsonb,
            'account',
            true,
            true
        )
        ON CONFLICT (name) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject,
            available_variables = EXCLUDED.available_variables;
    """)

    # Add password_reset template (NO hardcoded values)
    op.execute("""
        INSERT INTO email_templates (name, display_name, description, subject, html_body, text_body, available_variables, category, is_active, is_system)
        VALUES (
            'password_reset',
            'Password Reset',
            'Password reset email with secure reset link',
            'Reset Your {{app_name}} Password',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Reset Your Password</h2>
<p>Hi {{user_name}},</p>

<p>You requested to reset your {{app_name}} password.</p>

<p>Click the link below to reset your password:</p>
<p><a href="{{reset_url}}" style="background-color: {{button_color}}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>

<p>This link will expire in {{reset_link_expiration_hours}} hours.</p>

<p>If you did not request this, please ignore this email - your password will remain unchanged.</p>

<p>Best regards,<br>{{company_signature}}</p>
</body>
</html>',
            'Reset Your Password

Hi {{user_name}},

You requested to reset your {{app_name}} password.

Click the link below to reset your password:
{{reset_url}}

This link will expire in {{reset_link_expiration_hours}} hours.

If you did not request this, please ignore this email - your password will remain unchanged.

Best regards,
{{company_signature}}',
            '["user_name", "app_name", "reset_url", "reset_link_expiration_hours", "button_color", "company_signature"]'::jsonb,
            'account',
            true,
            true
        )
        ON CONFLICT (name) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject,
            available_variables = EXCLUDED.available_variables;
    """)

    # Add verification_code template (NO hardcoded values)
    op.execute("""
        INSERT INTO email_templates (name, display_name, description, subject, html_body, text_body, available_variables, category, is_active, is_system)
        VALUES (
            'verification_code',
            'Verification Code',
            '2FA verification code email',
            'Your {{app_name}} Verification Code',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Verification Code</h2>
<p>Hi {{user_name}},</p>

<p>Your verification code is:</p>
<h1 style="color: {{button_color}}; font-size: 36px; letter-spacing: 5px;">{{verification_code}}</h1>

<p>This code will expire in {{code_expiration_minutes}} minutes.</p>

<p>If you did not request this code, please secure your account immediately.</p>

<p>Best regards,<br>{{company_signature}}</p>
</body>
</html>',
            'Verification Code

Hi {{user_name}},

Your verification code is:

{{verification_code}}

This code will expire in {{code_expiration_minutes}} minutes.

If you did not request this code, please secure your account immediately.

Best regards,
{{company_signature}}',
            '["user_name", "app_name", "verification_code", "code_expiration_minutes", "button_color", "company_signature"]'::jsonb,
            'account',
            true,
            true
        )
        ON CONFLICT (name) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject,
            available_variables = EXCLUDED.available_variables;
    """)

    # Add drive_connected template (NO hardcoded values)
    op.execute("""
        INSERT INTO email_templates (name, display_name, description, subject, html_body, text_body, available_variables, category, is_active, is_system)
        VALUES (
            'drive_connected',
            'Drive Connected',
            'Email sent when user connects cloud storage',
            '{{storage_provider}} Connected Successfully',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>{{storage_provider}} Connected</h2>
<p>Hi {{user_name}},</p>

<p>Your {{storage_provider}} account has been successfully connected to {{app_name}}.</p>

<p>You can now upload documents directly from your {{storage_provider}}.</p>

<p><a href="{{dashboard_url}}" style="background-color: {{button_color}}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Dashboard</a></p>

<p>If you did not authorize this connection, please disconnect it immediately from your settings.</p>

<p>Best regards,<br>{{company_signature}}</p>
</body>
</html>',
            '{{storage_provider}} Connected

Hi {{user_name}},

Your {{storage_provider}} account has been successfully connected to {{app_name}}.

You can now upload documents directly from your {{storage_provider}}.

Go to your dashboard: {{dashboard_url}}

If you did not authorize this connection, please disconnect it immediately from your settings.

Best regards,
{{company_signature}}',
            '["user_name", "app_name", "storage_provider", "dashboard_url", "button_color", "company_signature"]'::jsonb,
            'account',
            true,
            true
        )
        ON CONFLICT (name) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject,
            available_variables = EXCLUDED.available_variables;
    """)

    # Add account_deleted template (NO hardcoded values)
    op.execute("""
        INSERT INTO email_templates (name, display_name, description, subject, html_body, text_body, available_variables, category, is_active, is_system)
        VALUES (
            'account_deleted',
            'Account Deletion Confirmation',
            'Email sent when user deletes their account',
            'Account Deletion Confirmed',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Account Deletion Confirmed</h2>
<p>Hi {{user_name}},</p>

<p>Your {{app_name}} account has been scheduled for deletion as of {{deletion_date}}.</p>

<p>Your data will be permanently deleted in {{data_retention_days}} days. During this period, you can still recover your account by logging in.</p>

<p>After {{data_retention_days}} days, all your data will be permanently removed and cannot be recovered.</p>

<p>We are sorry to see you go. If you have any feedback, please reply to this email.</p>

<p>Best regards,<br>{{company_signature}}</p>
</body>
</html>',
            'Account Deletion Confirmed

Hi {{user_name}},

Your {{app_name}} account has been scheduled for deletion as of {{deletion_date}}.

Your data will be permanently deleted in {{data_retention_days}} days. During this period, you can still recover your account by logging in.

After {{data_retention_days}} days, all your data will be permanently removed and cannot be recovered.

We are sorry to see you go. If you have any feedback, please reply to this email.

Best regards,
{{company_signature}}',
            '["user_name", "app_name", "deletion_date", "data_retention_days", "company_signature"]'::jsonb,
            'account',
            true,
            true
        )
        ON CONFLICT (name) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject,
            available_variables = EXCLUDED.available_variables;
    """)


def downgrade():
    # Remove added templates
    op.execute("DELETE FROM email_templates WHERE name IN ('welcome_email', 'password_reset', 'verification_code', 'drive_connected', 'account_deleted');")

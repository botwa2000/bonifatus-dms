"""add all email templates with simplified HTML

Revision ID: 025_add_all_email_templates
Revises: 024_make_stripe_price_id_nullable
Create Date: 2025-11-23 17:00:00

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '025_add_all_email_templates'
down_revision = '024_make_stripe_price_id_nullable'
branch_labels = None
depends_on = None


def upgrade():
    # Simplify existing subscription_confirmation template (remove complex HTML)
    op.execute("""
        UPDATE email_templates
        SET
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

<p><a href="{{dashboard_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Dashboard</a></p>

<p>Need help? Reply to this email or visit our <a href="{{support_url}}" style="color: #4CAF50;">support center</a>.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>'
        WHERE name = 'subscription_confirmation';
    """)

    # Simplify cancellation_confirmation
    op.execute("""
        UPDATE email_templates
        SET
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
<p><a href="{{reactivate_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reactivate Subscription</a></p>

<p>We are sorry to see you go. If you have feedback on how we can improve, please reply to this email.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            available_variables = '["user_name", "plan_name", "cancellation_date", "access_end_date", "reactivate_url"]'::jsonb
        WHERE name = 'cancellation_confirmation';
    """)

    # Simplify invoice_email
    op.execute("""
        UPDATE email_templates
        SET
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

<p><a href="{{invoice_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Invoice</a></p>

<p>Your subscription is active and you have full access to all features.</p>

<p>Questions about your invoice? Reply to this email or visit our <a href="{{support_url}}" style="color: #4CAF50;">support center</a>.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>'
        WHERE name = 'invoice_email';
    """)

    # Add welcome_email template
    op.execute("""
        INSERT INTO email_templates (id, name, language_code, subject, html_body, text_body, available_variables, description, is_active)
        VALUES (
            gen_random_uuid(),
            'welcome_email',
            'en',
            'Welcome to BoniDoc!',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Welcome to BoniDoc, {{user_name}}!</h2>
<p>Your account has been created successfully.</p>

<p>You can now log in and start organizing your documents:</p>
<p><a href="{{login_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Login</a></p>

<p>If you have any questions, feel free to contact our support team.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            'Welcome to BoniDoc, {{user_name}}!

Your account has been created successfully.

You can now log in and start organizing your documents:
{{login_url}}

If you have any questions, feel free to contact our support team.

Best regards,
The BoniDoc Team',
            '["user_name", "login_url"]'::jsonb,
            'Welcome email sent to new users after account creation',
            true
        )
        ON CONFLICT (name, language_code) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject;
    """)

    # Add password_reset template
    op.execute("""
        INSERT INTO email_templates (id, name, language_code, subject, html_body, text_body, available_variables, description, is_active)
        VALUES (
            gen_random_uuid(),
            'password_reset',
            'en',
            'Reset Your BoniDoc Password',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Reset Your Password</h2>
<p>Hi {{user_name}},</p>

<p>You requested to reset your BoniDoc password.</p>

<p>Click the link below to reset your password:</p>
<p><a href="{{reset_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>

<p>This link will expire in 24 hours.</p>

<p>If you did not request this, please ignore this email - your password will remain unchanged.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            'Reset Your Password

Hi {{user_name}},

You requested to reset your BoniDoc password.

Click the link below to reset your password:
{{reset_url}}

This link will expire in 24 hours.

If you did not request this, please ignore this email - your password will remain unchanged.

Best regards,
The BoniDoc Team',
            '["user_name", "reset_url"]'::jsonb,
            'Password reset email with secure reset link',
            true
        )
        ON CONFLICT (name, language_code) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject;
    """)

    # Add verification_code template
    op.execute("""
        INSERT INTO email_templates (id, name, language_code, subject, html_body, text_body, available_variables, description, is_active)
        VALUES (
            gen_random_uuid(),
            'verification_code',
            'en',
            'Your BoniDoc Verification Code',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Verification Code</h2>
<p>Hi {{user_name}},</p>

<p>Your verification code is:</p>
<h1 style="color: #4CAF50; font-size: 36px; letter-spacing: 5px;">{{verification_code}}</h1>

<p>This code will expire in {{code_expiration_minutes}} minutes.</p>

<p>If you did not request this code, please secure your account immediately.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            'Verification Code

Hi {{user_name}},

Your verification code is:

{{verification_code}}

This code will expire in {{code_expiration_minutes}} minutes.

If you did not request this code, please secure your account immediately.

Best regards,
The BoniDoc Team',
            '["user_name", "verification_code", "code_expiration_minutes"]'::jsonb,
            '2FA verification code email',
            true
        )
        ON CONFLICT (name, language_code) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject;
    """)

    # Add drive_connected template
    op.execute("""
        INSERT INTO email_templates (id, name, language_code, subject, html_body, text_body, available_variables, description, is_active)
        VALUES (
            gen_random_uuid(),
            'drive_connected',
            'en',
            'Google Drive Connected Successfully',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Google Drive Connected</h2>
<p>Hi {{user_name}},</p>

<p>Your Google Drive account has been successfully connected to BoniDoc.</p>

<p>You can now upload documents directly from your Google Drive.</p>

<p><a href="{{dashboard_url}}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Dashboard</a></p>

<p>If you did not authorize this connection, please disconnect it immediately from your settings.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            'Google Drive Connected

Hi {{user_name}},

Your Google Drive account has been successfully connected to BoniDoc.

You can now upload documents directly from your Google Drive.

Go to your dashboard: {{dashboard_url}}

If you did not authorize this connection, please disconnect it immediately from your settings.

Best regards,
The BoniDoc Team',
            '["user_name", "dashboard_url"]'::jsonb,
            'Email sent when user connects Google Drive',
            true
        )
        ON CONFLICT (name, language_code) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject;
    """)

    # Add account_deleted template
    op.execute("""
        INSERT INTO email_templates (id, name, language_code, subject, html_body, text_body, available_variables, description, is_active)
        VALUES (
            gen_random_uuid(),
            'account_deleted',
            'en',
            'Account Deletion Confirmed',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
<h2>Account Deletion Confirmed</h2>
<p>Hi {{user_name}},</p>

<p>Your BoniDoc account has been scheduled for deletion as of {{deletion_date}}.</p>

<p>Your data will be permanently deleted in {{data_retention_days}} days. During this period, you can still recover your account by logging in.</p>

<p>After {{data_retention_days}} days, all your data will be permanently removed and cannot be recovered.</p>

<p>We are sorry to see you go. If you have any feedback, please reply to this email.</p>

<p>Best regards,<br>The BoniDoc Team</p>
</body>
</html>',
            'Account Deletion Confirmed

Hi {{user_name}},

Your BoniDoc account has been scheduled for deletion as of {{deletion_date}}.

Your data will be permanently deleted in {{data_retention_days}} days. During this period, you can still recover your account by logging in.

After {{data_retention_days}} days, all your data will be permanently removed and cannot be recovered.

We are sorry to see you go. If you have any feedback, please reply to this email.

Best regards,
The BoniDoc Team',
            '["user_name", "deletion_date", "data_retention_days"]'::jsonb,
            'Email sent when user deletes their account',
            true
        )
        ON CONFLICT (name, language_code) DO UPDATE
        SET
            html_body = EXCLUDED.html_body,
            text_body = EXCLUDED.text_body,
            subject = EXCLUDED.subject;
    """)


def downgrade():
    # Remove added templates
    op.execute("DELETE FROM email_templates WHERE name IN ('welcome_email', 'password_reset', 'verification_code', 'drive_connected', 'account_deleted');")

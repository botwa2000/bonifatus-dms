"""Add missing email templates for complete admin control

Revision ID: 044_add_missing_email_templates
Revises: 298165871595
Create Date: 2025-01-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '044_add_missing_email_templates'
down_revision = '298165871595'
branch_labels = None
depends_on = None


def upgrade():
    """Add 6 missing email templates to enable full DB-driven email system"""

    # Get database connection
    conn = op.get_bind()

    # Template 1: user_created_notification (Marketing welcome email)
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'user_created_notification',
            'User Created Notification',
            'Marketing welcome email sent to new users highlighting key features',
            'Welcome to {{app_name}} - Your Account is Ready!',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, {{button_color}} 0%, #d35400 100%); padding: 30px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Welcome to {{app_name}}!</h1>
    </div>

    <div style="padding: 30px; background-color: #f9f9f9;">
        <p style="font-size: 16px;">Hello {{user_name}},</p>

        <p>Thank you for creating your account! We''re excited to have you on board.</p>

        <h2 style="color: {{button_color}}; font-size: 20px;">Here''s what you can do with {{app_name}}:</h2>

        <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <ul style="list-style: none; padding: 0;">
                <li style="padding: 10px 0; border-bottom: 1px solid #eee;">✓ {{feature_1}}</li>
                <li style="padding: 10px 0; border-bottom: 1px solid #eee;">✓ {{feature_2}}</li>
                <li style="padding: 10px 0; border-bottom: 1px solid #eee;">✓ {{feature_3}}</li>
                <li style="padding: 10px 0;">✓ {{feature_4}}</li>
            </ul>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{dashboard_url}}" style="background-color: {{button_color}}; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block;">
                Get Started
            </a>
        </div>

        <p>If you have any questions, feel free to reach out to our support team.</p>

        <p>{{company_signature}}</p>
    </div>

    <div style="padding: 20px; text-align: center; font-size: 12px; color: #666;">
        <p>You''re receiving this email because you created an account on {{app_name}}.</p>
        <p>If you''d prefer not to receive marketing emails, you can <a href="{{dashboard_url}}/settings">update your preferences</a>.</p>
    </div>
</body>
</html>',
            NULL,
            '["user_name", "app_name", "dashboard_url", "feature_1", "feature_2", "feature_3", "feature_4", "button_color", "company_signature"]',
            'marketing',
            true,
            true,
            'BoniDoc',
            'info@bonidoc.com'
        )
    """))

    # Template 2: admin_new_user_notification (Admin alert)
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'admin_new_user_notification',
            'Admin New User Notification',
            'Internal notification sent to admins when new user registers',
            'New User Registration: {{new_user_name}}',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2196F3;">New User Registration</h2>

    <p>Hello {{admin_name}},</p>

    <p>A new user has registered on {{app_name}}.</p>

    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3 style="margin-top: 0;">User Details:</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px; font-weight: bold; width: 150px;">Name:</td>
                <td style="padding: 8px;">{{new_user_name}}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Email:</td>
                <td style="padding: 8px;">{{new_user_email}}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">User ID:</td>
                <td style="padding: 8px;">{{new_user_id}}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Tier:</td>
                <td style="padding: 8px;">{{tier_name}}</td>
            </tr>
            <tr>
                <td style="padding: 8px; font-weight: bold;">Registration Date:</td>
                <td style="padding: 8px;">{{registration_date}}</td>
            </tr>
        </table>
    </div>

    <p style="text-align: center; margin: 30px 0;">
        <a href="{{admin_dashboard_url}}" style="background-color: #2196F3; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
            View in Admin Dashboard
        </a>
    </p>

    <p style="font-size: 12px; color: #666;">
        This is an automated notification from {{app_name}} admin system.
    </p>
</body>
</html>',
            NULL,
            '["admin_name", "new_user_name", "new_user_email", "new_user_id", "tier_name", "registration_date", "admin_dashboard_url", "app_name"]',
            'system',
            true,
            true,
            NULL,
            NULL
        )
    """))

    # Template 3: delegate_invitation_registered
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'delegate_invitation_registered',
            'Delegate Invitation (Registered User)',
            'Invitation for registered users to accept delegate access to another user''s documents',
            'Delegate Access Invitation from {{owner_name}}',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
    <div style="background-color: {{button_color}}; padding: 30px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">You''ve Been Granted Access</h1>
    </div>

    <div style="padding: 30px;">
        <p style="font-size: 16px;">Hello {{delegate_name}},</p>

        <p><strong>{{owner_name}}</strong> ({{owner_email}}) has invited you to access their documents on {{app_name}}.</p>

        <div style="background-color: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {{button_color}}; margin-top: 0;">Access Level: {{role}}</h3>

            <p><strong>You will be able to:</strong></p>
            <ul>
                <li>{{permission_1}}</li>
                <li>{{permission_2}}</li>
                <li>{{permission_3}}</li>
            </ul>

            <p><strong>Restrictions:</strong></p>
            <ul>
                <li>{{restriction_1}}</li>
                <li>{{restriction_2}}</li>
            </ul>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{accept_url}}" style="background-color: {{button_color}}; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block;">
                Accept Invitation
            </a>
        </div>

        <p style="font-size: 14px; color: #666;">This invitation will expire in 7 days. If you don''t want to accept this invitation, you can simply ignore this email.</p>

        <p>{{company_signature}}</p>
    </div>
</body>
</html>',
            NULL,
            '["delegate_name", "owner_name", "owner_email", "role", "accept_url", "app_name", "permission_1", "permission_2", "permission_3", "restriction_1", "restriction_2", "button_color", "company_signature"]',
            'account',
            true,
            true,
            NULL,
            NULL
        )
    """))

    # Template 4: delegate_invitation_unregistered
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'delegate_invitation_unregistered',
            'Delegate Invitation (Unregistered User)',
            'Invitation for unregistered users requiring account creation before accepting delegate access',
            '{{owner_name}} invited you to collaborate on {{app_name}}',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
    <div style="background-color: {{button_color}}; padding: 30px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">You''ve Been Invited!</h1>
    </div>

    <div style="padding: 30px;">
        <p style="font-size: 16px;">Hello,</p>

        <p><strong>{{owner_name}}</strong> ({{owner_email}}) has invited you to collaborate on {{app_name}}.</p>

        <p>To access their documents, you''ll need to create a free {{app_name}} account first.</p>

        <div style="background-color: #f9f9f9; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {{button_color}}; margin-top: 0;">What you''ll be able to do:</h3>
            <ul>
                <li>{{feature_1}}</li>
                <li>{{feature_2}}</li>
                <li>{{feature_3}}</li>
            </ul>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{signup_url}}" style="background-color: {{button_color}}; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block;">
                Create Account & Accept
            </a>
        </div>

        <p style="font-size: 14px; color: #666;">This invitation will expire in 7 days. Creating an account is free and only takes a minute.</p>

        <p>{{company_signature}}</p>
    </div>
</body>
</html>',
            NULL,
            '["delegate_email", "owner_name", "owner_email", "signup_url", "app_name", "feature_1", "feature_2", "feature_3", "button_color", "company_signature"]',
            'account',
            true,
            true,
            NULL,
            NULL
        )
    """))

    # Template 5: email_rejection_notification
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'email_rejection_notification',
            'Email Processing Rejection',
            'Notification sent when email-to-document processing fails',
            'Document Processing Failed - {{sender_email}}',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #f44336;">Document Processing Failed</h2>

    <p>Hello {{user_name}},</p>

    <p>We were unable to process an email you sent to {{app_name}}.</p>

    <div style="background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #f44336;">Email Details:</h3>
        <p><strong>From:</strong> {{sender_email}}</p>
        <p><strong>Subject:</strong> {{subject}}</p>
        <p><strong>Reason:</strong> {{rejection_reason}}</p>
    </div>

    <h3>What you can do:</h3>
    <ul>
        <li>Verify that the sender email ({{sender_email}}) is in your <a href="{{settings_url}}">allowed senders list</a></li>
        <li>Check that the email contained valid attachments (PDF, images, or documents)</li>
        <li>Make sure the email size didn''t exceed the maximum limit</li>
        <li>Review your subscription tier limits in your account settings</li>
    </ul>

    <p>If you need assistance, please <a href="{{support_url}}">contact our support team</a>.</p>

    <p>Best regards,<br>The {{app_name}} Team</p>
</body>
</html>',
            NULL,
            '["user_name", "sender_email", "subject", "rejection_reason", "settings_url", "support_url", "app_name"]',
            'system',
            true,
            true,
            NULL,
            NULL
        )
    """))

    # Template 6: email_completion_notification
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'email_completion_notification',
            'Email Processing Success',
            'Notification sent when email-to-document processing succeeds',
            'Documents Processed - {{documents_created}} file(s)',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #4CAF50;">✓ Documents Processed Successfully</h2>

    <p>Hello {{user_name}},</p>

    <p>We''ve successfully processed an email and created <strong>{{documents_created}} document(s)</strong> in your {{app_name}} account.</p>

    <div style="background-color: #e8f5e9; border-left: 4px solid #4CAF50; padding: 15px; margin: 20px 0;">
        <h3 style="margin-top: 0; color: #4CAF50;">Email Details:</h3>
        <p><strong>From:</strong> {{sender_email}}</p>
        <p><strong>Subject:</strong> {{subject}}</p>
        <p><strong>Documents Created:</strong> {{documents_created}}</p>
    </div>

    <p style="text-align: center; margin: 30px 0;">
        <a href="{{dashboard_url}}" style="background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; display: inline-block;">
            View Your Documents
        </a>
    </p>

    <p>The documents have been automatically categorized and are ready to search and organize.</p>

    <p>{{company_signature}}</p>
</body>
</html>',
            NULL,
            '["user_name", "sender_email", "subject", "documents_created", "dashboard_url", "app_name", "company_signature"]',
            'system',
            true,
            true,
            NULL,
            NULL
        )
    """))


def downgrade():
    """Remove the 6 added email templates"""
    conn = op.get_bind()

    # Delete the templates in reverse order
    template_names = [
        'email_completion_notification',
        'email_rejection_notification',
        'delegate_invitation_unregistered',
        'delegate_invitation_registered',
        'admin_new_user_notification',
        'user_created_notification'
    ]

    for template_name in template_names:
        conn.execute(text(f"DELETE FROM email_templates WHERE name = '{template_name}'"))

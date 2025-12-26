"""Add storage provider connected/disconnected email templates

Revision ID: 047_add_storage_provider_email_templates
Revises: 046_document_multi_provider
Create Date: 2025-12-26 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '047_add_storage_provider_email_templates'
down_revision = '046_document_multi_provider'
branch_labels = None
depends_on = None


def upgrade():
    """Add storage provider connection email templates"""

    conn = op.get_bind()

    # Template 1: provider_connected
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'provider_connected',
            'Storage Provider Connected',
            'Notification sent when a cloud storage provider is successfully connected',
            '{{provider_name}} Connected Successfully - {{app_name}}',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Cloud Storage Connected</h2>

        <p>Hello {{user_name}},</p>

        <p>Great news! Your <strong>{{provider_name}}</strong> account has been successfully connected to {{app_name}}.</p>

        <div style="background-color: #e8f5e9; border-left: 4px solid #4CAF50; padding: 15px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #4CAF50;">✓ What You Can Do Now:</h3>
            <ul style="margin: 10px 0;">
                <li>Upload and organize documents securely</li>
                <li>Access your files from anywhere</li>
                <li>Benefit from automatic categorization and OCR</li>
                <li>Search and manage documents across multiple languages</li>
            </ul>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{dashboard_url}}" style="background-color: {{button_color}}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Go to Dashboard
            </a>
        </div>

        <p style="color: #7f8c8d; font-size: 14px; margin-top: 40px;">
            {{company_signature}}
        </p>
    </div>
</body>
</html>',
            NULL,
            '["user_name", "provider_name", "app_name", "dashboard_url", "button_color", "company_signature"]',
            'system',
            true,
            true,
            'BoniDoc',
            'info@bonidoc.com'
        )
    """))

    # Template 2: provider_disconnected
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'provider_disconnected',
            'Storage Provider Disconnected',
            'Notification sent when a cloud storage provider is disconnected',
            '{{provider_name}} Disconnected - {{app_name}}',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Cloud Storage Disconnected</h2>

        <p>Hello {{user_name}},</p>

        <p>Your <strong>{{provider_name}}</strong> account has been disconnected from {{app_name}}.</p>

        <div style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #f57c00;">What This Means:</h3>
            <ul style="margin: 10px 0;">
                <li>We no longer have access to your {{provider_name}} storage</li>
                <li>Your existing documents in {{app_name}} remain accessible</li>
                <li>You can reconnect {{provider_name}} or connect a different provider anytime</li>
                <li>Any in-progress uploads to {{provider_name}} have been cancelled</li>
            </ul>
        </div>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{dashboard_url}}" style="background-color: {{button_color}}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Manage Storage Providers
            </a>
        </div>

        <p style="color: #7f8c8d; font-size: 14px; margin-top: 40px;">
            {{company_signature}}
        </p>
    </div>
</body>
</html>',
            NULL,
            '["user_name", "provider_name", "app_name", "dashboard_url", "button_color", "company_signature"]',
            'system',
            true,
            true,
            'BoniDoc',
            'info@bonidoc.com'
        )
    """))


def downgrade():
    """Remove storage provider email templates"""
    conn = op.get_bind()

    template_names = [
        'provider_disconnected',
        'provider_connected'
    ]

    for template_name in template_names:
        conn.execute(text(f"DELETE FROM email_templates WHERE name = '{template_name}'"))

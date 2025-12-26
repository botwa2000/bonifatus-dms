"""Add cloud storage provider migration email templates

Revision ID: 049_migration_email_templates
Revises: 048_add_migration_tasks
Create Date: 2025-12-26 21:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '049_migration_email_templates'
down_revision = '048_add_migration_tasks'
branch_labels = None
depends_on = None


def upgrade():
    """Add migration notification email templates"""

    conn = op.get_bind()

    # Template 1: migration_completed (all successful, folder deleted)
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'migration_completed',
            'Migration Completed Successfully',
            'Notification sent when all documents successfully migrated to new provider',
            'Migration Complete: {{from_provider_name}} → {{to_provider_name}}',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Migration Completed Successfully</h2>

        <p>Hello {{user_name}},</p>

        <p>Great news! Your documents have been successfully migrated from <strong>{{from_provider_name}}</strong> to <strong>{{to_provider_name}}</strong>.</p>

        <div style="background-color: #e8f5e9; border-left: 4px solid #4CAF50; padding: 15px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #4CAF50;">✓ Migration Summary:</h3>
            <ul style="margin: 10px 0;">
                <li><strong>{{successful_count}}</strong> documents migrated successfully</li>
                <li>Old {{from_provider_name}} app folder has been deleted</li>
                <li>All documents are now available in {{to_provider_name}}</li>
            </ul>
        </div>

        <p style="color: #7f8c8d; font-size: 14px;">
            Your files in the old {{from_provider_name}} app folder have been removed as part of the migration.
            All documents are now exclusively stored in {{to_provider_name}}.
        </p>

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
            '["user_name", "from_provider_name", "to_provider_name", "successful_count", "dashboard_url", "button_color", "company_signature"]',
            'system',
            true,
            true,
            NULL,
            NULL
        )
    """))

    # Template 2: migration_partial (some failed, folder NOT deleted)
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'migration_partial',
            'Migration Partially Completed',
            'Notification sent when some documents failed to migrate',
            'Migration Partially Complete: {{from_provider_name}} → {{to_provider_name}}',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Migration Partially Completed</h2>

        <p>Hello {{user_name}},</p>

        <p>Your document migration from <strong>{{from_provider_name}}</strong> to <strong>{{to_provider_name}}</strong> has completed with some issues.</p>

        <div style="background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #f57c00;">Migration Summary:</h3>
            <ul style="margin: 10px 0;">
                <li><strong>{{successful_count}}</strong> documents migrated successfully</li>
                <li><strong>{{failed_count}}</strong> documents failed to migrate</li>
                <li>{{from_provider_name}} remains connected for failed documents</li>
            </ul>
        </div>

        <p style="color: #d84315; font-weight: bold;">
            Important: Your {{from_provider_name}} app folder has NOT been deleted because some documents could not be migrated.
        </p>

        <p>Failed documents remain accessible in {{from_provider_name}}. You can:</p>
        <ul>
            <li>Try migrating the failed documents again</li>
            <li>Keep both providers connected</li>
            <li>Manually manage the remaining files</li>
        </ul>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{dashboard_url}}" style="background-color: {{button_color}}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Review Migration Results
            </a>
        </div>

        <p style="color: #7f8c8d; font-size: 14px; margin-top: 40px;">
            {{company_signature}}
        </p>
    </div>
</body>
</html>',
            NULL,
            '["user_name", "from_provider_name", "to_provider_name", "successful_count", "failed_count", "dashboard_url", "button_color", "company_signature"]',
            'system',
            true,
            true,
            NULL,
            NULL
        )
    """))

    # Template 3: migration_failed (all failed, folder NOT deleted)
    conn.execute(text("""
        INSERT INTO email_templates (
            name, display_name, description, subject, html_body, text_body,
            available_variables, category, is_active, is_system, send_from_name, send_from_email
        ) VALUES (
            'migration_failed',
            'Migration Failed',
            'Notification sent when migration completely failed',
            'Migration Failed: {{from_provider_name}} → {{to_provider_name}}',
            '<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Migration Failed</h2>

        <p>Hello {{user_name}},</p>

        <p>Unfortunately, the migration from <strong>{{from_provider_name}}</strong> to <strong>{{to_provider_name}}</strong> could not be completed.</p>

        <div style="background-color: #ffebee; border-left: 4px solid #f44336; padding: 15px; margin: 20px 0;">
            <h3 style="margin-top: 0; color: #c62828;">What Happened:</h3>
            <ul style="margin: 10px 0;">
                <li>No documents could be migrated to {{to_provider_name}}</li>
                <li>All {{total_count}} documents remain in {{from_provider_name}}</li>
                <li>Your {{from_provider_name}} folder has NOT been deleted</li>
            </ul>
        </div>

        <p><strong>Your data is safe.</strong> All documents remain accessible in your {{from_provider_name}} account.</p>

        <p>Error details: {{error_message}}</p>

        <p>You can:</p>
        <ul>
            <li>Check your {{to_provider_name}} connection and try again</li>
            <li>Contact support if the issue persists</li>
            <li>Continue using {{from_provider_name}} normally</li>
        </ul>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{{dashboard_url}}" style="background-color: {{button_color}}; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                Go to Settings
            </a>
        </div>

        <p style="color: #7f8c8d; font-size: 14px; margin-top: 40px;">
            {{company_signature}}
        </p>
    </div>
</body>
</html>',
            NULL,
            '["user_name", "from_provider_name", "to_provider_name", "total_count", "error_message", "dashboard_url", "button_color", "company_signature"]',
            'system',
            true,
            true,
            NULL,
            NULL
        )
    """))


def downgrade():
    """Remove migration email templates"""
    conn = op.get_bind()

    template_names = [
        'migration_failed',
        'migration_partial',
        'migration_completed'
    ]

    for template_name in template_names:
        conn.execute(text(f"DELETE FROM email_templates WHERE name = '{template_name}'"))

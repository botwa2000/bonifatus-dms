"""fix_email_processing_logs_cascade_constraint

Revision ID: 298165871595
Revises: 49595aa30f65
Create Date: 2025-12-21 14:18:42.419431

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '298165871595'
down_revision = '49595aa30f65'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix email_processing_logs FK constraint to CASCADE on user deletion"""
    op.drop_constraint('email_processing_logs_user_id_fkey', 'email_processing_logs', type_='foreignkey')
    op.create_foreign_key(
        'email_processing_logs_user_id_fkey',
        'email_processing_logs', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Revert to SET NULL (not recommended)"""
    op.drop_constraint('email_processing_logs_user_id_fkey', 'email_processing_logs', type_='foreignkey')
    op.create_foreign_key(
        'email_processing_logs_user_id_fkey',
        'email_processing_logs', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )
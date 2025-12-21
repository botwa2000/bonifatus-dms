"""fix_allowed_senders_cascade_constraint

Revision ID: 49595aa30f65
Revises: 043_add_user_delegates
Create Date: 2025-12-21 12:01:12.581398

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '49595aa30f65'
down_revision = '043_add_user_delegates'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix allowed_senders FK constraint to CASCADE on user deletion"""
    op.drop_constraint('allowed_senders_user_id_fkey', 'allowed_senders', type_='foreignkey')
    op.create_foreign_key(
        'allowed_senders_user_id_fkey',
        'allowed_senders', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Revert to SET NULL (not recommended)"""
    op.drop_constraint('allowed_senders_user_id_fkey', 'allowed_senders', type_='foreignkey')
    op.create_foreign_key(
        'allowed_senders_user_id_fkey',
        'allowed_senders', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL'
    )
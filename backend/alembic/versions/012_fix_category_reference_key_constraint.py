"""fix category reference_key constraint for per-user architecture

Revision ID: 012_fix_reference_key
Revises: 011_standardize_categories
Create Date: 2025-10-31 20:35:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '012_fix_reference_key'
down_revision = '011_standardize_categories'
branch_labels = None
depends_on = None


def upgrade():
    """
    Drop the unique constraint on reference_key alone and replace with
    a composite unique constraint on (reference_key, user_id) to support
    per-user category architecture.

    This allows:
    - One template category per reference_key (user_id IS NULL)
    - One category per reference_key per user (user_id = user's UUID)
    """

    print("\n=== Fixing Category Reference Key Constraint ===\n")

    # Drop the old unique index that only checks reference_key
    print("Dropping old unique index ix_categories_reference_key...")
    op.drop_index('ix_categories_reference_key', table_name='categories')

    # Create new composite unique index that includes user_id
    # Uses COALESCE to treat NULL as a specific value (all-zeros UUID)
    print("Creating new composite unique index...")
    op.execute("""
        CREATE UNIQUE INDEX ix_categories_reference_key_user
        ON categories (reference_key, COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid))
    """)

    print("\n✓ Migration 012 completed: Fixed reference_key constraint for per-user categories")
    print("  - Multiple users can now have categories with the same reference_key")
    print("  - Templates (user_id=NULL) remain unique per reference_key")


def downgrade():
    """
    Revert to single-column unique constraint (not recommended for per-user architecture)
    """

    print("\n=== Reverting Category Reference Key Constraint ===\n")

    # Drop composite unique index
    op.drop_index('ix_categories_reference_key_user', table_name='categories')

    # Recreate old single-column unique index
    op.create_index('ix_categories_reference_key', 'categories', ['reference_key'], unique=True)

    print("✓ Migration 012 downgrade completed")

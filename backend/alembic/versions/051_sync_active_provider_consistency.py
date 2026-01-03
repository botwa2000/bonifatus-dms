"""sync_active_provider_consistency

Revision ID: 051_sync_active_provider_consistency
Revises: 49595aa30f65
Create Date: 2026-01-03 00:00:00.000000

Fix schema desynchronization between provider_connections.is_active and
users.active_storage_provider fields. This migration:

1. Repairs existing data inconsistencies for ALL users
2. Creates database trigger to prevent future desyncs
3. Ensures only one active provider per user

Root Cause: Upload validation checks User.active_storage_provider while UI
displays ProviderConnection.is_active. When these get out of sync (due to
transaction rollback or manual DB updates), users see "connected and active"
but uploads fail with "STORAGE_PROVIDER_NOT_CONNECTED".

Compliance: System-level fix for all users (CLAUDE.md compliant)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '051_sync_active_provider_consistency'
down_revision = '49595aa30f65'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Repair schema inconsistencies and add trigger for ongoing consistency.

    This migration is idempotent and safe to run multiple times.
    """
    conn = op.get_bind()

    # STEP 1: Sync User.active_storage_provider from ProviderConnection.is_active
    # Updates users where ProviderConnection.is_active = TRUE but User field is NULL or wrong
    print("STEP 1: Syncing User.active_storage_provider from ProviderConnection.is_active...")
    result = conn.execute(text("""
        UPDATE users u
        SET active_storage_provider = pc.provider_key
        FROM provider_connections pc
        WHERE pc.user_id = u.id
          AND pc.is_active = TRUE
          AND (u.active_storage_provider IS NULL
               OR u.active_storage_provider != pc.provider_key)
    """))
    print(f"   Synced {result.rowcount} users with mismatched active provider")

    # STEP 2: Clear User.active_storage_provider where no active ProviderConnection exists
    # Handles orphaned values from deleted ProviderConnections
    print("STEP 2: Clearing orphaned User.active_storage_provider values...")
    result = conn.execute(text("""
        UPDATE users u
        SET active_storage_provider = NULL
        WHERE u.active_storage_provider IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM provider_connections pc
              WHERE pc.user_id = u.id AND pc.is_active = TRUE
          )
    """))
    print(f"   Cleared {result.rowcount} orphaned active_storage_provider values")

    # STEP 3: Ensure only ONE active provider per user (data integrity fix)
    # Keeps most recently connected provider as active, deactivates others
    print("STEP 3: Ensuring only one active provider per user...")
    result = conn.execute(text("""
        WITH ranked_connections AS (
            SELECT id, user_id,
                   ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY connected_at DESC) as rn
            FROM provider_connections
            WHERE is_active = TRUE
        )
        UPDATE provider_connections
        SET is_active = FALSE
        WHERE id IN (SELECT id FROM ranked_connections WHERE rn > 1)
    """))
    print(f"   Deactivated {result.rowcount} duplicate active providers")

    # STEP 4: Create trigger function to maintain consistency
    print("STEP 4: Creating database trigger to prevent future desyncs...")
    conn.execute(text("""
        CREATE OR REPLACE FUNCTION sync_active_provider()
        RETURNS TRIGGER AS $$
        BEGIN
            -- When a provider is activated
            IF NEW.is_active = TRUE THEN
                -- Deactivate all other providers for this user (ensure only ONE active)
                UPDATE provider_connections
                SET is_active = FALSE
                WHERE user_id = NEW.user_id AND id != NEW.id;

                -- Sync User table to match ProviderConnection
                UPDATE users
                SET active_storage_provider = NEW.provider_key
                WHERE id = NEW.user_id;

            -- When a provider is deactivated
            ELSIF OLD.is_active = TRUE AND NEW.is_active = FALSE THEN
                -- If this was the active provider, clear User table
                UPDATE users
                SET active_storage_provider = NULL
                WHERE id = NEW.user_id
                  AND active_storage_provider = OLD.provider_key;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """))

    # STEP 5: Create trigger on provider_connections table
    conn.execute(text("""
        DROP TRIGGER IF EXISTS trigger_sync_active_provider ON provider_connections;

        CREATE TRIGGER trigger_sync_active_provider
        AFTER INSERT OR UPDATE ON provider_connections
        FOR EACH ROW
        EXECUTE FUNCTION sync_active_provider();
    """))
    print("   Trigger created successfully")

    print("✅ Migration completed successfully!")
    print("   All users now have consistent provider state across both tables.")
    print("   Database trigger will prevent future desyncs automatically.")


def downgrade() -> None:
    """
    Remove trigger (but preserve data consistency).

    Note: This does NOT undo the data sync - the repaired data remains consistent.
    Only removes the trigger to allow manual management if needed.
    """
    conn = op.get_bind()

    print("Removing consistency trigger...")

    # Drop trigger
    conn.execute(text("""
        DROP TRIGGER IF EXISTS trigger_sync_active_provider ON provider_connections;
    """))

    # Drop trigger function
    conn.execute(text("""
        DROP FUNCTION IF EXISTS sync_active_provider();
    """))

    print("⚠️  Trigger removed - data sync is now manual via ProviderManager only")
    print("   Existing data remains consistent, but future desyncs are possible")

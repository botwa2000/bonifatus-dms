"""add currency exchange rates

Revision ID: 022
Revises: 021
Create Date: 2025-11-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '022'
down_revision = '021_payment_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Add exchange_rate column to currencies table"""
    print("\n=== Adding Currency Exchange Rate Support ===\n")

    # Add exchange_rate column
    # IMPORTANT: Exchange rate interpretation (to avoid confusion):
    #   - EUR is the BASE currency (exchange_rate = 1.00)
    #   - exchange_rate represents: "How many units of THIS currency per 1 EUR"
    #   - Example: USD with exchange_rate = 1.10 means 1 EUR = 1.10 USD
    #   - Formula: price_in_currency = price_in_eur × exchange_rate
    #
    # Admin will set these manually on the admin dashboard
    # Only currencies with exchange_rate set will be shown to users
    print("1. Adding exchange_rate column to currencies table...")
    print("   Exchange rate = units of currency per 1 EUR (EUR/XXX)")
    print("   Example: rate 1.10 for USD means 1 EUR = 1.10 USD")

    op.add_column('currencies', sa.Column('exchange_rate', sa.Numeric(10, 6), nullable=True))

    print("   ✓ Exchange rate column added")
    print("   → Admin can now set exchange rates on the admin dashboard")
    print("   → Only currencies with rates will be shown to users")
    print("\n=== Currency Exchange Rate Support Added ===\n")


def downgrade():
    """Remove exchange_rate column"""
    print("\n=== Removing Currency Exchange Rates ===\n")
    op.drop_column('currencies', 'exchange_rate')
    print("   ✓ Removed exchange_rate column")
    print("\n=== Currency Exchange Rates Removed ===\n")

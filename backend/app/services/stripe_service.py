# backend/app/services/stripe_service.py
"""
Stripe payment integration service for subscription management
"""

import logging
import stripe
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.database.models import User, Subscription, Payment, Invoice, TierPlan, Currency

logger = logging.getLogger(__name__)


class StripeService:
    """Stripe payment service for subscription billing"""

    def __init__(self):
        self.api_key = settings.stripe.stripe_secret_key
        self.publishable_key = settings.stripe.stripe_publishable_key
        self.webhook_secret = settings.stripe.stripe_webhook_secret

        if not self.api_key:
            logger.warning(
                "STRIPE_SECRET_KEY not set! Payment processing will be disabled. "
                "Set via system environment variable (not .env file)."
            )
        else:
            stripe.api_key = self.api_key
            logger.info("Stripe service initialized")

    def _check_api_key(self) -> bool:
        """Check if API key is configured"""
        if not self.api_key:
            logger.error("Cannot process payment: STRIPE_SECRET_KEY not configured")
            return False
        return True

    # ============================================================
    # Customer Management
    # ============================================================

    async def create_customer(
        self,
        user_id: str,
        email: str,
        name: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> Optional[stripe.Customer]:
        """
        Create a Stripe customer

        Args:
            user_id: Internal user ID
            email: Customer email
            name: Customer name
            metadata: Additional metadata

        Returns:
            Stripe Customer object or None if failed
        """
        if not self._check_api_key():
            return None

        try:
            customer_metadata = {
                "user_id": str(user_id),
                **(metadata or {})
            }

            # Search for existing customer by email to avoid orphaned duplicates
            existing_customers = stripe.Customer.search(
                query=f'email:"{email}"'
            )
            if existing_customers.data:
                customer = existing_customers.data[0]
                # Update metadata to link to new user_id
                stripe.Customer.modify(customer.id, metadata=customer_metadata, name=name)
                logger.info(f"Reused existing Stripe customer {customer.id} for user {user_id}")

                # Cancel any orphaned active subscriptions
                old_subs = stripe.Subscription.list(customer=customer.id, status='active')
                for old_sub in old_subs.data:
                    try:
                        stripe.Subscription.cancel(old_sub.id)
                        logger.info(f"Cancelled orphaned subscription {old_sub.id} for re-created user {email}")
                    except Exception as e:
                        logger.warning(f"Could not cancel orphaned subscription {old_sub.id}: {e}")

                return customer

            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata
            )

            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return customer

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create Stripe customer: {str(e)}")
            return None

    async def get_or_create_customer(
        self,
        db: AsyncSession,
        user: User
    ) -> Optional[stripe.Customer]:
        """
        Get existing Stripe customer or create new one

        Args:
            db: Database session
            user: User object

        Returns:
            Stripe Customer object or None if failed
        """
        if not self._check_api_key():
            return None

        # Check if user already has a Stripe customer ID
        if user.stripe_customer_id:
            try:
                customer = stripe.Customer.retrieve(user.stripe_customer_id)
                return customer
            except stripe.error.StripeError as e:
                logger.warning(f"Failed to retrieve customer {user.stripe_customer_id}: {str(e)}")
                # Will create new customer below

        # Create new customer
        customer = await self.create_customer(
            user_id=user.id,
            email=user.billing_email or user.email,
            name=user.billing_name or user.full_name
        )

        if customer:
            # Update user with Stripe customer ID
            user.stripe_customer_id = customer.id
            await db.commit()

        return customer

    async def update_customer(
        self,
        customer_id: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        address: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[stripe.Customer]:
        """
        Update Stripe customer details

        Args:
            customer_id: Stripe customer ID
            email: Customer email
            name: Customer name
            address: Customer address
            metadata: Additional metadata

        Returns:
            Updated Stripe Customer or None if failed
        """
        if not self._check_api_key():
            return None

        try:
            update_params = {}
            if email:
                update_params['email'] = email
            if name:
                update_params['name'] = name
            if address:
                update_params['address'] = address
            if metadata:
                update_params['metadata'] = metadata

            customer = stripe.Customer.modify(customer_id, **update_params)
            logger.info(f"Updated Stripe customer {customer_id}")
            return customer

        except stripe.error.StripeError as e:
            logger.error(f"Failed to update customer {customer_id}: {str(e)}")
            return None

    # ============================================================
    # Subscription Management
    # ============================================================

    async def get_or_create_price(
        self,
        db: AsyncSession,
        tier: TierPlan,
        billing_cycle: str,
        currency: Optional[str] = None
    ) -> Optional[str]:
        """
        Get existing or create new Stripe price from database tier configuration

        This implements dynamic pricing - prices are controlled by the database,
        not hard-coded in Stripe dashboard or environment variables.

        Args:
            db: Database session
            tier: TierPlan object from database
            billing_cycle: 'monthly' or 'yearly'
            currency: Currency code (e.g., 'USD', 'EUR'). If None, uses tier.currency

        Returns:
            Stripe price ID or None if failed
        """
        if not self._check_api_key():
            return None

        try:
            # Get base price from database tier
            price_cents_base = tier.price_monthly_cents if billing_cycle == 'monthly' else tier.price_yearly_cents

            if price_cents_base == 0:
                logger.error(f"Cannot create subscription for free tier {tier.name}")
                return None

            # Determine target currency - must be provided or error
            if not currency:
                logger.error("Currency parameter is required")
                return None

            target_currency = currency.upper()

            # Get currency details from database (including exchange rate)
            currency_obj = self.get_currency(db, target_currency)
            if not currency_obj:
                logger.error(f"Currency {target_currency} not found in database")
                return None

            if currency_obj.exchange_rate is None:
                logger.error(f"Currency {target_currency} has no exchange rate set")
                return None

            # Convert price using database exchange rate (base prices are in EUR)
            # Exchange rate format: 1 EUR = X target_currency (e.g., 1 EUR = 1.10 USD)
            price_cents = int(price_cents_base * currency_obj.exchange_rate)
            logger.info(f"Converted {price_cents_base} EUR cents to {price_cents} {target_currency} cents using rate {currency_obj.exchange_rate}")

            # Check if we already have a Stripe price ID cached for this tier/cycle
            # This reduces API calls by reusing existing price objects
            cache_key = f"stripe_price_{tier.id}_{billing_cycle}"

            # Try to get cached price ID from tier metadata (if you want to implement caching)
            # For now, we'll create a new price object each time or search existing ones

            # Search for existing price in Stripe with matching criteria
            # Note: We cannot filter by product name in Price.list(), only by price attributes
            interval = 'month' if billing_cycle == 'monthly' else 'year'
            existing_prices = stripe.Price.list(
                currency=target_currency.lower(),
                active=True,
                limit=100  # Get more results to filter manually
            )

            # Filter manually for matching price
            for price in existing_prices.data:
                if (price.unit_amount == price_cents and
                    price.recurring and
                    price.recurring.interval == interval and
                    price.currency == target_currency.lower()):
                    logger.info(f"Reusing existing Stripe price {price.id}")
                    return price.id

            # Create new price object dynamically from database values
            # interval already defined above

            price = stripe.Price.create(
                currency=target_currency.lower(),
                unit_amount=price_cents,
                recurring={'interval': interval},
                product_data={
                    'name': f'{tier.display_name} - {billing_cycle.capitalize()} ({target_currency})',
                    'metadata': {
                        'tier_id': str(tier.id),
                        'tier_name': tier.name,
                        'billing_cycle': billing_cycle,
                        'currency': target_currency,
                        'description': tier.description  # Store description in metadata instead
                    }
                },
                metadata={
                    'tier_id': str(tier.id),
                    'tier_name': tier.name,
                    'billing_cycle': billing_cycle,
                    'currency': target_currency,
                    'source': 'bonidoc_dynamic'
                }
            )

            logger.info(f"Created dynamic Stripe price {price.id} for {tier.name} {billing_cycle} (${price_cents/100})")
            return price.id

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create/get Stripe price: {str(e)}")
            return None

    def get_price_id(self, tier_name: str, billing_cycle: str) -> Optional[str]:
        """
        DEPRECATED: Get Stripe price ID from environment configuration

        Use get_or_create_price() instead for dynamic pricing from database.
        This method is kept for backwards compatibility only.

        Args:
            tier_name: Tier name (starter, pro)
            billing_cycle: monthly or yearly

        Returns:
            Stripe price ID or None
        """
        logger.warning("get_price_id() is deprecated. Use get_or_create_price() for dynamic pricing.")

        price_map = {
            ('starter', 'monthly'): settings.stripe.stripe_price_id_starter_monthly,
            ('starter', 'yearly'): settings.stripe.stripe_price_id_starter_yearly,
            ('pro', 'monthly'): settings.stripe.stripe_price_id_pro_monthly,
            ('pro', 'yearly'): settings.stripe.stripe_price_id_pro_yearly,
        }

        return price_map.get((tier_name.lower(), billing_cycle.lower()))

    async def create_subscription(
        self,
        db: AsyncSession,
        user: User,
        tier: TierPlan,
        billing_cycle: str,
        currency: str,
        payment_method_id: Optional[str] = None,
        trial_days: Optional[int] = None,
        discount_code: Optional[str] = None
    ) -> Optional[stripe.Subscription]:
        """
        Create a new Stripe subscription

        Args:
            db: Database session
            user: User object
            tier: TierPlan object
            billing_cycle: monthly or yearly
            currency: Currency code (e.g., 'USD', 'EUR')
            payment_method_id: Stripe payment method ID
            trial_days: Number of trial days
            discount_code: Discount/promo code

        Returns:
            Stripe Subscription object or None if failed
        """
        if not self._check_api_key():
            return None

        try:
            # Get or create customer
            customer = await self.get_or_create_customer(db, user)
            if not customer:
                logger.error(f"Failed to get/create customer for user {user.id}")
                return None

            # Get or create dynamic price from database with selected currency
            price_id = await self.get_or_create_price(db, tier, billing_cycle, currency)
            if not price_id:
                logger.error(f"Failed to get/create price for {tier.name} {billing_cycle} in {currency}")
                return None

            # Build subscription params
            subscription_params = {
                'customer': customer.id,
                'items': [{'price': price_id}],
                'metadata': {
                    'user_id': str(user.id),
                    'tier_id': str(tier.id),
                    'tier_name': tier.name,
                    'billing_cycle': billing_cycle
                }
            }

            # Add payment method if provided
            if payment_method_id:
                subscription_params['default_payment_method'] = payment_method_id

            # Add trial period if specified
            if trial_days and trial_days > 0:
                subscription_params['trial_period_days'] = trial_days

            # Add discount code if provided
            if discount_code:
                subscription_params['promotion_code'] = discount_code

            # Enable automatic tax calculation
            subscription_params['automatic_tax'] = {'enabled': True}

            # Create subscription
            subscription = stripe.Subscription.create(**subscription_params)

            logger.info(f"Created subscription {subscription.id} for user {user.id}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to create subscription: {str(e)}")
            return None

    async def update_subscription(
        self,
        subscription_id: str,
        new_price_id: Optional[str] = None,
        proration_behavior: str = 'create_prorations',
        cancel_at_period_end: Optional[bool] = None
    ) -> Optional[stripe.Subscription]:
        """
        Update an existing subscription

        Args:
            subscription_id: Stripe subscription ID
            new_price_id: New price ID for upgrade/downgrade
            proration_behavior: How to handle prorations (create_prorations, none, always_invoice)
            cancel_at_period_end: Whether to cancel at period end

        Returns:
            Updated Stripe Subscription or None if failed
        """
        if not self._check_api_key():
            return None

        try:
            update_params = {}

            if new_price_id:
                # Get current subscription
                subscription = stripe.Subscription.retrieve(subscription_id)

                # Update the subscription item
                update_params['items'] = [{
                    'id': subscription['items']['data'][0].id,
                    'price': new_price_id,
                }]
                update_params['proration_behavior'] = proration_behavior

            if cancel_at_period_end is not None:
                update_params['cancel_at_period_end'] = cancel_at_period_end

            subscription = stripe.Subscription.modify(subscription_id, **update_params)
            logger.info(f"Updated subscription {subscription_id}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to update subscription {subscription_id}: {str(e)}")
            return None

    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_immediately: bool = False
    ) -> Optional[stripe.Subscription]:
        """
        Cancel a subscription

        Args:
            subscription_id: Stripe subscription ID
            cancel_immediately: If True, cancel immediately; if False, cancel at period end

        Returns:
            Cancelled/updated Stripe Subscription or None if failed
        """
        if not self._check_api_key():
            return None

        try:
            if cancel_immediately:
                # Cancel immediately
                subscription = stripe.Subscription.delete(subscription_id)
                logger.info(f"Cancelled subscription {subscription_id} immediately")
            else:
                # Cancel at period end
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
                logger.info(f"Scheduled subscription {subscription_id} to cancel at period end")

            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Failed to cancel subscription {subscription_id}: {str(e)}")
            return None

    # ============================================================
    # Payment Method Management
    # ============================================================

    async def attach_payment_method(
        self,
        payment_method_id: str,
        customer_id: str,
        set_as_default: bool = True
    ) -> Optional[stripe.PaymentMethod]:
        """
        Attach payment method to customer

        Args:
            payment_method_id: Stripe payment method ID
            customer_id: Stripe customer ID
            set_as_default: Whether to set as default payment method

        Returns:
            Stripe PaymentMethod or None if failed
        """
        if not self._check_api_key():
            return None

        try:
            # Attach payment method to customer
            payment_method = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )

            # Set as default if requested
            if set_as_default:
                stripe.Customer.modify(
                    customer_id,
                    invoice_settings={'default_payment_method': payment_method_id}
                )

            logger.info(f"Attached payment method {payment_method_id} to customer {customer_id}")
            return payment_method

        except stripe.error.StripeError as e:
            logger.error(f"Failed to attach payment method: {str(e)}")
            return None

    async def list_payment_methods(
        self,
        customer_id: str,
        method_type: str = 'card'
    ) -> List[stripe.PaymentMethod]:
        """
        List customer's payment methods

        Args:
            customer_id: Stripe customer ID
            method_type: Payment method type (card, us_bank_account, sepa_debit)

        Returns:
            List of PaymentMethod objects
        """
        if not self._check_api_key():
            return []

        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type=method_type
            )
            return payment_methods.data

        except stripe.error.StripeError as e:
            logger.error(f"Failed to list payment methods: {str(e)}")
            return []

    # ============================================================
    # Invoice Management
    # ============================================================

    async def get_upcoming_invoice(
        self,
        customer_id: str,
        subscription_id: Optional[str] = None
    ) -> Optional[stripe.Invoice]:
        """
        Get upcoming invoice for preview

        Args:
            customer_id: Stripe customer ID
            subscription_id: Stripe subscription ID

        Returns:
            Stripe Invoice or None if failed
        """
        if not self._check_api_key():
            return None

        try:
            params = {'customer': customer_id}
            if subscription_id:
                params['subscription'] = subscription_id

            invoice = stripe.Invoice.upcoming(**params)
            return invoice

        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve upcoming invoice: {str(e)}")
            return None

    # ============================================================
    # Webhook Processing
    # ============================================================

    def construct_webhook_event(
        self,
        payload: bytes,
        sig_header: str
    ) -> Optional[stripe.Event]:
        """
        Verify and construct webhook event from Stripe

        Args:
            payload: Request body bytes
            sig_header: Stripe-Signature header value

        Returns:
            Stripe Event object or None if verification failed
        """
        if not self.webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event

        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            return None

    # ============================================================
    # Currency Formatting (Database-driven)
    # ============================================================

    def get_currency(self, db, currency_code: str) -> Optional[Currency]:
        """
        Get currency information from database

        Args:
            db: Database session (sync or async)
            currency_code: Currency code (USD, EUR, GBP)

        Returns:
            Currency object or None if not found
        """
        try:
            result = db.query(Currency).filter(Currency.code == currency_code.upper()).first()
            return result
        except Exception as e:
            logger.error(f"Failed to fetch currency {currency_code}: {str(e)}")
            return None

    async def get_default_currency(self, db: AsyncSession) -> Optional[Currency]:
        """
        Get default currency from database

        Args:
            db: Database session

        Returns:
            Currency object or None if not found
        """
        try:
            result = await db.execute(
                select(Currency).where(Currency.is_default == True).limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to fetch default currency: {str(e)}")
            return None

    async def format_amount(
        self,
        db: AsyncSession,
        amount_cents: int,
        currency_code: str
    ) -> str:
        """
        Format amount in cents to human-readable string using database currency info

        Args:
            db: Database session
            amount_cents: Amount in cents
            currency_code: Currency code

        Returns:
            Formatted amount string (e.g., "$9.99")
        """
        currency = await self.get_currency(db, currency_code)
        if not currency:
            # Fallback to basic formatting
            amount = amount_cents / 100
            return f"{currency_code} {amount:.2f}"

        # Convert cents to major unit
        amount = amount_cents / (10 ** currency.decimal_places)

        # Format with currency symbol
        return f"{currency.symbol}{amount:.{currency.decimal_places}f}"


# Singleton instance
stripe_service = StripeService()

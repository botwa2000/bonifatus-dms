# backend/app/api/billing_payments.py
"""
Billing API - Payment Method Management Endpoints
Handles payment method attachment and listing
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import stripe as stripe_lib

from app.schemas.billing_schemas import (
    PaymentMethodAttachRequest,
    PaymentMethodResponse,
    CardDetails
)
from app.database.connection import get_db
from app.database.models import User
from app.middleware.auth_middleware import get_current_active_user
from app.services.stripe_service import stripe_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/payment-methods",
    response_model=PaymentMethodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach Payment Method"
)
async def attach_payment_method(
    payment_method_request: PaymentMethodAttachRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> PaymentMethodResponse:
    """Attach a payment method to customer account"""
    try:
        customer = await stripe_service.get_or_create_customer(session, current_user)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize customer"
            )

        payment_method = await stripe_service.attach_payment_method(
            payment_method_request.payment_method_id,
            customer.id,
            set_as_default=payment_method_request.set_as_default
        )

        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to attach payment method"
            )

        logger.info(f"Attached payment method {payment_method.id} for user {current_user.email}")

        card_details = None
        if payment_method.type == 'card' and payment_method.card:
            card_details = CardDetails(
                brand=payment_method.card.brand,
                last4=payment_method.card.last4,
                exp_month=payment_method.card.exp_month,
                exp_year=payment_method.card.exp_year,
                country=payment_method.card.country
            )

        return PaymentMethodResponse(
            id=payment_method.id,
            type=payment_method.type,
            card=card_details,
            is_default=payment_method_request.set_as_default,
            created_at=datetime.fromtimestamp(payment_method.created, tz=timezone.utc)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Attach payment method error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/payment-methods",
    response_model=List[PaymentMethodResponse],
    summary="List Payment Methods"
)
async def list_payment_methods(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> List[PaymentMethodResponse]:
    """Get all payment methods for current user"""
    try:
        if not current_user.stripe_customer_id:
            return []

        payment_methods = await stripe_service.list_payment_methods(
            current_user.stripe_customer_id,
            method_type='card'
        )

        customer = stripe_lib.Customer.retrieve(current_user.stripe_customer_id)
        default_payment_method_id = None
        if customer.invoice_settings and customer.invoice_settings.default_payment_method:
            default_payment_method_id = customer.invoice_settings.default_payment_method

        response = []
        for pm in payment_methods:
            card_details = None
            if pm.type == 'card' and pm.card:
                card_details = CardDetails(
                    brand=pm.card.brand,
                    last4=pm.card.last4,
                    exp_month=pm.card.exp_month,
                    exp_year=pm.card.exp_year,
                    country=pm.card.country
                )

            response.append(PaymentMethodResponse(
                id=pm.id,
                type=pm.type,
                card=card_details,
                is_default=(pm.id == default_payment_method_id),
                created_at=datetime.fromtimestamp(pm.created, tz=timezone.utc)
            ))

        return response

    except Exception as e:
        logger.error(f"List payment methods error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/payment-methods/{payment_method_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Payment Method"
)
async def remove_payment_method(
    payment_method_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Detach a payment method from customer"""
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No customer account found"
            )

        payment_method = stripe_lib.PaymentMethod.detach(payment_method_id)

        logger.info(f"Removed payment method {payment_method_id} for user {current_user.email}")

        return {"message": "Payment method removed successfully"}

    except stripe_lib.error.StripeError as e:
        logger.error(f"Remove payment method error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Remove payment method error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

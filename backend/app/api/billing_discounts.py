# backend/app/api/billing_discounts.py
"""
Billing API - Discount Code Management Endpoints
Handles discount code validation and administration
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.schemas.billing_schemas import (
    DiscountCodeValidateRequest,
    DiscountCodeValidateResponse,
    DiscountCodeCreateRequest,
    DiscountCodeResponse
)
from app.database.connection import get_db
from app.database.models import User, DiscountCode
from app.middleware.auth_middleware import get_current_active_user, get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/discount-codes/validate",
    response_model=DiscountCodeValidateResponse,
    summary="Validate Discount Code"
)
async def validate_discount_code(
    validate_request: DiscountCodeValidateRequest,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> DiscountCodeValidateResponse:
    """Check if discount code is valid and applicable"""
    try:
        discount_code = session.query(DiscountCode).filter(
            DiscountCode.code == validate_request.code.upper(),
            DiscountCode.is_active == True
        ).first()

        if not discount_code:
            return DiscountCodeValidateResponse(
                valid=False,
                discount_code=None,
                error_message="Discount code not found or inactive"
            )

        now = datetime.now(timezone.utc)

        if discount_code.valid_from and now < discount_code.valid_from:
            return DiscountCodeValidateResponse(
                valid=False,
                discount_code=None,
                error_message="Discount code is not yet valid"
            )

        if discount_code.valid_until and now > discount_code.valid_until:
            return DiscountCodeValidateResponse(
                valid=False,
                discount_code=None,
                error_message="Discount code has expired"
            )

        if discount_code.max_redemptions and discount_code.times_redeemed >= discount_code.max_redemptions:
            return DiscountCodeValidateResponse(
                valid=False,
                discount_code=None,
                error_message="Discount code has reached maximum redemptions"
            )

        if discount_code.applicable_tiers and validate_request.tier_id not in discount_code.applicable_tiers:
            return DiscountCodeValidateResponse(
                valid=False,
                discount_code=None,
                error_message="Discount code is not applicable to this tier"
            )

        return DiscountCodeValidateResponse(
            valid=True,
            discount_code=DiscountCodeResponse(
                id=str(discount_code.id),
                code=discount_code.code,
                discount_type=discount_code.discount_type,
                discount_value=discount_code.discount_value,
                currency=discount_code.currency,
                duration=discount_code.duration,
                duration_in_months=discount_code.duration_in_months,
                times_redeemed=discount_code.times_redeemed,
                max_redemptions=discount_code.max_redemptions,
                valid_from=discount_code.valid_from,
                valid_until=discount_code.valid_until,
                applicable_tiers=discount_code.applicable_tiers,
                is_active=discount_code.is_active,
                description=discount_code.description,
                created_at=discount_code.created_at
            ),
            error_message=None
        )

    except Exception as e:
        logger.error(f"Validate discount code error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/admin/discount-codes",
    response_model=DiscountCodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Discount Code (Admin)"
)
async def create_discount_code(
    code_request: DiscountCodeCreateRequest,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_db)
) -> DiscountCodeResponse:
    """Admin endpoint to create new discount code"""
    try:
        existing_code = session.query(DiscountCode).filter(
            DiscountCode.code == code_request.code.upper()
        ).first()

        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Discount code already exists"
            )

        discount_code = DiscountCode(
            code=code_request.code.upper(),
            discount_type=code_request.discount_type.value,
            discount_value=code_request.discount_value,
            currency=code_request.currency,
            duration=code_request.duration,
            duration_in_months=code_request.duration_in_months,
            max_redemptions=code_request.max_redemptions,
            valid_from=code_request.valid_from,
            valid_until=code_request.valid_until,
            applicable_tiers=code_request.applicable_tiers,
            description=code_request.description,
            is_active=True
        )

        session.add(discount_code)
        session.commit()
        session.refresh(discount_code)

        logger.info(f"Created discount code {discount_code.code} by admin {current_admin.email}")

        return DiscountCodeResponse(
            id=str(discount_code.id),
            code=discount_code.code,
            discount_type=discount_code.discount_type,
            discount_value=discount_code.discount_value,
            currency=discount_code.currency,
            duration=discount_code.duration,
            duration_in_months=discount_code.duration_in_months,
            times_redeemed=discount_code.times_redeemed,
            max_redemptions=discount_code.max_redemptions,
            valid_from=discount_code.valid_from,
            valid_until=discount_code.valid_until,
            applicable_tiers=discount_code.applicable_tiers,
            is_active=discount_code.is_active,
            description=discount_code.description,
            created_at=discount_code.created_at
        )

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Create discount code error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/admin/discount-codes",
    response_model=List[DiscountCodeResponse],
    summary="List All Discount Codes (Admin)"
)
async def list_discount_codes(
    active_only: bool = False,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_db)
) -> List[DiscountCodeResponse]:
    """Admin endpoint to list all discount codes"""
    try:
        query = session.query(DiscountCode)

        if active_only:
            query = query.filter(DiscountCode.is_active == True)

        codes = query.order_by(DiscountCode.created_at.desc()).all()

        return [
            DiscountCodeResponse(
                id=str(code.id),
                code=code.code,
                discount_type=code.discount_type,
                discount_value=code.discount_value,
                currency=code.currency,
                duration=code.duration,
                duration_in_months=code.duration_in_months,
                times_redeemed=code.times_redeemed,
                max_redemptions=code.max_redemptions,
                valid_from=code.valid_from,
                valid_until=code.valid_until,
                applicable_tiers=code.applicable_tiers,
                is_active=code.is_active,
                description=code.description,
                created_at=code.created_at
            )
            for code in codes
        ]

    except Exception as e:
        logger.error(f"List discount codes error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/admin/discount-codes/{code_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate Discount Code (Admin)"
)
async def deactivate_discount_code(
    code_id: str,
    current_admin: User = Depends(get_current_admin_user),
    session: Session = Depends(get_db)
):
    """Admin endpoint to deactivate a discount code"""
    try:
        discount_code = session.query(DiscountCode).filter(
            DiscountCode.id == code_id
        ).first()

        if not discount_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discount code not found"
            )

        discount_code.is_active = False
        session.commit()

        logger.info(f"Deactivated discount code {discount_code.code} by admin {current_admin.email}")

        return {"message": "Discount code deactivated successfully"}

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Deactivate discount code error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

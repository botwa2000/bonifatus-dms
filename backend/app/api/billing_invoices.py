# backend/app/api/billing_invoices.py
"""
Billing API - Invoice Management Endpoints
Handles invoice listing and retrieval
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.billing_schemas import (
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceLineItem
)
from app.database.connection import get_db
from app.database.models import User, Invoice
from app.middleware.auth_middleware import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/invoices",
    response_model=InvoiceListResponse,
    summary="List Invoices"
)
async def list_invoices(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> InvoiceListResponse:
    """Get invoice history for current user"""
    try:
        total_count = session.query(Invoice).filter(
            Invoice.user_id == current_user.id
        ).count()

        invoices = session.query(Invoice).filter(
            Invoice.user_id == current_user.id
        ).order_by(
            Invoice.created_at.desc()
        ).offset(offset).limit(limit).all()

        invoice_responses = []
        for inv in invoices:
            line_items = []
            if inv.line_items:
                for item in inv.line_items:
                    line_items.append(InvoiceLineItem(**item))

            invoice_responses.append(InvoiceResponse(
                id=inv.stripe_invoice_id,
                invoice_number=inv.invoice_number,
                status=inv.status,
                amount_due=inv.amount_due_cents,
                amount_paid=inv.amount_paid_cents,
                subtotal=inv.subtotal_cents,
                tax=inv.tax_cents,
                discount=inv.discount_cents,
                currency=inv.currency,
                period_start=inv.period_start,
                period_end=inv.period_end,
                due_date=inv.due_date,
                paid_at=inv.paid_at,
                pdf_url=inv.pdf_url,
                hosted_url=inv.hosted_invoice_url,
                line_items=line_items,
                created_at=inv.created_at
            ))

        return InvoiceListResponse(
            invoices=invoice_responses,
            has_more=(offset + len(invoices)) < total_count,
            total_count=total_count
        )

    except Exception as e:
        logger.error(f"List invoices error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/invoices/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get Invoice Details"
)
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db)
) -> InvoiceResponse:
    """Get detailed invoice information"""
    try:
        invoice = session.query(Invoice).filter(
            Invoice.stripe_invoice_id == invoice_id,
            Invoice.user_id == current_user.id
        ).first()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found"
            )

        line_items = []
        if invoice.line_items:
            for item in invoice.line_items:
                line_items.append(InvoiceLineItem(**item))

        return InvoiceResponse(
            id=invoice.stripe_invoice_id,
            invoice_number=invoice.invoice_number,
            status=invoice.status,
            amount_due=invoice.amount_due_cents,
            amount_paid=invoice.amount_paid_cents,
            subtotal=invoice.subtotal_cents,
            tax=invoice.tax_cents,
            discount=invoice.discount_cents,
            currency=invoice.currency,
            period_start=invoice.period_start,
            period_end=invoice.period_end,
            due_date=invoice.due_date,
            paid_at=invoice.paid_at,
            pdf_url=invoice.pdf_url,
            hosted_url=invoice.hosted_invoice_url,
            line_items=line_items,
            created_at=invoice.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get invoice error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

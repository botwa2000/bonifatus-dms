# backend/app/services/email_service.py
"""
Email service using Brevo (Sendinblue) API for transactional emails
"""

import logging
import httpx
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.email_template_service import email_template_service
from app.core.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class EmailService:
    """Brevo email service for transactional emails"""

    BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

    # Mandatory email types (cannot be opted out - GDPR/CAN-SPAM compliant)
    MANDATORY_EMAIL_TYPES = {
        'password_reset',      # Security-critical
        'verification_code',   # Security-critical
        'account_security',    # Security alerts
        'legal_updates',       # Terms of service, privacy policy changes
        'service_announcements' # Critical service updates
    }

    def __init__(self):
        self.api_key = settings.email.brevo_api_key
        self.from_name = settings.email.email_from_name
        self.timeout = 30

        if not self.api_key:
            logger.warning(
                "BREVO_API_KEY not set! Email sending will be disabled. "
                "Set via system environment variable (not .env file)."
            )
        else:
            logger.info("Email service initialized with Brevo API")

    def _check_api_key(self) -> bool:
        """Check if API key is configured"""
        if not self.api_key:
            logger.error("Cannot send email: BREVO_API_KEY not configured")
            return False
        return True

    async def send_email(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        html_content: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send a single email via Brevo API

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            html_content: HTML email body
            from_email: Sender email (defaults to no-reply@)
            from_name: Sender name (defaults to BoniDoc)
            reply_to: Reply-to email address

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self._check_api_key():
            return False

        try:
            # Default sender
            if not from_email:
                from_email = settings.email.email_from_noreply
            if not from_name:
                from_name = self.from_name

            # Build request payload
            payload = {
                "sender": {
                    "name": from_name,
                    "email": from_email
                },
                "to": [
                    {
                        "email": to_email,
                        "name": to_name or to_email
                    }
                ],
                "subject": subject,
                "htmlContent": html_content
            }

            # Add reply-to if specified
            if reply_to:
                payload["replyTo"] = {"email": reply_to}

            # Send request to Brevo API
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.BREVO_API_URL,
                    headers={
                        "api-key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=payload
                )

                if response.status_code == 201:
                    message_id = response.json().get("messageId")
                    logger.info(f"Email sent successfully to {to_email} (ID: {message_id})")
                    return True
                else:
                    logger.error(
                        f"Failed to send email to {to_email}: "
                        f"Status {response.status_code}, Response: {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Email sending error to {to_email}: {e}")
            return False

    async def send_templated_email(
        self,
        to_email: str,
        to_name: Optional[str],
        template_key: str,
        template_content: str,
        variables: Dict[str, str],
        from_email: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send email using a template with variable substitution

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            template_key: Template identifier (e.g., 'welcome_email')
            template_content: HTML template with {{variable}} placeholders
            variables: Dictionary of variable names to values
            from_email: Sender email (optional)
            reply_to: Reply-to email (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self._check_api_key():
            return False

        try:
            # Replace variables in template
            html_content = template_content
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"  # {{key}}
                html_content = html_content.replace(placeholder, str(value))

            # Extract subject from variables or template
            subject = variables.get("subject", "BoniDoc Notification")

            # Check if template has Subject: line
            if template_content.startswith("Subject:"):
                lines = template_content.split("\n", 1)
                subject_line = lines[0].replace("Subject:", "").strip()
                # Replace variables in subject
                for key, value in variables.items():
                    placeholder = f"{{{{{key}}}}}"
                    subject_line = subject_line.replace(placeholder, str(value))
                subject = subject_line
                html_content = lines[1] if len(lines) > 1 else ""

            return await self.send_email(
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                html_content=html_content,
                from_email=from_email,
                reply_to=reply_to
            )

        except Exception as e:
            logger.error(f"Templated email sending error to {to_email}: {e}")
            return False

    async def send_welcome_email(
        self,
        session: Session,
        to_email: str,
        user_name: str,
        dashboard_url: str
    ) -> bool:
        """
        Send welcome email to new user

        Args:
            session: Database session
            to_email: User email
            user_name: User name
            dashboard_url: Dashboard/homepage URL

        Returns:
            True if email sent successfully
        """
        # Load template from database
        template_variables = {
            'user_name': user_name,
            'app_name': 'BoniDoc',
            'login_url': dashboard_url,
            'button_color': '#e67e22',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='welcome_email',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=user_name
        )

        if not email_data:
            logger.error(f"Database template 'welcome_email' not found")
            raise Exception("Email template 'welcome_email' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_noreply),
            reply_to=settings.email.email_from_noreply
        )

    async def send_password_reset_email(
        self,
        session: Session,
        to_email: str,
        user_name: str,
        reset_token: str,
        reset_url: str
    ) -> bool:
        """
        Send password reset email

        Args:
            session: Database session
            to_email: User email
            user_name: User name
            reset_token: Password reset token
            reset_url: Password reset URL with token

        Returns:
            True if email sent successfully
        """
        # Load template from database
        template_variables = {
            'user_name': user_name,
            'app_name': 'BoniDoc',
            'reset_url': reset_url,
            'reset_link_expiration_hours': '1',
            'button_color': '#e67e22',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='password_reset',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=user_name
        )

        if not email_data:
            logger.error(f"Database template 'password_reset' not found")
            raise Exception("Email template 'password_reset' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_noreply),
            reply_to=settings.email.email_from_noreply
        )

    async def send_verification_code_email(
        self,
        session: Session,
        to_email: str,
        user_name: str,
        verification_code: str
    ) -> bool:
        """
        Send 2FA verification code email

        Args:
            session: Database session
            to_email: User email
            user_name: User name
            verification_code: 6-digit verification code

        Returns:
            True if email sent successfully
        """
        # Load template from database
        template_variables = {
            'user_name': user_name,
            'app_name': 'BoniDoc',
            'verification_code': verification_code,
            'code_expiration_minutes': '10',
            'button_color': '#e67e22',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='verification_code',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=user_name
        )

        if not email_data:
            logger.error(f"Database template 'verification_code' not found")
            raise Exception("Email template 'verification_code' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_noreply),
            reply_to=settings.email.email_from_noreply
        )

    async def send_user_created_notification(
        self,
        session: Session,
        to_email: str,
        user_name: str,
        dashboard_url: str,
        user_can_receive_marketing: bool = True
    ) -> bool:
        """
        Send notification when new user account is created

        Args:
            session: Database session
            to_email: User email
            user_name: User name
            dashboard_url: Dashboard/homepage URL
            user_can_receive_marketing: Check if user opted in for marketing emails

        Returns:
            True if email sent successfully
        """
        # Optional email - check user preferences
        if not user_can_receive_marketing:
            logger.info(f"Skipping user creation email to {to_email} - marketing emails disabled")
            return False

        # Load template from database
        template_variables = {
            'user_name': user_name,
            'app_name': 'BoniDoc',
            'dashboard_url': dashboard_url,
            'feature_1': 'Automatically categorize your documents with intelligent OCR',
            'feature_2': 'Store documents securely in your Google Drive',
            'feature_3': 'Search and organize documents across multiple languages',
            'feature_4': 'Access your documents from anywhere',
            'button_color': '#e67e22',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='user_created_notification',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=user_name
        )

        if not email_data:
            logger.error(f"Database template 'user_created_notification' not found")
            raise Exception("Email template 'user_created_notification' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_info),
            reply_to=settings.email.email_from_info
        )

    async def send_drive_connected_notification(
        self,
        session: Session,
        to_email: str,
        user_name: str,
        dashboard_url: str,
        user_can_receive_marketing: bool = True
    ) -> bool:
        """
        Send notification when Google Drive is successfully connected

        Args:
            session: Database session
            to_email: User email
            user_name: User name
            dashboard_url: Dashboard URL
            user_can_receive_marketing: Check if user opted in for marketing emails

        Returns:
            True if email sent successfully
        """
        # Optional email - check user preferences
        if not user_can_receive_marketing:
            logger.info(f"Skipping Drive connection email to {to_email} - marketing emails disabled")
            return False

        # Load template from database
        template_variables = {
            'user_name': user_name,
            'app_name': 'BoniDoc',
            'storage_provider': 'Google Drive',
            'dashboard_url': dashboard_url,
            'button_color': '#e67e22',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='drive_connected',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=user_name
        )

        if not email_data:
            logger.error(f"Database template 'drive_connected' not found")
            raise Exception("Email template 'drive_connected' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_info),
            reply_to=settings.email.email_from_info
        )

    async def send_storage_provider_connected_notification(
        self,
        session: Session,
        to_email: str,
        user_name: str,
        provider_name: str,
        dashboard_url: str,
        user_can_receive_marketing: bool = True
    ) -> bool:
        """
        Send notification when any storage provider is successfully connected

        Args:
            session: Database session
            to_email: User email
            user_name: User name
            provider_name: Display name of provider (e.g., 'OneDrive', 'Google Drive')
            dashboard_url: Dashboard URL
            user_can_receive_marketing: Check if user opted in for marketing emails

        Returns:
            True if email sent successfully
        """
        # Optional email - check user preferences
        if not user_can_receive_marketing:
            logger.info(f"Skipping {provider_name} connection email to {to_email} - marketing emails disabled")
            return False

        # Load template from database
        template_variables = {
            'user_name': user_name,
            'provider_name': provider_name,
            'app_name': 'BoniDoc',
            'dashboard_url': dashboard_url,
            'button_color': '#3498db',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='provider_connected',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=user_name
        )

        if not email_data:
            logger.error(f"Database template 'provider_connected' not found")
            raise Exception("Email template 'provider_connected' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_info),
            reply_to=settings.email.email_from_info
        )

    async def send_storage_provider_disconnected_notification(
        self,
        session: Session,
        to_email: str,
        user_name: str,
        provider_name: str,
        dashboard_url: str,
        user_can_receive_marketing: bool = True
    ) -> bool:
        """
        Send notification when a storage provider is disconnected

        Args:
            session: Database session
            to_email: User email
            user_name: User name
            provider_name: Display name of provider (e.g., 'OneDrive', 'Google Drive')
            dashboard_url: Dashboard URL
            user_can_receive_marketing: Check if user opted in for marketing emails

        Returns:
            True if email sent successfully
        """
        # Optional email - check user preferences
        if not user_can_receive_marketing:
            logger.info(f"Skipping {provider_name} disconnection email to {to_email} - marketing emails disabled")
            return False

        # Load template from database
        template_variables = {
            'user_name': user_name,
            'provider_name': provider_name,
            'app_name': 'BoniDoc',
            'dashboard_url': dashboard_url,
            'button_color': '#3498db',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='provider_disconnected',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=user_name
        )

        if not email_data:
            logger.error(f"Database template 'provider_disconnected' not found")
            raise Exception("Email template 'provider_disconnected' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_info),
            reply_to=settings.email.email_from_info
        )

    async def send_migration_notification(
        self,
        session: Session,
        to_email: str,
        user_name: str,
        template_name: str,
        from_provider: str,
        to_provider: str,
        successful_count: int,
        failed_count: int,
        total_count: int,
        dashboard_url: str,
        error_message: str = '',
        user_can_receive_marketing: bool = True
    ) -> bool:
        """
        Send notification about cloud storage provider migration results

        Args:
            session: Database session
            to_email: User email
            user_name: User name
            template_name: Email template name ('migration_completed', 'migration_partial', 'migration_failed')
            from_provider: Source provider type (e.g., 'google_drive')
            to_provider: Target provider type (e.g., 'onedrive')
            successful_count: Number of successfully migrated documents
            failed_count: Number of failed documents
            total_count: Total number of documents
            dashboard_url: Dashboard URL
            error_message: Error message (if any)
            user_can_receive_marketing: Check if user opted in for marketing emails

        Returns:
            True if email sent successfully
        """
        # Optional email - check user preferences
        if not user_can_receive_marketing:
            logger.info(f"Skipping migration notification email to {to_email} - marketing emails disabled")
            return False

        # Format provider names for display using ProviderRegistry
        from_provider_name = ProviderRegistry.get_display_name(from_provider)
        to_provider_name = ProviderRegistry.get_display_name(to_provider)

        # Load template from database
        template_variables = {
            'user_name': user_name,
            'from_provider_name': from_provider_name,
            'to_provider_name': to_provider_name,
            'successful_count': str(successful_count),
            'failed_count': str(failed_count),
            'total_count': str(total_count),
            'dashboard_url': dashboard_url,
            'error_message': error_message,
            'button_color': '#3498db',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name=template_name,
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=user_name
        )

        if not email_data:
            logger.error(f"Database template '{template_name}' not found")
            raise Exception(f"Email template '{template_name}' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_info),
            reply_to=settings.email.email_from_info
        )

    async def send_account_deleted_notification(
        self,
        session: Session,
        to_email: str,
        user_name: str,
        deletion_date: str
    ) -> bool:
        """
        Send notification when user account is deleted/deactivated

        This is a mandatory notification (GDPR Article 17 - Right to Erasure)
        User must be informed about their data deletion.

        Args:
            session: Database session
            to_email: User email
            user_name: User name
            deletion_date: Date when account was deleted

        Returns:
            True if email sent successfully
        """
        # Try to load template from database first
        template_variables = {
            'user_name': user_name,
            'deletion_date': deletion_date,
            'support_email': settings.email.email_from_info
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='account_deleted',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=user_name
        )

        if not email_data:
            logger.error(f"Database template 'account_deleted' not found")
            raise Exception("Email template 'account_deleted' not found in database")

        logger.info(f"Using database template for account deletion email to {to_email}")
        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_info),
            reply_to=settings.email.email_from_info
        )

    async def send_subscription_confirmation(
        self,
        session: Session,
        user_email: str,
        user_name: str,
        plan_name: str,
        billing_cycle: str,
        amount: float,
        currency_symbol: str,
        billing_period: str,
        next_billing_date: str,
        tier_feature_1: str,
        tier_feature_2: str,
        tier_feature_3: str,
        dashboard_url: str,
        support_url: str
    ) -> bool:
        """
        Send subscription confirmation email using database template

        Args:
            session: Database session
            user_email: User email address
            user_name: User name
            plan_name: Subscription plan name
            billing_cycle: Billing cycle (monthly/yearly)
            amount: Subscription amount
            currency_symbol: Currency symbol ($, €, etc.)
            billing_period: Billing period text (month/year)
            next_billing_date: Next billing date
            tier_feature_1: First tier feature description
            tier_feature_2: Second tier feature description
            tier_feature_3: Third tier feature description
            dashboard_url: Dashboard URL
            support_url: Support URL

        Returns:
            True if email sent successfully
        """
        try:
            variables = {
                'user_name': user_name,
                'plan_name': plan_name,
                'billing_cycle': billing_cycle,
                'billing_period': billing_period,
                'amount': str(amount),
                'currency_symbol': currency_symbol,
                'next_billing_date': next_billing_date,
                'tier_feature_1': tier_feature_1,
                'tier_feature_2': tier_feature_2,
                'tier_feature_3': tier_feature_3,
                'dashboard_url': dashboard_url,
                'support_url': support_url
            }

            email_data = email_template_service.prepare_email(
                session=session,
                template_name='subscription_confirmation',
                variables=variables,
                recipient_email=user_email,
                recipient_name=user_name
            )

            if not email_data:
                logger.error("Subscription confirmation template not found")
                return False

            return await self.send_email(
                to_email=email_data['to_email'],
                to_name=email_data['to_name'],
                subject=email_data['subject'],
                html_content=email_data['html_body'],
                from_email=email_data.get('from_email'),
                from_name=email_data.get('from_name')
            )

        except Exception as e:
            logger.error(f"Failed to send subscription confirmation to {user_email}: {e}")
            return False

    async def send_invoice_email(
        self,
        session: Session,
        user_email: str,
        user_name: str,
        plan_name: str,
        invoice_number: str,
        invoice_date: str,
        period_start: str,
        period_end: str,
        amount: float,
        currency_symbol: str,
        invoice_pdf_url: str,
        support_url: str
    ) -> bool:
        """
        Send invoice email using database template

        Args:
            session: Database session
            user_email: User email address
            user_name: User name
            plan_name: Subscription plan name
            invoice_number: Invoice number
            invoice_date: Invoice date
            period_start: Billing period start date
            period_end: Billing period end date
            amount: Invoice amount
            currency_symbol: Currency symbol
            invoice_pdf_url: URL to invoice PDF
            support_url: Support URL

        Returns:
            True if email sent successfully
        """
        try:
            variables = {
                'user_name': user_name,
                'plan_name': plan_name,
                'invoice_number': invoice_number,
                'invoice_date': invoice_date,
                'period_start': period_start,
                'period_end': period_end,
                'amount': str(amount),
                'currency_symbol': currency_symbol,
                'invoice_pdf_url': invoice_pdf_url,
                'support_url': support_url
            }

            email_data = email_template_service.prepare_email(
                session=session,
                template_name='invoice_email',
                variables=variables,
                recipient_email=user_email,
                recipient_name=user_name
            )

            if not email_data:
                logger.error("Invoice email template not found")
                return False

            return await self.send_email(
                to_email=email_data['to_email'],
                to_name=email_data['to_name'],
                subject=email_data['subject'],
                html_content=email_data['html_body'],
                from_email=email_data.get('from_email'),
                from_name=email_data.get('from_name')
            )

        except Exception as e:
            logger.error(f"Failed to send invoice email to {user_email}: {e}")
            return False

    async def send_cancellation_email(
        self,
        session: Session,
        user_email: str,
        user_name: str,
        plan_name: str,
        access_end_date: str,
        free_tier_feature_1: str,
        free_tier_feature_2: str,
        free_tier_feature_3: str,
        reactivate_url: str,
        feedback_url: str,
        support_url: str
    ) -> bool:
        """
        Send cancellation confirmation email using database template

        Args:
            session: Database session
            user_email: User email address
            user_name: User name
            plan_name: Cancelled plan name
            access_end_date: Date when access ends
            free_tier_feature_1: First free tier feature
            free_tier_feature_2: Second free tier feature
            free_tier_feature_3: Third free tier feature
            reactivate_url: URL to reactivate subscription
            feedback_url: URL to feedback survey
            support_url: Support URL

        Returns:
            True if email sent successfully
        """
        try:
            variables = {
                'user_name': user_name,
                'plan_name': plan_name,
                'access_end_date': access_end_date,
                'free_tier_feature_1': free_tier_feature_1,
                'free_tier_feature_2': free_tier_feature_2,
                'free_tier_feature_3': free_tier_feature_3,
                'reactivate_url': reactivate_url,
                'feedback_url': feedback_url,
                'support_url': support_url
            }

            email_data = email_template_service.prepare_email(
                session=session,
                template_name='cancellation_confirmation',
                variables=variables,
                recipient_email=user_email,
                recipient_name=user_name
            )

            if not email_data:
                logger.error("Cancellation confirmation template not found")
                return False

            return await self.send_email(
                to_email=email_data['to_email'],
                to_name=email_data['to_name'],
                subject=email_data['subject'],
                html_content=email_data['html_body'],
                from_email=email_data.get('from_email'),
                from_name=email_data.get('from_name')
            )

        except Exception as e:
            logger.error(f"Failed to send cancellation email to {user_email}: {e}")
            return False


    async def send_billing_cycle_change_email(
        self,
        session: Session,
        user_email: str,
        user_name: str,
        plan_name: str,
        old_billing_cycle: str,
        new_billing_cycle: str,
        new_amount: float,
        currency: str,
        billing_period: str,
        change_effective_date: str,
        next_billing_date: str,
        dashboard_url: str
    ) -> bool:
        """
        Send billing cycle change confirmation email using database template

        Args:
            session: Database session
            user_email: User email address
            user_name: User name
            plan_name: Subscription plan name
            old_billing_cycle: Previous billing cycle (monthly/yearly)
            new_billing_cycle: New billing cycle (monthly/yearly)
            new_amount: New price amount (formatted, e.g., "29.99")
            currency: Currency code (e.g., "USD", "EUR", "GBP")
            billing_period: Billing period text (e.g., "month", "year")
            change_effective_date: Date when change takes effect
            next_billing_date: Next billing date
            dashboard_url: Dashboard URL

        Returns:
            True if email sent successfully
        """
        try:
            variables = {
                'user_name': user_name,
                'plan_name': plan_name,
                'old_billing_cycle': old_billing_cycle.capitalize(),
                'new_billing_cycle': new_billing_cycle.capitalize(),
                'new_amount': str(new_amount),
                'currency': currency,
                'billing_period': billing_period,
                'change_effective_date': change_effective_date,
                'next_billing_date': next_billing_date,
                'change_info': f'Your billing cycle has been changed from {old_billing_cycle} to {new_billing_cycle}. This change took effect on {change_effective_date}.',
                'dashboard_url': dashboard_url
            }

            email_data = email_template_service.prepare_email(
                session=session,
                template_name='billing_cycle_change_confirmation',
                variables=variables,
                recipient_email=user_email,
                recipient_name=user_name
            )

            if not email_data:
                logger.error("Billing cycle change confirmation template not found")
                return False

            return await self.send_email(
                to_email=email_data['to_email'],
                to_name=email_data['to_name'],
                subject=email_data['subject'],
                html_content=email_data['html_body'],
                from_email=email_data.get('from_email'),
                from_name=email_data.get('from_name')
            )

        except Exception as e:
            logger.error(f"Failed to send billing cycle change email to {user_email}: {e}")
            return False

    async def send_admin_new_user_notification(
        self,
        session: Session,
        admin_email: str,
        admin_name: str,
        new_user_name: str,
        new_user_id: int,
        new_user_email: str,
        tier_name: str,
        registration_date: str
    ) -> bool:
        """
        Send notification to admin when new user registers

        Args:
            session: Database session
            admin_email: Admin email address
            admin_name: Admin name
            new_user_name: New user's full name
            new_user_id: New user's ID
            new_user_email: New user's email
            tier_name: Selected subscription tier
            registration_date: Date of registration

        Returns:
            True if email sent successfully
        """
        # Load template from database
        template_variables = {
            'admin_name': admin_name,
            'new_user_name': new_user_name,
            'new_user_email': new_user_email,
            'new_user_id': str(new_user_id),
            'tier_name': tier_name,
            'registration_date': registration_date,
            'admin_dashboard_url': f"{settings.app.app_frontend_url}/admin",
            'app_name': 'BoniDoc'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='admin_new_user_notification',
            variables=template_variables,
            recipient_email=admin_email,
            recipient_name=admin_name
        )

        if not email_data:
            logger.error(f"Database template 'admin_new_user_notification' not found")
            raise Exception("Email template 'admin_new_user_notification' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_noreply),
            reply_to=settings.email.email_from_noreply
        )
    async def send_delegate_invitation_registered(
        self,
        session: Session,
        to_email: str,
        to_name: str,
        owner_name: str,
        owner_email: str,
        role: str,
        accept_url: str
    ) -> bool:
        """
        Send delegate invitation to registered user

        Args:
            session: Database session
            to_email: Delegate email
            to_name: Delegate name
            owner_name: Document owner name
            owner_email: Document owner email
            role: Access role (viewer/editor/owner)
            accept_url: URL to accept invitation

        Returns:
            True if email sent successfully
        """
        # Define permissions based on role
        permissions = {
            'viewer': ['View documents', 'Download documents', 'Access shared documents'],
            'editor': ['View documents', 'Download documents', 'Edit document metadata'],
            'owner': ['Full access to documents', 'Manage categories', 'Full control']
        }

        restrictions = {
            'viewer': ['Cannot upload new documents', 'Cannot modify existing documents'],
            'editor': ['Cannot upload new documents', 'Limited administrative access'],
            'owner': ['No restrictions', 'Full access granted']
        }

        role_perms = permissions.get(role, permissions['viewer'])
        role_restrictions = restrictions.get(role, restrictions['viewer'])

        template_variables = {
            'delegate_name': to_name,
            'owner_name': owner_name,
            'owner_email': owner_email,
            'role': role.capitalize(),
            'accept_url': accept_url,
            'app_name': 'BoniDoc',
            'permission_1': role_perms[0] if len(role_perms) > 0 else '',
            'permission_2': role_perms[1] if len(role_perms) > 1 else '',
            'permission_3': role_perms[2] if len(role_perms) > 2 else '',
            'restriction_1': role_restrictions[0],
            'restriction_2': role_restrictions[1],
            'button_color': '#e67e22',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='delegate_invitation_registered',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=to_name
        )

        if not email_data:
            logger.error(f"Database template 'delegate_invitation_registered' not found")
            raise Exception("Email template 'delegate_invitation_registered' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_noreply),
            reply_to=settings.email.email_from_noreply
        )

    async def send_delegate_invitation_unregistered(
        self,
        session: Session,
        to_email: str,
        owner_name: str,
        owner_email: str,
        signup_url: str
    ) -> bool:
        """
        Send delegate invitation to unregistered user (requires signup)

        Args:
            session: Database session
            to_email: Delegate email
            owner_name: Document owner name
            owner_email: Document owner email
            signup_url: URL to sign up and accept invitation

        Returns:
            True if email sent successfully
        """
        template_variables = {
            'delegate_email': to_email,
            'owner_name': owner_name,
            'owner_email': owner_email,
            'signup_url': signup_url,
            'app_name': 'BoniDoc',
            'feature_1': 'Access and view shared documents',
            'feature_2': 'Collaborate with document owners',
            'feature_3': 'Organize and manage shared content',
            'button_color': '#e67e22',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='delegate_invitation_unregistered',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=to_email
        )

        if not email_data:
            logger.error(f"Database template 'delegate_invitation_unregistered' not found")
            raise Exception("Email template 'delegate_invitation_unregistered' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_noreply),
            reply_to=settings.email.email_from_noreply
        )

    async def send_email_rejection_notification(
        self,
        session: Session,
        to_email: str,
        to_name: str,
        sender_email: str,
        subject: str,
        rejection_reason: str
    ) -> bool:
        """
        Send notification when email processing fails

        Args:
            session: Database session
            to_email: User email
            to_name: User name
            sender_email: Email sender address
            subject: Original email subject
            rejection_reason: Why processing failed

        Returns:
            True if email sent successfully
        """
        template_variables = {
            'user_name': to_name,
            'sender_email': sender_email,
            'subject': subject,
            'rejection_reason': rejection_reason,
            'settings_url': f"{settings.app.app_frontend_url}/settings",
            'support_url': f"{settings.app.app_frontend_url}/support",
            'app_name': 'BoniDoc'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='email_rejection_notification',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=to_name
        )

        if not email_data:
            logger.error(f"Database template 'email_rejection_notification' not found")
            raise Exception("Email template 'email_rejection_notification' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_noreply),
            reply_to=settings.email.email_from_noreply
        )

    async def send_email_completion_notification(
        self,
        session: Session,
        to_email: str,
        to_name: str,
        sender_email: str,
        subject: str,
        documents_created: int
    ) -> bool:
        """
        Send notification when email processing succeeds

        Args:
            session: Database session
            to_email: User email
            to_name: User name
            sender_email: Email sender address
            subject: Original email subject
            documents_created: Number of documents created

        Returns:
            True if email sent successfully
        """
        template_variables = {
            'user_name': to_name,
            'sender_email': sender_email,
            'subject': subject,
            'documents_created': str(documents_created),
            'dashboard_url': f"{settings.app.app_frontend_url}/documents",
            'app_name': 'BoniDoc',
            'company_signature': 'Best regards,<br>The BoniDoc Team'
        }

        email_data = email_template_service.prepare_email(
            session=session,
            template_name='email_completion_notification',
            variables=template_variables,
            recipient_email=to_email,
            recipient_name=to_name
        )

        if not email_data:
            logger.error(f"Database template 'email_completion_notification' not found")
            raise Exception("Email template 'email_completion_notification' not found in database")

        return await self.send_email(
            to_email=email_data['to_email'],
            to_name=email_data['to_name'],
            subject=email_data['subject'],
            html_content=email_data['html_body'],
            from_email=email_data.get('from_email', settings.email.email_from_noreply),
            reply_to=settings.email.email_from_noreply
        )


# Global email service instance
email_service = EmailService()

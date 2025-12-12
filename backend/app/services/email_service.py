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
        to_email: str,
        user_name: str,
        dashboard_url: str
    ) -> bool:
        """
        Send welcome email to new user

        Args:
            to_email: User email
            user_name: User name
            dashboard_url: Dashboard/homepage URL

        Returns:
            True if email sent successfully
        """
        subject = "Welcome to BoniDoc!"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Welcome to BoniDoc, {user_name}!</h2>
            <p>Your account has been created successfully.</p>
            <p>Get started with organizing your documents:</p>
            <p><a href="{dashboard_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Go to Dashboard</a></p>
            <p>If you have any questions, feel free to reply to this email.</p>
            <p>Best regards,<br>The BoniDoc Team</p>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            to_name=user_name,
            subject=subject,
            html_content=html_content,
            from_email=settings.email.email_from_noreply
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_token: str,
        reset_url: str
    ) -> bool:
        """
        Send password reset email

        Args:
            to_email: User email
            user_name: User name
            reset_token: Password reset token
            reset_url: Password reset URL with token

        Returns:
            True if email sent successfully
        """
        subject = "Reset Your BoniDoc Password"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Password Reset Request</h2>
            <p>Hello {user_name},</p>
            <p>We received a request to reset your BoniDoc password.</p>
            <p>Click the button below to reset your password:</p>
            <p><a href="{reset_url}" style="background-color: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request a password reset, please ignore this email.</p>
            <p>Best regards,<br>The BoniDoc Team</p>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            to_name=user_name,
            subject=subject,
            html_content=html_content,
            from_email=settings.email.email_from_noreply
        )

    async def send_verification_code_email(
        self,
        to_email: str,
        user_name: str,
        verification_code: str
    ) -> bool:
        """
        Send 2FA verification code email

        Args:
            to_email: User email
            user_name: User name
            verification_code: 6-digit verification code

        Returns:
            True if email sent successfully
        """
        subject = "Your BoniDoc Verification Code"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Verification Code</h2>
            <p>Hello {user_name},</p>
            <p>Your verification code is:</p>
            <h1 style="color: #4CAF50; font-size: 36px; letter-spacing: 5px;">{verification_code}</h1>
            <p>This code will expire in 10 minutes.</p>
            <p>If you didn't request this code, please secure your account immediately.</p>
            <p>Best regards,<br>The BoniDoc Team</p>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            to_name=user_name,
            subject=subject,
            html_content=html_content,
            from_email=settings.email.email_from_noreply
        )

    async def send_user_created_notification(
        self,
        to_email: str,
        user_name: str,
        dashboard_url: str,
        user_can_receive_marketing: bool = True
    ) -> bool:
        """
        Send notification when new user account is created

        Args:
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

        subject = "Welcome to BoniDoc - Your Account is Ready!"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Welcome to BoniDoc, {user_name}!</h2>
            <p>Your account has been successfully created. We're excited to have you on board!</p>

            <h3>What you can do with BoniDoc:</h3>
            <ul>
                <li>Automatically categorize your documents with intelligent OCR</li>
                <li>Store documents securely in your Google Drive</li>
                <li>Search and organize documents across multiple languages</li>
                <li>Access your documents from anywhere</li>
            </ul>

            <p>Get started now:</p>
            <p><a href="{dashboard_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Go to Dashboard</a></p>

            <p>If you have any questions or need help, feel free to reach out to our support team.</p>

            <p>Best regards,<br>The BoniDoc Team</p>

            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 12px; color: #666;">
                You received this email because you created a BoniDoc account.
                You can manage your email preferences in your account settings.
            </p>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            to_name=user_name,
            subject=subject,
            html_content=html_content,
            from_email=settings.email.email_from_info,
            reply_to=settings.email.email_from_info
        )

    async def send_drive_connected_notification(
        self,
        to_email: str,
        user_name: str,
        dashboard_url: str,
        user_can_receive_marketing: bool = True
    ) -> bool:
        """
        Send notification when Google Drive is successfully connected

        Args:
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

        subject = "Google Drive Successfully Connected!"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Great news, {user_name}!</h2>
            <p>Your Google Drive has been successfully connected to BoniDoc.</p>

            <h3>What happens next:</h3>
            <ul>
                <li>Your documents will be securely stored in your Google Drive</li>
                <li>BoniDoc will automatically categorize and organize them for you</li>
                <li>You maintain full control and ownership of your files</li>
                <li>Access your documents anytime from the dashboard</li>
            </ul>

            <p>Ready to upload your first document?</p>
            <p><a href="{dashboard_url}" style="background-color: #2196F3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Go to Dashboard</a></p>

            <p>If you have any questions about Google Drive integration, check out our help center or contact support.</p>

            <p>Best regards,<br>The BoniDoc Team</p>

            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 12px; color: #666;">
                You received this email because you connected Google Drive to your BoniDoc account.
                You can manage your email preferences in your account settings.
            </p>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            to_name=user_name,
            subject=subject,
            html_content=html_content,
            from_email=settings.email.email_from_info,
            reply_to=settings.email.email_from_info
        )

    async def send_account_deleted_notification(
        self,
        to_email: str,
        user_name: str,
        deletion_date: str
    ) -> bool:
        """
        Send notification when user account is deleted/deactivated

        This is a mandatory notification (GDPR Article 17 - Right to Erasure)
        User must be informed about their data deletion.

        Args:
            to_email: User email
            user_name: User name
            deletion_date: Date when account was deleted

        Returns:
            True if email sent successfully
        """
        subject = "Your BoniDoc Account Has Been Deleted"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Account Deletion Confirmation</h2>
            <p>Hello {user_name},</p>
            <p>This email confirms that your BoniDoc account has been successfully deleted on {deletion_date}.</p>

            <h3>What has been done:</h3>
            <ul>
                <li>Your account has been deactivated and scheduled for permanent deletion</li>
                <li>Your personal information will be removed from our systems</li>
                <li>Your documents remain in your Google Drive (we only removed our access)</li>
                <li>All active sessions have been terminated</li>
            </ul>

            <h3>Data Retention:</h3>
            <p>Per our data retention policy and legal requirements:</p>
            <ul>
                <li>Most personal data will be deleted within 30 days</li>
                <li>Some anonymized usage statistics may be retained for analytics</li>
                <li>Transaction records may be kept for accounting/legal purposes (7 years)</li>
            </ul>

            <p><strong>Important:</strong> Your documents stored in Google Drive are still yours and remain untouched.
            We have only removed BoniDoc's access to your Drive.</p>

            <p>If you deleted your account by mistake or would like to return, you're always welcome to create a new account.</p>

            <p>We're sorry to see you go. If you have any feedback about your experience, we'd love to hear it.</p>

            <p>Best regards,<br>The BoniDoc Team</p>

            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 12px; color: #666;">
                This is a mandatory notification per GDPR regulations. You received this email because your
                BoniDoc account was deleted. For questions, contact: {settings.email.email_from_info}
            </p>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=to_email,
            to_name=user_name,
            subject=subject,
            html_content=html_content,
            from_email=settings.email.email_from_info,
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
        subject = f"New User Registration: {new_user_name}"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>New User Registration</h2>
            <p>Hello {admin_name},</p>
            <p>A new user has completed registration on BoniDoc.</p>

            <h3>User Details:</h3>
            <table style="border-collapse: collapse; width: 100%; max-width: 500px;">
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px; font-weight: bold;">Name:</td>
                    <td style="padding: 8px;">{new_user_name}</td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px; font-weight: bold;">User ID:</td>
                    <td style="padding: 8px;">{new_user_id}</td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px; font-weight: bold;">Email:</td>
                    <td style="padding: 8px;">{new_user_email}</td>
                </tr>
                <tr style="border-bottom: 1px solid #ddd;">
                    <td style="padding: 8px; font-weight: bold;">Package:</td>
                    <td style="padding: 8px;"><strong>{tier_name}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold;">Registration Date:</td>
                    <td style="padding: 8px;">{registration_date}</td>
                </tr>
            </table>

            <p style="margin-top: 20px;">This is an automated notification from the BoniDoc system.</p>

            <p>Best regards,<br>BoniDoc Admin System</p>
        </body>
        </html>
        """

        return await self.send_email(
            to_email=admin_email,
            to_name=admin_name,
            subject=subject,
            html_content=html_content,
            from_email=settings.email.email_from_noreply
        )


# Global email service instance
email_service = EmailService()

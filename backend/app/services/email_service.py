# backend/app/services/email_service.py
"""
Email service using Brevo (Sendinblue) API for transactional emails
"""

import logging
import httpx
from typing import Optional, Dict
from app.core.config import settings

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
        login_url: str
    ) -> bool:
        """
        Send welcome email to new user

        Args:
            to_email: User email
            user_name: User name
            login_url: Login page URL

        Returns:
            True if email sent successfully
        """
        subject = "Welcome to BoniDoc!"
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>Welcome to BoniDoc, {user_name}!</h2>
            <p>Your account has been created successfully.</p>
            <p>You can now log in and start organizing your documents:</p>
            <p><a href="{login_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Login</a></p>
            <p>If you have any questions, feel free to contact our support team.</p>
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
        login_url: str,
        user_can_receive_marketing: bool = True
    ) -> bool:
        """
        Send notification when new user account is created

        Args:
            to_email: User email
            user_name: User name
            login_url: Login page URL
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
            <p><a href="{login_url}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Log In to BoniDoc</a></p>

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


# Global email service instance
email_service = EmailService()

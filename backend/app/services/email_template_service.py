"""
Email Template Service
Handles template rendering and email sending for transactional emails
"""

import re
import logging
from typing import Dict, Optional, Any
from sqlalchemy.orm import Session
from app.database.models import EmailTemplate

logger = logging.getLogger(__name__)


class EmailTemplateService:
    """Service for rendering and managing email templates"""

    def __init__(self):
        self.logger = logger

    def get_template(self, session: Session, template_name: str) -> Optional[EmailTemplate]:
        """
        Fetch email template by name

        Args:
            session: Database session
            template_name: Template identifier (e.g., 'subscription_confirmation')

        Returns:
            EmailTemplate object or None if not found
        """
        try:
            template = session.query(EmailTemplate).filter(
                EmailTemplate.name == template_name,
                EmailTemplate.is_active == True
            ).first()

            if not template:
                self.logger.warning(f"Email template '{template_name}' not found or inactive")
                return None

            return template

        except Exception as e:
            self.logger.error(f"Error fetching template '{template_name}': {str(e)}")
            return None

    def render_template(self, template_text: str, variables: Dict[str, Any]) -> str:
        """
        Replace template variables with actual values

        Variables use Mustache-style syntax: {{variable_name}}

        Args:
            template_text: Template string with {{variables}}
            variables: Dictionary of variable_name: value pairs

        Returns:
            Rendered template string
        """
        if not template_text:
            return ""

        rendered = template_text

        # Replace all {{variable}} instances
        for key, value in variables.items():
            # Convert value to string, handle None
            str_value = "" if value is None else str(value)

            # Replace {{key}} with value
            pattern = r'\{\{' + re.escape(key) + r'\}\}'
            rendered = re.sub(pattern, str_value, rendered)

        # Log any remaining unreplaced variables (for debugging)
        remaining_vars = re.findall(r'\{\{(\w+)\}\}', rendered)
        if remaining_vars:
            self.logger.warning(f"Unreplaced template variables: {remaining_vars}")

        return rendered

    def prepare_email(
        self,
        session: Session,
        template_name: str,
        variables: Dict[str, Any],
        recipient_email: str,
        recipient_name: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Prepare email content from template

        Args:
            session: Database session
            template_name: Template identifier
            variables: Variables to replace in template
            recipient_email: Recipient email address
            recipient_name: Recipient name (optional)

        Returns:
            Dictionary with email data or None if template not found:
            {
                'to_email': str,
                'to_name': str,
                'subject': str,
                'html_body': str,
                'text_body': str,
                'from_email': str (optional),
                'from_name': str (optional)
            }
        """
        # Fetch template
        template = self.get_template(session, template_name)
        if not template:
            return None

        # Ensure user_name is in variables
        if 'user_name' not in variables and recipient_name:
            variables['user_name'] = recipient_name

        # Render subject
        subject = self.render_template(template.subject, variables)

        # Render HTML body
        html_body = self.render_template(template.html_body, variables)

        # Render text body
        text_body = None
        if template.text_body:
            text_body = self.render_template(template.text_body, variables)

        # Prepare email data
        email_data = {
            'to_email': recipient_email,
            'to_name': recipient_name or recipient_email,
            'subject': subject,
            'html_body': html_body,
            'text_body': text_body
        }

        # Add custom from address if specified in template
        if template.send_from_email:
            email_data['from_email'] = template.send_from_email
        if template.send_from_name:
            email_data['from_name'] = template.send_from_name

        return email_data

    def validate_variables(self, template: EmailTemplate, provided_variables: Dict[str, Any]) -> Dict[str, list]:
        """
        Validate that all required template variables are provided

        Args:
            template: EmailTemplate object
            provided_variables: Dictionary of provided variables

        Returns:
            Dictionary with 'missing' and 'extra' variable lists
        """
        import json

        # Get expected variables from template
        try:
            expected_vars = set(json.loads(template.available_variables)) if template.available_variables else set()
        except:
            expected_vars = set()

        provided_vars = set(provided_variables.keys())

        missing = list(expected_vars - provided_vars)
        extra = list(provided_vars - expected_vars)

        return {
            'missing': missing,
            'extra': extra
        }


# Singleton instance
email_template_service = EmailTemplateService()

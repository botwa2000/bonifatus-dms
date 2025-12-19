"""
Email Processing Service
Handles incoming emails sent to @doc.bonidoc.com addresses
"""

import logging
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import os
import secrets
import json
import hashlib
import asyncio
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.database.auth_models import AllowedSender, EmailProcessingLog, EmailSettings
from app.database.models import User, Document, UserMonthlyUsage
from app.services.email_service import EmailService
from app.services.document_upload_service import document_upload_service
from app.services.malware_scanner_service import malware_scanner_service
from app.services.document_analysis_service import DocumentAnalysisService

logger = logging.getLogger(__name__)


class EmailProcessingService:
    """Service for processing incoming emails and converting them to documents"""

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
        self.document_analysis_service = DocumentAnalysisService()
        self.imap_host = settings.email_processing.imap_host
        self.imap_port = settings.email_processing.imap_port
        self.imap_user = settings.email_processing.imap_user
        self.imap_password = settings.email_processing.imap_password
        self.imap_use_ssl = settings.email_processing.imap_use_ssl
        self.doc_domain = settings.email_processing.doc_domain
        self.temp_storage_path = settings.email_processing.temp_storage_path

        # Ensure temp storage directory exists
        os.makedirs(self.temp_storage_path, exist_ok=True)

    def generate_user_email_address(self, user_id: str) -> str:
        """
        Generate a unique email address for a user
        Format: {random-token}@doc.bonidoc.com

        Args:
            user_id: User UUID

        Returns:
            Unique email address
        """
        # Generate cryptographically secure random token (8 characters)
        token = secrets.token_urlsafe(6)[:8].lower()
        return f"{token}@{self.doc_domain}"

    def auto_enable_email_processing_for_pro_user(self, user_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Automatically enable email processing for Pro users
        Creates processing email + single allowed sender pair (user's registered email)

        Args:
            user_id: User UUID

        Returns:
            Tuple of (success, email_address, error_message)
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, None, "User not found"

            # Check if already enabled
            if user.email_processing_enabled and user.email_processing_address:
                logger.info(f"Email processing already enabled for user {user_id}")
                return True, user.email_processing_address, None

            # Generate unique processing email address
            max_attempts = 10
            for _ in range(max_attempts):
                email_address = self.generate_user_email_address(user_id)

                # Check if email address already exists
                existing = self.db.query(User).filter(
                    User.email_processing_address == email_address
                ).first()

                if not existing:
                    break
            else:
                return False, None, "Failed to generate unique email address"

            # Update user
            user.email_processing_address = email_address
            user.email_processing_enabled = True

            # Create email settings (check if already exists)
            existing_settings = self.db.query(EmailSettings).filter(
                EmailSettings.user_id == user_id
            ).first()

            if not existing_settings:
                email_settings = EmailSettings(
                    user_id=user_id,
                    email_address=email_address,
                    is_enabled=True,
                    daily_email_limit=50,
                    max_attachment_size_mb=20,
                    auto_categorize=True,
                    send_confirmation_email=True
                )
                self.db.add(email_settings)
                logger.info(f"Created new email settings for user {user_id}")
            else:
                # Update existing settings
                existing_settings.email_address = email_address
                existing_settings.is_enabled = True
                logger.info(f"Updated existing email settings for user {user_id}")

            # Create single allowed sender pair (user's registered email → processing email)
            # Check if allowed sender already exists to avoid unique constraint violation
            existing_sender = self.db.query(AllowedSender).filter(
                AllowedSender.user_id == user_id,
                AllowedSender.sender_email == user.email
            ).first()

            if not existing_sender:
                allowed_sender = AllowedSender(
                    user_id=user_id,
                    sender_email=user.email,
                    sender_name=user.full_name,
                    is_verified=True,
                    is_active=True,
                    trust_level='high',
                    notes='Auto-created email pair for Pro user'
                )
                self.db.add(allowed_sender)
                logger.info(f"Created new allowed sender for user {user_id}: {user.email}")
            else:
                logger.info(f"Allowed sender already exists for user {user_id}: {user.email}")

            # DO NOT commit here - let the caller manage the transaction
            # The session is typically passed from update_user_tier which will commit
            # self.db.commit()  # Commented out to prevent double-commit issues

            logger.info(f"Email processing auto-enabled for Pro user {user_id}: {user.email} → {email_address}")
            return True, email_address, None

        except Exception as e:
            # DO NOT rollback here - let the caller handle transaction cleanup
            # Rolling back here would undo the tier update that the caller made
            # self.db.rollback()  # Commented out
            logger.error(f"Error auto-enabling email processing for user {user_id}: {str(e)}")
            return False, None, str(e)

    def enable_email_processing_for_user(self, user_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Enable email processing for a user (called automatically for Pro users)
        Creates processing email + single allowed sender pair

        Args:
            user_id: User UUID

        Returns:
            Tuple of (success, email_address, error_message)
        """
        # Delegate to auto_enable method (same implementation)
        return self.auto_enable_email_processing_for_pro_user(user_id)

    def connect_to_imap(self) -> Optional[imaplib.IMAP4_SSL]:
        """
        Connect to IMAP server

        Returns:
            IMAP connection or None if failed
        """
        try:
            if self.imap_use_ssl:
                imap = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
            else:
                imap = imaplib.IMAP4(self.imap_host, self.imap_port)

            imap.login(self.imap_user, self.imap_password)
            logger.info(f"Connected to IMAP server {self.imap_host}")
            return imap

        except Exception as e:
            logger.error(f"Failed to connect to IMAP server: {str(e)}")
            return None

    def is_doc_email(self, recipient: str) -> bool:
        """
        Check if email is sent to @doc.bonidoc.com domain

        Args:
            recipient: Email address

        Returns:
            True if recipient is @doc.bonidoc.com
        """
        if not recipient:
            return False

        domain = recipient.split('@')[-1].lower() if '@' in recipient else ''
        return domain == self.doc_domain

    def extract_email_address(self, email_str: str) -> str:
        """
        Extract email address from 'Name <email@domain.com>' format

        Args:
            email_str: Email string

        Returns:
            Email address only
        """
        name, addr = parseaddr(email_str)
        return addr.lower().strip()

    def decode_email_header(self, header: str) -> str:
        """
        Decode email header (handles MIME encoding)

        Args:
            header: Email header string

        Returns:
            Decoded string
        """
        if not header:
            return ""

        decoded_parts = decode_header(header)
        result = []

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or 'utf-8', errors='ignore'))
                except:
                    result.append(part.decode('utf-8', errors='ignore'))
            else:
                result.append(str(part))

        return ''.join(result)

    def find_user_by_email_address(self, recipient_email: str) -> Optional[User]:
        """
        Find user by their email processing address

        Args:
            recipient_email: Recipient email address

        Returns:
            User or None
        """
        return self.db.query(User).filter(
            User.email_processing_address == recipient_email,
            User.email_processing_enabled == True
        ).first()

    def is_sender_allowed(self, user_id: str, sender_email: str) -> Tuple[bool, Optional[AllowedSender]]:
        """
        Check if sender is in user's whitelist

        Args:
            user_id: User UUID
            sender_email: Sender email address

        Returns:
            Tuple of (is_allowed, allowed_sender_record)
        """
        allowed_sender = self.db.query(AllowedSender).filter(
            AllowedSender.user_id == user_id,
            AllowedSender.sender_email == sender_email,
            AllowedSender.is_active == True
        ).first()

        return (allowed_sender is not None, allowed_sender)

    def check_monthly_quota(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if user has quota remaining for email processing

        Args:
            user_id: User UUID

        Returns:
            Tuple of (has_quota, error_message)
        """
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False, "User not found"

            # Check if feature is enabled for user's tier
            if not user.tier.email_to_process_enabled:
                return False, f"Email processing not available on {user.tier.name} tier"

            # Get current month period
            now = datetime.utcnow()
            month_period = now.strftime("%Y-%m")

            # Get or create usage record
            usage = self.db.query(UserMonthlyUsage).filter(
                UserMonthlyUsage.user_id == user_id,
                UserMonthlyUsage.month_period == month_period
            ).first()

            if not usage:
                return True, ""  # No usage yet, quota available

            # Check quota limit
            max_emails = user.tier.max_email_documents_per_month
            if max_emails is None:
                return True, ""  # Unlimited

            if usage.email_documents_processed >= max_emails:
                return False, f"Monthly email processing quota exceeded ({max_emails} documents/month)"

            return True, ""

        except Exception as e:
            logger.error(f"Error checking quota for user {user_id}: {str(e)}")
            return False, str(e)

    def create_processing_log(
        self,
        user_id: str,
        sender_email: str,
        recipient_email: str,
        subject: Optional[str],
        message_id: Optional[str],
        uid: Optional[str],
        attachment_count: int,
        total_size_bytes: int,
        status: str,
        rejection_reason: Optional[str] = None
    ) -> EmailProcessingLog:
        """
        Create email processing log entry

        Args:
            All email processing details

        Returns:
            Created log entry
        """
        log = EmailProcessingLog(
            user_id=user_id,
            sender_email=sender_email,
            recipient_email=recipient_email,
            subject=subject,
            email_message_id=message_id,
            email_uid=uid,
            attachment_count=attachment_count,
            total_size_bytes=total_size_bytes,
            status=status,
            rejection_reason=rejection_reason,
            received_at=datetime.utcnow()
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        return log

    def extract_attachments(self, email_message) -> List[Dict[str, Any]]:
        """
        Extract attachments from email message

        Args:
            email_message: Parsed email message

        Returns:
            List of attachment info dictionaries
        """
        attachments = []

        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()
            if not filename:
                continue

            # Decode filename
            filename = self.decode_email_header(filename)

            # Get file content
            file_data = part.get_payload(decode=True)
            if not file_data:
                continue

            attachments.append({
                'filename': filename,
                'data': file_data,
                'size': len(file_data),
                'content_type': part.get_content_type()
            })

        return attachments

    def save_attachment_to_temp(self, attachment: Dict[str, Any]) -> Optional[str]:
        """
        Save attachment to temporary storage

        Args:
            attachment: Attachment dictionary

        Returns:
            Path to saved file or None if failed
        """
        try:
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{secrets.token_hex(4)}_{attachment['filename']}"
            filepath = os.path.join(self.temp_storage_path, safe_filename)

            # Save file
            with open(filepath, 'wb') as f:
                f.write(attachment['data'])

            logger.info(f"Saved attachment to temp: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Failed to save attachment: {str(e)}")
            return None

    def cleanup_temp_files(self, filepaths: List[str]):
        """
        Delete temporary files

        Args:
            filepaths: List of file paths to delete
        """
        for filepath in filepaths:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"Deleted temp file: {filepath}")
            except Exception as e:
                logger.error(f"Failed to delete temp file {filepath}: {str(e)}")

    def delete_email_from_inbox(self, imap, email_id: bytes):
        """
        Delete email from inbox

        Args:
            imap: IMAP connection
            email_id: Email ID to delete
        """
        try:
            # Mark for deletion
            imap.store(email_id, '+FLAGS', '\\Deleted')
            # Expunge to permanently delete
            imap.expunge()
            logger.info(f"Deleted email {email_id} from inbox")
        except Exception as e:
            logger.error(f"Failed to delete email {email_id}: {str(e)}")

    def increment_monthly_usage(self, user_id: str, document_count: int):
        """
        Increment user's monthly email processing usage

        Args:
            user_id: User UUID
            document_count: Number of documents processed
        """
        try:
            now = datetime.utcnow()
            month_period = now.strftime("%Y-%m")
            first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day_month = (first_day.replace(month=first_day.month % 12 + 1, day=1) if first_day.month < 12
                            else first_day.replace(year=first_day.year + 1, month=1, day=1))
            last_day = last_day_month.replace(day=1) - timedelta(days=1)

            # Get or create usage record
            usage = self.db.query(UserMonthlyUsage).filter(
                UserMonthlyUsage.user_id == user_id,
                UserMonthlyUsage.month_period == month_period
            ).first()

            if not usage:
                usage = UserMonthlyUsage(
                    user_id=user_id,
                    month_period=month_period,
                    period_start_date=first_day.date(),
                    period_end_date=last_day.date(),
                    email_documents_processed=document_count
                )
                self.db.add(usage)
            else:
                usage.email_documents_processed += document_count
                usage.last_updated_at = now

            self.db.commit()
            logger.info(f"Updated monthly usage for user {user_id}: +{document_count} email documents")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update monthly usage: {str(e)}")

    def update_allowed_sender_stats(self, allowed_sender: AllowedSender):
        """
        Update allowed sender statistics

        Args:
            allowed_sender: AllowedSender record
        """
        try:
            allowed_sender.use_count += 1
            allowed_sender.last_email_at = datetime.utcnow()
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update allowed sender stats: {str(e)}")

    async def process_attachments(
        self,
        temp_files: List[str],
        filenames: List[str],
        user: User,
        sender_email: str,
        subject: str,
        email_id: bytes
    ) -> Tuple[int, List[str], List[str], bool]:
        """
        Process email attachments: scan, analyze, and upload

        Args:
            temp_files: List of temporary file paths
            filenames: List of original filenames
            user: User object
            sender_email: Sender email address
            subject: Email subject
            email_id: Email ID

        Returns:
            Tuple of (documents_created, uploaded_document_ids, processing_errors, malware_detected)
        """
        # SECURITY GATE #8: Malware scanning (ClamAV)
        malware_detected = False
        malware_details = []

        for temp_file in temp_files:
            try:
                with open(temp_file, 'rb') as f:
                    scan_result = await malware_scanner_service.scan_file(
                        file_content=f,
                        filename=os.path.basename(temp_file),
                        mime_type=None
                    )

                    if not scan_result.is_safe:
                        malware_detected = True
                        malware_details.extend(scan_result.threats)
                        logger.error(f"Malware detected in {temp_file}: {scan_result.threats}")

                    # Log warnings even if file is safe
                    if scan_result.warnings:
                        logger.warning(f"Scan warnings for {temp_file}: {scan_result.warnings}")

            except Exception as e:
                logger.error(f"Error scanning file {temp_file}: {str(e)}")
                # Fail-safe: reject on scanning error
                malware_detected = True
                malware_details.append(f"Scan error: {str(e)}")

        if malware_detected:
            return 0, [], malware_details, True

        # Process documents (upload to Drive, AI categorization)
        documents_created = 0
        uploaded_document_ids = []
        processing_errors = []

        for idx, temp_file in enumerate(temp_files):
            try:
                # Read file content
                with open(temp_file, 'rb') as f:
                    file_content = f.read()

                filename = filenames[idx]

                # Detect MIME type
                import magic
                mime_type = magic.from_buffer(file_content, mime=True)

                logger.info(f"Processing attachment {idx + 1}/{len(temp_files)}: {filename} ({mime_type})")

                # Analyze document with AI
                analysis_result = await self.document_analysis_service.analyze_document(
                    file_content=file_content,
                    file_name=filename,
                    mime_type=mime_type,
                    db=self.db,
                    user_id=str(user.id)
                )

                logger.info(f"Document analyzed: language={analysis_result.get('detected_language')}, category={analysis_result.get('suggested_category_id')}")

                # Get user's language preference
                user_language = user.preferred_doc_languages[0] if user.preferred_doc_languages else analysis_result.get('detected_language', 'en')

                # Prepare category IDs
                suggested_category_id = analysis_result.get('suggested_category_id')
                if suggested_category_id:
                    category_ids = [suggested_category_id]
                else:
                    # Find "Other/Uncategorized" system category
                    from app.database.models import Category
                    uncategorized = self.db.query(Category).filter(
                        Category.is_system == True,
                        Category.reference_key == 'other'
                    ).first()
                    category_ids = [str(uncategorized.id)] if uncategorized else []

                if not category_ids:
                    raise ValueError("No category available for document")

                # Extract keywords
                keywords = [kw['word'] for kw in analysis_result.get('keywords', [])]

                # Generate document title from attachment filename (not email subject)
                # Remove file extension for cleaner title
                title = os.path.splitext(filename)[0]

                # Check for duplicates by file hash
                file_hash = hashlib.sha256(file_content).hexdigest()

                existing_doc = self.db.query(Document).filter(
                    Document.user_id == user.id,
                    Document.file_hash == file_hash,
                    Document.is_deleted == False
                ).first()

                if existing_doc:
                    logger.warning(f"[EMAIL DEBUG] Duplicate detected: {filename} already exists as document {existing_doc.id}")
                    processing_errors.append(f"{filename}: Duplicate - already uploaded")
                    continue  # Skip this attachment

                logger.info(f"[EMAIL DEBUG] No duplicate found for {filename}, proceeding with upload")

                # Prepare temp_data for upload service
                temp_data = {
                    'file_content': file_content,
                    'file_name': filename,
                    'mime_type': mime_type,
                    'analysis_result': analysis_result
                }

                # Upload document to Drive
                upload_result = await document_upload_service.confirm_upload(
                    temp_id=f"email_{email_id.decode()}_{idx}",
                    temp_data=temp_data,
                    title=title,
                    category_ids=category_ids,
                    confirmed_keywords=keywords,
                    description=f"Received via email from {sender_email}",
                    user_id=str(user.id),
                    user_email=user.email,
                    language_code=user_language,
                    session=self.db
                )

                if upload_result['success']:
                    documents_created += 1
                    uploaded_document_ids.append(upload_result['document_id'])
                    logger.info(f"Document uploaded successfully: {upload_result['document_id']} - {title}")
                else:
                    processing_errors.append(f"{filename}: Upload failed")
                    logger.error(f"Document upload failed for {filename}")

            except Exception as e:
                logger.error(f"Error processing attachment {filename}: {str(e)}", exc_info=True)
                processing_errors.append(f"{filename}: {str(e)}")

        return documents_created, uploaded_document_ids, processing_errors, False

    async def send_rejection_notification(
        self,
        user_email: str,
        sender_email: str,
        subject: str,
        rejection_reason: str
    ):
        """
        Send rejection notification to user

        Args:
            user_email: User's email address
            sender_email: Sender who was rejected
            subject: Original email subject
            rejection_reason: Why it was rejected
        """
        try:
            html_content = f"""
            <h2>Document Processing Failed</h2>
            <p>An email from <strong>{sender_email}</strong> was rejected and not processed.</p>
            <p><strong>Subject:</strong> {subject}</p>
            <p><strong>Reason:</strong> {rejection_reason}</p>
            <p>If you want to accept documents from this sender, please add them to your allowed senders list in your account settings.</p>
            """

            await self.email_service.send_email(
                to_email=user_email,
                to_name=None,
                subject=f"Document Processing Failed - {sender_email}",
                html_content=html_content
            )

        except Exception as e:
            logger.error(f"Failed to send rejection notification: {str(e)}")

    async def send_completion_notification(
        self,
        user_email: str,
        sender_email: str,
        subject: str,
        documents_created: int
    ):
        """
        Send completion notification to user

        Args:
            user_email: User's email address
            sender_email: Sender email
            subject: Original email subject
            documents_created: Number of documents created
        """
        try:
            html_content = f"""
            <h2>Documents Processed Successfully</h2>
            <p>Your email from <strong>{sender_email}</strong> has been processed.</p>
            <p><strong>Subject:</strong> {subject}</p>
            <p><strong>Documents Created:</strong> {documents_created}</p>
            <p>Your documents are now available in your dashboard.</p>
            """

            await self.email_service.send_email(
                to_email=user_email,
                to_name=None,
                subject=f"Documents Processed - {documents_created} file(s)",
                html_content=html_content
            )

        except Exception as e:
            logger.error(f"Failed to send completion notification: {str(e)}")

    async def poll_inbox(self) -> int:
        """
        Poll IMAP inbox for new emails sent to @doc.bonidoc.com

        Returns:
            Number of emails processed
        """
        imap = None
        processed_count = 0

        try:
            # Connect to IMAP
            logger.info(f"[EMAIL DEBUG] Connecting to IMAP server: {self.imap_host}:{self.imap_port}")
            imap = self.connect_to_imap()
            if not imap:
                logger.error("[EMAIL DEBUG] Failed to connect to IMAP")
                return 0

            logger.info("[EMAIL DEBUG] IMAP connection successful")

            # Select inbox
            logger.info("[EMAIL DEBUG] Selecting INBOX folder")
            status, data = imap.select('INBOX')
            logger.info(f"[EMAIL DEBUG] INBOX selected. Status: {status}, Messages: {data}")

            # Search for unread emails
            logger.info("[EMAIL DEBUG] Searching for UNSEEN emails")
            status, messages = imap.search(None, 'UNSEEN')
            if status != 'OK':
                logger.error(f"[EMAIL DEBUG] Failed to search for emails. Status: {status}")
                return 0

            email_ids = messages[0].split()
            logger.info(f"[EMAIL DEBUG] Found {len(email_ids)} unread emails")
            logger.info(f"[EMAIL DEBUG] Email IDs: {email_ids}")

            for email_id in email_ids:
                try:
                    logger.info(f"[EMAIL DEBUG] Processing email ID: {email_id}")

                    # Fetch email
                    status, msg_data = imap.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        logger.error(f"[EMAIL DEBUG] Failed to fetch email {email_id}. Status: {status}")
                        continue

                    # Parse email
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)

                    # Extract headers
                    recipient_raw = email_message.get('To', '')
                    sender_raw = email_message.get('From', '')
                    subject_raw = email_message.get('Subject', '')
                    message_id = email_message.get('Message-ID', '')

                    logger.info(f"[EMAIL DEBUG] From: {sender_raw} | To: {recipient_raw} | Subject: {subject_raw}")

                    # Decode
                    recipient_email = self.extract_email_address(recipient_raw)
                    sender_email = self.extract_email_address(sender_raw)
                    subject = self.decode_email_header(subject_raw)

                    logger.info(f"Processing email: {sender_email} -> {recipient_email}")

                    # CRITICAL FILTER: Only process @doc.bonidoc.com emails
                    logger.info(f"[EMAIL DEBUG] Checking if {recipient_email} is doc email")
                    if not self.is_doc_email(recipient_email):
                        logger.warning(f"[EMAIL DEBUG] REJECTED - Not a doc email: {recipient_email}")
                        continue
                    logger.info(f"[EMAIL DEBUG] ✓ Passed doc email check")

                    # Extract attachments
                    logger.info(f"[EMAIL DEBUG] Extracting attachments")
                    attachments = self.extract_attachments(email_message)
                    attachment_count = len(attachments)
                    total_size = sum(att['size'] for att in attachments)
                    logger.info(f"[EMAIL DEBUG] Found {attachment_count} attachments, total size: {total_size} bytes")

                    # SECURITY GATE #1: Find user by email address
                    logger.info(f"[EMAIL DEBUG] Looking up user by email address: {recipient_email}")
                    user = self.find_user_by_email_address(recipient_email)
                    if not user:
                        logger.error(f"[EMAIL DEBUG] REJECTED - No user found for address: {recipient_email}")
                        logger.error(f"[EMAIL DEBUG] Deleting email {email_id}")
                        # Delete email and continue
                        self.delete_email_from_inbox(imap, email_id)
                        continue
                    logger.info(f"[EMAIL DEBUG] ✓ User found: {user.email} (ID: {user.id})")

                    # SECURITY GATE #2 & #3: Check sender is allowed and active
                    logger.info(f"[EMAIL DEBUG] Checking if sender {sender_email} is allowed for user {user.id}")
                    is_allowed, allowed_sender = self.is_sender_allowed(str(user.id), sender_email)
                    if not is_allowed:
                        rejection_reason = f"Sender {sender_email} not in whitelist"
                        logger.error(f"[EMAIL DEBUG] REJECTED - Sender not whitelisted: {sender_email} for user {user.id}")
                        logger.error(f"[EMAIL DEBUG] Creating rejection log and sending notification")

                        # Create log
                        self.create_processing_log(
                            user_id=str(user.id),
                            sender_email=sender_email,
                            recipient_email=recipient_email,
                            subject=subject,
                            message_id=message_id,
                            uid=str(email_id),
                            attachment_count=attachment_count,
                            total_size_bytes=total_size,
                            status='rejected',
                            rejection_reason=rejection_reason
                        )

                        # Send notification
                        await self.send_rejection_notification(
                            user.email, sender_email, subject, rejection_reason
                        )

                        logger.error(f"[EMAIL DEBUG] Deleting email {email_id}")
                        # Delete email
                        self.delete_email_from_inbox(imap, email_id)
                        continue
                    logger.info(f"[EMAIL DEBUG] ✓ Sender is whitelisted: {sender_email}")

                    # SECURITY GATE #4 & #5: Quota check removed (Pro tier has unlimited email processing)
                    # Future: Add quota check here for Free tier if needed

                    # SECURITY GATE #6: Check attachment count
                    logger.info(f"[EMAIL DEBUG] Checking attachment count: {attachment_count}")
                    if attachment_count == 0:
                        logger.error(f"[EMAIL DEBUG] REJECTED - No attachments in email from {sender_email}")
                        rejection_reason = "No attachments found in email"

                        self.create_processing_log(
                            user_id=str(user.id),
                            sender_email=sender_email,
                            recipient_email=recipient_email,
                            subject=subject,
                            message_id=message_id,
                            uid=str(email_id),
                            attachment_count=0,
                            total_size_bytes=0,
                            status='rejected',
                            rejection_reason=rejection_reason
                        )

                        await self.send_rejection_notification(
                            user.email, sender_email, subject, rejection_reason
                        )

                        logger.error(f"[EMAIL DEBUG] Deleting email {email_id}")
                        self.delete_email_from_inbox(imap, email_id)
                        continue
                    logger.info(f"[EMAIL DEBUG] ✓ Has {attachment_count} attachments")

                    if attachment_count > settings.email_processing.max_attachments_per_email:
                        rejection_reason = f"Too many attachments ({attachment_count} > {settings.email_processing.max_attachments_per_email})"
                        logger.warning(f"Too many attachments from {sender_email}")

                        self.create_processing_log(
                            user_id=str(user.id),
                            sender_email=sender_email,
                            recipient_email=recipient_email,
                            subject=subject,
                            message_id=message_id,
                            uid=str(email_id),
                            attachment_count=attachment_count,
                            total_size_bytes=total_size,
                            status='rejected',
                            rejection_reason=rejection_reason
                        )

                        await self.send_rejection_notification(
                            user.email, sender_email, subject, rejection_reason
                        )

                        self.delete_email_from_inbox(imap, email_id)
                        continue

                    # SECURITY GATE #7: Check total size
                    logger.info(f"[EMAIL DEBUG] Checking total size: {total_size} bytes ({total_size / 1024 / 1024:.2f}MB)")
                    max_size_bytes = settings.email_processing.max_attachment_size_mb * 1024 * 1024
                    if total_size > max_size_bytes:
                        rejection_reason = f"Attachments too large ({total_size / 1024 / 1024:.1f}MB > {settings.email_processing.max_attachment_size_mb}MB)"
                        logger.error(f"[EMAIL DEBUG] REJECTED - Attachments too large from {sender_email}")

                        self.create_processing_log(
                            user_id=str(user.id),
                            sender_email=sender_email,
                            recipient_email=recipient_email,
                            subject=subject,
                            message_id=message_id,
                            uid=str(email_id),
                            attachment_count=attachment_count,
                            total_size_bytes=total_size,
                            status='rejected',
                            rejection_reason=rejection_reason
                        )

                        await self.send_rejection_notification(
                            user.email, sender_email, subject, rejection_reason
                        )

                        logger.error(f"[EMAIL DEBUG] Deleting email {email_id}")
                        self.delete_email_from_inbox(imap, email_id)
                        continue
                    logger.info(f"[EMAIL DEBUG] ✓ Size check passed")

                    # PASSED ALL SECURITY GATES - PROCESSING EMAIL
                    logger.info(f"[EMAIL DEBUG] ========================================")
                    logger.info(f"[EMAIL DEBUG] ✓✓✓ EMAIL PASSED ALL CHECKS - PROCESSING ✓✓✓")
                    logger.info(f"[EMAIL DEBUG] ========================================")

                    # Create processing log
                    logger.info(f"[EMAIL DEBUG] Creating processing log")
                    log = self.create_processing_log(
                        user_id=str(user.id),
                        sender_email=sender_email,
                        recipient_email=recipient_email,
                        subject=subject,
                        message_id=message_id,
                        uid=str(email_id),
                        attachment_count=attachment_count,
                        total_size_bytes=total_size,
                        status='processing'
                    )

                    # Save attachments to temp storage
                    logger.info(f"[EMAIL DEBUG] Saving {len(attachments)} attachments to temp storage")
                    temp_files = []
                    filenames = []
                    for attachment in attachments:
                        logger.info(f"[EMAIL DEBUG] Saving attachment: {attachment['filename']}")
                        filepath = self.save_attachment_to_temp(attachment)
                        if filepath:
                            temp_files.append(filepath)
                            filenames.append(attachment['filename'])
                            logger.info(f"[EMAIL DEBUG] ✓ Saved to {filepath}")
                        else:
                            logger.error(f"[EMAIL DEBUG] Failed to save attachment: {attachment['filename']}")

                    logger.info(f"[EMAIL DEBUG] Saved {len(temp_files)} files successfully")

                    # Update log with filenames
                    log.attachment_filenames = json.dumps(filenames)
                    log.processing_started_at = datetime.utcnow()
                    self.db.commit()

                    # Process attachments: scan, analyze, upload
                    logger.info(f"[EMAIL DEBUG] Starting attachment processing (scan, analyze, upload)")
                    documents_created, uploaded_document_ids, processing_errors, malware_detected = await self.process_attachments(
                        temp_files=temp_files,
                        filenames=filenames,
                        user=user,
                        sender_email=sender_email,
                        subject=subject,
                        email_id=email_id
                    )

                    logger.info(f"[EMAIL DEBUG] Processing complete. Results:")
                    logger.info(f"[EMAIL DEBUG]   - Documents created: {documents_created}")
                    logger.info(f"[EMAIL DEBUG]   - Document IDs: {uploaded_document_ids}")
                    logger.info(f"[EMAIL DEBUG]   - Malware detected: {malware_detected}")
                    logger.info(f"[EMAIL DEBUG]   - Processing errors: {processing_errors}")

                    # Handle malware detection
                    if malware_detected:
                        rejection_reason = f"Malware/threats detected: {', '.join(processing_errors)}"
                        logger.error(f"[EMAIL DEBUG] REJECTED - Malware detected: {rejection_reason}")

                        # Update log
                        log.status = 'rejected'
                        log.rejection_reason = rejection_reason
                        log.error_code = 'MALWARE_DETECTED'
                        log.processing_completed_at = datetime.utcnow()
                        self.db.commit()

                        # Cleanup
                        self.cleanup_temp_files(temp_files)
                        self.delete_email_from_inbox(imap, email_id)

                        # Notify user
                        await self.send_rejection_notification(
                            user.email, sender_email, subject, rejection_reason
                        )
                        continue

                    # Handle processing failures
                    if documents_created == 0:
                        rejection_reason = f"Failed to process attachments: {'; '.join(processing_errors)}"
                        logger.error(f"[EMAIL DEBUG] FAILED - No documents created: {rejection_reason}")

                        # Update log
                        log.status = 'failed'
                        log.rejection_reason = rejection_reason
                        log.error_code = 'PROCESSING_FAILED'
                        log.error_message = json.dumps(processing_errors)
                        log.processing_completed_at = datetime.utcnow()
                        self.db.commit()

                        # Cleanup
                        self.cleanup_temp_files(temp_files)
                        self.delete_email_from_inbox(imap, email_id)

                        # Notify user
                        await self.send_rejection_notification(
                            user.email, sender_email, subject, rejection_reason
                        )
                        continue

                    # SUCCESS! Email passed all checks and documents created
                    logger.info(f"[EMAIL DEBUG] ========================================")
                    logger.info(f"[EMAIL DEBUG] ✓✓✓ SUCCESS - {documents_created} DOCUMENTS CREATED ✓✓✓")
                    logger.info(f"[EMAIL DEBUG] ========================================")

                    # Update log with document IDs
                    log.processing_metadata = json.dumps({
                        'uploaded_document_ids': uploaded_document_ids,
                        'processing_errors': processing_errors
                    })

                    # Update usage
                    logger.info(f"[EMAIL DEBUG] Updating monthly usage for user {user.id}")
                    self.increment_monthly_usage(str(user.id), documents_created)

                    # Update allowed sender stats
                    if allowed_sender:
                        logger.info(f"[EMAIL DEBUG] Updating sender stats for {sender_email}")
                        self.update_allowed_sender_stats(allowed_sender)

                    # Update log
                    log.status = 'completed'
                    log.documents_created = documents_created
                    log.processing_completed_at = datetime.utcnow()
                    log.processing_time_ms = int((log.processing_completed_at - log.processing_started_at).total_seconds() * 1000)
                    self.db.commit()
                    logger.info(f"[EMAIL DEBUG] Processing log updated to 'completed'")

                    # Send completion notification
                    logger.info(f"[EMAIL DEBUG] Sending completion notification to {user.email}")
                    await self.send_completion_notification(
                        user.email, sender_email, subject, documents_created
                    )

                    # CRITICAL CLEANUP: Delete email and temp files
                    logger.info(f"[EMAIL DEBUG] Cleaning up temp files and deleting email {email_id}")
                    self.cleanup_temp_files(temp_files)
                    self.delete_email_from_inbox(imap, email_id)
                    logger.info(f"[EMAIL DEBUG] ✓ Cleanup complete")

                    processed_count += 1
                    logger.info(f"[EMAIL DEBUG] Email processing complete! Total processed in this batch: {processed_count}")
                    logger.info(f"Successfully processed email from {sender_email}: {documents_created} documents created")

                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {str(e)}")
                    # Cleanup any temp files
                    if 'temp_files' in locals():
                        self.cleanup_temp_files(temp_files)
                    continue

            return processed_count

        except Exception as e:
            logger.error(f"Error polling inbox: {str(e)}")
            return 0

        finally:
            if imap:
                try:
                    imap.close()
                    imap.logout()
                except:
                    pass


# Global instance
def get_email_processing_service(db: Session) -> EmailProcessingService:
    """Get email processing service instance"""
    return EmailProcessingService(db)

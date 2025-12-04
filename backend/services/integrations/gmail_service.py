"""
Gmail Integration Service
Email automation, filtering, and smart responses
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import base64
import re

from backend.services.performance_optimizer import cached, rate_limit


class GmailService:
    """
    Gmail service for email automation and management
    """

    def __init__(self):
        self.service = None
        self.authenticated = False
        self.health_status = {
            "last_check": None,
            "total_emails_processed": 0,
            "auto_replies_sent": 0
        }

    async def authenticate(self) -> bool:
        """
        Authenticate with Gmail API

        Returns:
            True if authenticated successfully
        """
        try:
            # TODO: Implement OAuth2 flow for Gmail
            # Similar to Google Calendar authentication
            logger.info("Gmail authentication not yet implemented")
            return False

        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False

    @cached(ttl=60)  # Cache for 1 minute
    @rate_limit(max_calls=20, time_window=60)  # 20 requests per minute
    async def get_unread_emails(
        self,
        max_results: int = 20,
        label_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get unread emails

        Args:
            max_results: Maximum number of emails
            label_ids: Filter by label IDs (e.g., ['INBOX', 'UNREAD'])

        Returns:
            List of email dictionaries
        """
        if not self.service:
            await self.authenticate()

        if not self.authenticated:
            logger.warning("Gmail not authenticated")
            return []

        try:
            # Build query
            query = "is:unread"
            if label_ids is None:
                label_ids = ['INBOX']

            # Get messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                labelIds=label_ids,
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])

            # Fetch full message details
            emails = []
            for msg in messages:
                email_data = await self._get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)

            self.health_status["last_check"] = datetime.now()
            return emails

        except Exception as e:
            logger.error(f"Failed to get unread emails: {e}")
            return []

    async def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get full email details"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = {h['name'].lower(): h['value'] for h in message['payload']['headers']}

            # Extract body
            body = ""
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
            else:
                data = message['payload']['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')

            return {
                "id": message_id,
                "thread_id": message['threadId'],
                "from": headers.get('from', ''),
                "to": headers.get('to', ''),
                "subject": headers.get('subject', ''),
                "date": headers.get('date', ''),
                "body": body,
                "snippet": message.get('snippet', ''),
                "labels": message.get('labelIds', [])
            }

        except Exception as e:
            logger.error(f"Failed to get email details: {e}")
            return None

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> bool:
        """
        Send an email

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            True if sent successfully
        """
        if not self.service:
            await self.authenticate()

        if not self.authenticated:
            logger.warning("Gmail not authenticated")
            return False

        try:
            # Create message
            message = self._create_message(to, subject, body, cc, bcc)

            # Send
            self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            logger.info(f"Email sent to {to}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _create_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None
    ) -> Dict[str, str]:
        """Create email message"""
        import email.mime.text

        message = email.mime.text.MIMEText(body)
        message['to'] = to
        message['subject'] = subject

        if cc:
            message['cc'] = cc
        if bcc:
            message['bcc'] = bcc

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw}

    async def auto_reply_to_emails(
        self,
        emails: List[Dict[str, Any]],
        reply_template: str
    ) -> Dict[str, int]:
        """
        Auto-reply to emails using template

        Args:
            emails: List of emails to reply to
            reply_template: Reply message template

        Returns:
            Summary of sent/failed
        """
        results = {"sent": 0, "failed": 0}

        for email in emails:
            try:
                # Parse sender
                from_email = self._extract_email(email['from'])

                # Generate reply
                reply_body = reply_template.format(
                    name=self._extract_name(email['from']),
                    subject=email['subject']
                )

                # Send reply
                success = await self.send_email(
                    to=from_email,
                    subject=f"Re: {email['subject']}",
                    body=reply_body
                )

                if success:
                    results["sent"] += 1
                    # Mark as read
                    await self.mark_as_read(email['id'])
                else:
                    results["failed"] += 1

            except Exception as e:
                logger.error(f"Failed to auto-reply: {e}")
                results["failed"] += 1

        self.health_status["auto_replies_sent"] += results["sent"]
        logger.info(f"Auto-reply: {results['sent']} sent, {results['failed']} failed")
        return results

    async def mark_as_read(self, message_id: str) -> bool:
        """Mark email as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return False

    async def filter_emails_by_sender(
        self,
        sender_pattern: str,
        action: str = "archive",
        label: Optional[str] = None
    ) -> int:
        """
        Filter emails by sender pattern

        Args:
            sender_pattern: Regex pattern for sender
            action: Action to take ('archive', 'label', 'delete')
            label: Label to apply if action is 'label'

        Returns:
            Number of emails processed
        """
        emails = await self.get_unread_emails(max_results=100)
        processed = 0

        for email in emails:
            sender = email['from']

            if re.search(sender_pattern, sender, re.IGNORECASE):
                if action == "archive":
                    await self._archive_email(email['id'])
                elif action == "label" and label:
                    await self._label_email(email['id'], label)
                elif action == "delete":
                    await self._delete_email(email['id'])

                processed += 1

        logger.info(f"Filtered {processed} emails from pattern: {sender_pattern}")
        return processed

    async def _archive_email(self, message_id: str) -> bool:
        """Archive email (remove INBOX label)"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to archive: {e}")
            return False

    async def _label_email(self, message_id: str, label: str) -> bool:
        """Add label to email"""
        try:
            # Get or create label
            label_id = await self._get_or_create_label(label)

            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to label: {e}")
            return False

    async def _delete_email(self, message_id: str) -> bool:
        """Move email to trash"""
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            return False

    async def _get_or_create_label(self, label_name: str) -> str:
        """Get label ID or create if doesn't exist"""
        try:
            # List labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            # Find matching label
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    return label['id']

            # Create new label
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }

            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()

            return created_label['id']

        except Exception as e:
            logger.error(f"Failed to get/create label: {e}")
            return ""

    def _extract_email(self, from_field: str) -> str:
        """Extract email address from 'from' field"""
        match = re.search(r'<(.+?)>', from_field)
        if match:
            return match.group(1)
        return from_field.strip()

    def _extract_name(self, from_field: str) -> str:
        """Extract name from 'from' field"""
        match = re.search(r'^(.+?)\s*<', from_field)
        if match:
            return match.group(1).strip('"')
        return "there"

    async def summarize_important_emails(
        self,
        max_emails: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get summary of important unread emails

        Args:
            max_emails: Maximum number of emails to summarize

        Returns:
            List of email summaries
        """
        emails = await self.get_unread_emails(
            max_results=max_emails,
            label_ids=['INBOX', 'IMPORTANT']
        )

        summaries = []
        for email in emails:
            summary = {
                "from": self._extract_name(email['from']),
                "from_email": self._extract_email(email['from']),
                "subject": email['subject'],
                "snippet": email['snippet'],
                "date": email['date']
            }
            summaries.append(summary)

        self.health_status["total_emails_processed"] += len(summaries)
        return summaries

    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status"""
        return {
            **self.health_status,
            "is_authenticated": self.authenticated,
            "is_healthy": self.authenticated,
            "last_check_ago": (
                str(datetime.now() - self.health_status["last_check"])
                if self.health_status["last_check"]
                else "Never"
            )
        }

"""
Email service for sending notifications via Microsoft 365
Supports both SMTP and Microsoft Graph API methods
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import logging
from typing import Optional, List

# For Microsoft Graph API (optional)
try:
    import requests
    import json
    GRAPH_API_AVAILABLE = True
except ImportError:
    GRAPH_API_AVAILABLE = False

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for Microsoft 365 integration"""
    
    def __init__(self):
        """Initialize email service with Microsoft 365 configuration"""
        # Microsoft 365 SMTP Configuration
        self.smtp_server = "smtp.office365.com"
        self.smtp_port = 587
        self.smtp_username = os.getenv('OFFICE365_EMAIL', 'support@homegrubhub.co.uk')
        self.smtp_password = os.getenv('OFFICE365_PASSWORD', '')
        
        # Email addresses
        # Option 1: Use homegrubhub.co.uk (requires SPF setup)
        self.support_from_email = 'support@homegrubhub.co.uk'
        self.support_to_email = 'contact@homegrubhub.co.uk'
        
        # Option 2: Use tenant domain (if SPF issues persist)
        # self.support_from_email = 'support@palmertech.co.uk'  
        # self.support_to_email = 'homegrubhub@palmertech.co.uk'
        
        # Microsoft Graph API Configuration (optional)
        self.graph_tenant_id = os.getenv('OFFICE365_TENANT_ID', '')
        self.graph_client_id = os.getenv('OFFICE365_CLIENT_ID', '')
        self.graph_client_secret = os.getenv('OFFICE365_CLIENT_SECRET', '')
        
    def send_support_email(self, name: str, email: str, subject: str, 
                          category: str, message: str) -> bool:
        """
        Send support email from support@homegrubhub.co.uk to contact@homegrubhub.co.uk
        
        Args:
            name: Customer's name
            email: Customer's email
            subject: Email subject
            category: Support category
            message: Customer's message
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Email subject and body
            email_subject = f"[HomeGrubHub Support] {category}: {subject}"
            body = self._create_support_email_body(name, email, category, subject, message)
            
            # Debug: Log configuration status
            logger.info(f"Graph API configured: {self._is_graph_api_configured()}")
            logger.info(f"Graph API available: {GRAPH_API_AVAILABLE}")
            if self._is_graph_api_configured():
                logger.info(f"Tenant ID present: {bool(self.graph_tenant_id)}")
                logger.info(f"Client ID present: {bool(self.graph_client_id)}")
                logger.info(f"Client Secret present: {bool(self.graph_client_secret)}")
            
            # Try Graph API first (preferred method)
            if self._is_graph_api_configured():
                logger.info("Attempting to send via Microsoft Graph API...")
                success = self._send_via_graph_api(self.support_to_email, email_subject, body, reply_to=email)
                if success:
                    logger.info("Support email sent successfully via Microsoft Graph API")
                    return True
                else:
                    logger.warning("Graph API failed, falling back to SMTP")
            else:
                logger.info("Graph API not configured, using SMTP")
            
            # Fallback to SMTP if Graph API is not configured or fails
            logger.info("Attempting to send via SMTP...")
            msg = MIMEMultipart()
            msg['From'] = self.support_from_email
            msg['To'] = self.support_to_email
            msg['Subject'] = email_subject
            msg['Reply-To'] = email  # So replies go back to the customer
            msg.attach(MIMEText(body, 'plain'))
            
            return self._send_via_smtp(msg, self.support_to_email)
            
        except Exception as e:
            logger.error(f"Error sending support email: {e}")
            return False
    
    def send_ticket_confirmation_to_user(self, customer_email: str, customer_name: str, 
                                        ticket_number: str, subject: str) -> bool:
        """
        Send ticket confirmation email to the user AND notify support team
        
        Args:
            customer_email: Customer's email address
            customer_name: Customer's name  
            ticket_number: Ticket reference number
            subject: Original ticket subject
            
        Returns:
            bool: True if user confirmation sent successfully
        """
        try:
            # 1. Send confirmation to user
            user_subject = f"Support Ticket Created: #{ticket_number}"
            user_body = f"""Dear {customer_name},

Thank you for contacting HomeGrubHub Support. We have received your support request and created ticket #{ticket_number}.

Your Request Details:
Subject: {subject}
Ticket Number: #{ticket_number}
Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

What happens next?
- Our support team will review your request
- You'll receive updates via email to this address: {customer_email}
- For urgent matters, you can reference ticket #{ticket_number}

We aim to respond to all support requests within 24 hours.

Best regards,
HomeGrubHub Support Team

---
This is an automated message. Please do not reply to this email.
For additional questions, please create a new support ticket."""

            user_success = False
            
            # Try Graph API first for user confirmation
            if self._is_graph_api_configured():
                user_success = self._send_via_graph_api(customer_email, user_subject, user_body)
                if user_success:
                    logger.info(f"User confirmation email sent via Graph API to {customer_email}")
                else:
                    logger.warning("Graph API failed for user confirmation, trying SMTP")
            
            # Fallback to SMTP for user confirmation
            if not user_success:
                msg = MIMEMultipart()
                msg['From'] = self.support_from_email
                msg['To'] = customer_email
                msg['Subject'] = user_subject
                msg.attach(MIMEText(user_body, 'plain'))
                user_success = self._send_via_smtp(msg, customer_email)
            
            # 2. Also notify support team (but don't fail if this fails)
            try:
                support_subject = f"New Support Ticket: #{ticket_number} - {subject}"
                support_body = f"""New support ticket created:

Ticket Number: #{ticket_number}
From: {customer_name} <{customer_email}>
Subject: {subject}
Priority: Normal
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please log into the admin panel to view full details and respond.

---
This notification was sent to: {self.support_to_email}"""

                # Send notification to support team
                if self._is_graph_api_configured():
                    self._send_via_graph_api(self.support_to_email, support_subject, support_body, reply_to=customer_email)
                else:
                    support_msg = MIMEMultipart()
                    support_msg['From'] = self.support_from_email
                    support_msg['To'] = self.support_to_email
                    support_msg['Subject'] = support_subject
                    support_msg['Reply-To'] = customer_email  # So support can reply directly
                    support_msg.attach(MIMEText(support_body, 'plain'))
                    self._send_via_smtp(support_msg, self.support_to_email)
                    
                logger.info(f"Support notification sent for ticket #{ticket_number}")
                
            except Exception as e:
                logger.warning(f"Failed to send support notification for ticket #{ticket_number}: {e}")
                # Don't fail the whole operation if support notification fails
            
            return user_success
            
        except Exception as e:
            logger.error(f"Error sending ticket confirmation: {e}")
            return False

    def send_confirmation_email(self, customer_email: str, customer_name: str, 
                              ticket_number: Optional[str] = None) -> bool:
        """
        Send confirmation email back to the customer
        
        Args:
            customer_email: Customer's email address
            customer_name: Customer's name
            ticket_number: Optional ticket number for reference
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            email_subject = "Thank you for contacting HomeGrubHub Support"
            body = self._create_confirmation_email_body(customer_name, ticket_number)
            
            # Try Graph API first (preferred method)
            if self._is_graph_api_configured():
                success = self._send_via_graph_api(customer_email, email_subject, body)
                if success:
                    logger.info("Confirmation email sent successfully via Microsoft Graph API")
                    return True
                else:
                    logger.warning("Graph API failed for confirmation email, falling back to SMTP")
            
            # Fallback to SMTP
            msg = MIMEMultipart()
            msg['From'] = self.support_from_email
            msg['To'] = customer_email
            msg['Subject'] = email_subject
            msg.attach(MIMEText(body, 'plain'))
            
            return self._send_via_smtp(msg, customer_email)
            
        except Exception as e:
            logger.error(f"Error sending confirmation email: {e}")
            return False
    
    def _send_via_smtp(self, msg: MIMEMultipart, to_email: str) -> bool:
        """
        Send email via Microsoft 365 SMTP
        
        Args:
            msg: Email message object
            to_email: Recipient email address
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Create secure connection
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
                
                # Send email
                text = msg.as_string()
                server.sendmail(self.support_from_email, to_email, text)
                
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Authentication failed. Check Office 365 credentials.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False
    
    def _send_via_graph_api(self, to_email: str, subject: str, body: str, reply_to: Optional[str] = None) -> bool:
        """
        Send email via Microsoft Graph API (preferred method)
        Uses Application permissions for secure server-to-server communication
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body content
            reply_to: Optional reply-to email address
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not GRAPH_API_AVAILABLE:
            logger.warning("Microsoft Graph API dependencies not available")
            return False
            
        if not self._is_graph_api_configured():
            logger.warning("Microsoft Graph API credentials not configured")
            return False
            
        try:
            # Get access token using client credentials flow
            access_token = self._get_graph_api_token()
            if not access_token:
                logger.error("Failed to obtain Graph API access token")
                return False
            
            # Prepare email message
            email_message = {
                'message': {
                    'subject': subject,
                    'body': {
                        'contentType': 'Text',
                        'content': body
                    },
                    'toRecipients': [
                        {
                            'emailAddress': {
                                'address': to_email
                            }
                        }
                    ]
                }
            }
            
            # Add reply-to if specified
            if reply_to:
                email_message['message']['replyTo'] = [
                    {
                        'emailAddress': {
                            'address': reply_to
                        }
                    }
                ]
            
            # Send email via Graph API
            graph_url = f"https://graph.microsoft.com/v1.0/users/{self.support_from_email}/sendMail"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(graph_url, headers=headers, json=email_message)
            
            if response.status_code == 202:  # Graph API returns 202 for successful email sending
                logger.info(f"Email sent successfully via Graph API to {to_email}")
                return True
            else:
                logger.error(f"Graph API returned status {response.status_code}: {response.text}")
                return False
            
        except requests.RequestException as e:
            logger.error(f"Graph API request failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with Graph API: {e}")
            return False
    
    def _get_graph_api_token(self) -> Optional[str]:
        """
        Get access token for Microsoft Graph API using client credentials flow
        
        Returns:
            Optional[str]: Access token if successful, None otherwise
        """
        try:
            token_url = f"https://login.microsoftonline.com/{self.graph_tenant_id}/oauth2/v2.0/token"
            token_data = {
                'client_id': self.graph_client_id,
                'client_secret': self.graph_client_secret,
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials'
            }
            
            logger.info(f"Requesting token from: {token_url}")
            logger.info(f"Using client_id: {self.graph_client_id}")
            logger.info(f"Using tenant_id: {self.graph_tenant_id}")
            
            response = requests.post(token_url, data=token_data)
            
            logger.info(f"Token response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Token request failed: {response.text}")
                return None
            
            response.raise_for_status()
            
            token_info = response.json()
            access_token = token_info.get('access_token')
            if access_token:
                logger.info("Successfully obtained Graph API access token")
            else:
                logger.error("No access token in response")
                logger.error(f"Response: {token_info}")
            
            return access_token
            
        except requests.RequestException as e:
            logger.error(f"Failed to get Graph API token - Request error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting Graph API token: {e}")
            return None
    
    def _is_graph_api_configured(self) -> bool:
        """Check if Graph API credentials are properly configured"""
        return bool(all([
            self.graph_tenant_id,
            self.graph_client_id,
            self.graph_client_secret,
            GRAPH_API_AVAILABLE
        ]))
    
    def _create_support_email_body(self, name: str, email: str, category: str, 
                                  subject: str, message: str) -> str:
        """Create formatted email body for support requests"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        return f"""New support request from HomeGrubHub website:

Customer Details:
- Name: {name}
- Email: {email}
- Category: {category}
- Subject: {subject}

Message:
{message}

---
Submitted: {timestamp}
Source: HomeGrubHub Contact Form
Website: homegrubhub.co.uk

To reply to this customer, simply reply to this email or contact them directly at: {email}
"""
    
    def _create_confirmation_email_body(self, customer_name: str, 
                                       ticket_number: Optional[str] = None) -> str:
        """Create confirmation email body for customers"""
        ticket_info = f"\nYour reference number is: {ticket_number}\n" if ticket_number else ""
        
        return f"""Hello {customer_name},

Thank you for contacting HomeGrubHub Support! We have received your message and our team will get back to you within 24 hours.{ticket_info}

In the meantime, you might find these resources helpful:
- Help Center: https://homegrubhub.co.uk/support
- Frequently Asked Questions: https://homegrubhub.co.uk/support/faq
- Getting Started Guide: https://homegrubhub.co.uk/support/getting-started

If you have any urgent questions, you can also reply to this email.

Best regards,
The HomeGrubHub Support Team

---
HomeGrubHub - Your Personal Recipe Manager
Website: https://homegrubhub.co.uk
Email: support@homegrubhub.co.uk
"""
    
    def test_connection(self) -> dict:
        """
        Test the email service connection
        
        Returns:
            dict: Connection test results
        """
        results = {
            'smtp_configured': bool(self.smtp_username and self.smtp_password),
            'smtp_connection': False,
            'graph_api_configured': self._is_graph_api_configured(),
            'graph_api_available': GRAPH_API_AVAILABLE,
            'graph_api_connection': False,
            'preferred_method': 'graph_api' if self._is_graph_api_configured() else 'smtp'
        }
        
        # Test Graph API connection (preferred)
        if results['graph_api_configured']:
            try:
                token = self._get_graph_api_token()
                if token:
                    results['graph_api_connection'] = True
                    logger.info("Graph API connection test successful")
                else:
                    logger.error("Graph API token acquisition failed")
            except Exception as e:
                logger.error(f"Graph API connection test failed: {e}")
                results['graph_api_error'] = str(e)
        
        # Test SMTP connection (fallback)
        if results['smtp_configured']:
            try:
                context = ssl.create_default_context()
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls(context=context)
                    server.login(self.smtp_username, self.smtp_password)
                    results['smtp_connection'] = True
                    logger.info("SMTP connection test successful")
            except Exception as e:
                logger.error(f"SMTP connection test failed: {e}")
                results['smtp_error'] = str(e)
        
        return results


# Singleton instance
email_service = EmailService()


def send_support_email(name: str, email: str, subject: str, category: str, message: str) -> bool:
    """
    Convenience function to send support email
    Compatible with existing code
    """
    success = email_service.send_support_email(name, email, subject, category, message)
    
    # Also send confirmation email to customer
    if success:
        email_service.send_confirmation_email(email, name)
    
    return success


def test_email_service() -> dict:
    """Test email service configuration"""
    return email_service.test_connection()

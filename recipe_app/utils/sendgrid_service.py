"""
SendGrid email service for transactional emails
Handles user registration, password reset, billing notifications, and other automated emails
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import json

# Configure logging
logger = logging.getLogger(__name__)

class SendGridEmailService:
    """
    SendGrid service for handling all automated email notifications
    Free tier: 100 emails/day - perfect for transactional emails
    """
    
    def __init__(self):
        """Initialize SendGrid client"""
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        self.client = None
        self.from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@homegrubhub.co.uk')
        self.from_name = os.environ.get('SENDGRID_FROM_NAME', 'HomeGrubHub')
        
        # Email template IDs (if using SendGrid templates)
        self.template_ids = {
            'registration': os.environ.get('SENDGRID_REGISTRATION_TEMPLATE_ID'),
            'password_reset': os.environ.get('SENDGRID_PASSWORD_RESET_TEMPLATE_ID'),
            'welcome': os.environ.get('SENDGRID_WELCOME_TEMPLATE_ID'),
            'billing': os.environ.get('SENDGRID_BILLING_TEMPLATE_ID')
        }
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize SendGrid API client"""
        try:
            if self.api_key:
                self.client = SendGridAPIClient(api_key=self.api_key)
                logger.info("SendGrid API client initialized successfully")
            else:
                logger.warning("SENDGRID_API_KEY not configured")
        except Exception as e:
            logger.error(f"Error initializing SendGrid client: {e}")
    
    def _is_configured(self) -> bool:
        """Check if SendGrid is properly configured"""
        return self.client is not None and self.api_key is not None
    
    # ===========================================
    # TRANSACTIONAL EMAILS
    # ===========================================
    
    def send_registration_confirmation(self, user_email: str, user_name: str, 
                                     confirmation_link: str) -> bool:
        """
        Send email confirmation for new user registration
        
        Args:
            user_email: User's email address
            user_name: User's display name
            confirmation_link: URL to confirm email address
            
        Returns:
            bool: True if email sent successfully
        """
        if not self._is_configured():
            logger.error("SendGrid not configured for registration confirmation")
            return False
        
        try:
            # Create email content
            subject = "Welcome to HomeGrubHub - Please Confirm Your Email"
            html_content = self._create_registration_confirmation_html(user_name, confirmation_link)
            plain_content = self._create_registration_confirmation_text(user_name, confirmation_link)
            
            # Create the email
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(user_email, user_name),
                subject=subject,
                html_content=Content("text/html", html_content),
                plain_text_content=Content("text/plain", plain_content)
            )
            
            # Add tracking
            message.tracking_settings = {
                "click_tracking": {"enable": True},
                "open_tracking": {"enable": True}
            }
            
            # Send email
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Registration confirmation sent to {user_email}")
                return True
            else:
                logger.error(f"Failed to send registration confirmation to {user_email}. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending registration confirmation to {user_email}: {e}")
            return False
    
    def send_password_reset(self, user_email: str, user_name: str, 
                           reset_link: str, expires_in_hours: int = 24) -> bool:
        """
        Send password reset email
        
        Args:
            user_email: User's email address
            user_name: User's display name
            reset_link: URL to reset password
            expires_in_hours: How many hours the link is valid
            
        Returns:
            bool: True if email sent successfully
        """
        if not self._is_configured():
            logger.error("SendGrid not configured for password reset")
            return False
        
        try:
            subject = "Reset Your HomeGrubHub Password"
            html_content = self._create_password_reset_html(user_name, reset_link, expires_in_hours)
            plain_content = self._create_password_reset_text(user_name, reset_link, expires_in_hours)
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(user_email, user_name),
                subject=subject,
                html_content=Content("text/html", html_content),
                plain_text_content=Content("text/plain", plain_content)
            )
            
            # Add security-focused tracking
            message.tracking_settings = {
                "click_tracking": {"enable": True},
                "open_tracking": {"enable": True}
            }
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Password reset email sent to {user_email}")
                return True
            else:
                logger.error(f"Failed to send password reset to {user_email}. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending password reset to {user_email}: {e}")
            return False
    
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """
        Send welcome email for new users (after Auth0 registration)
        
        Args:
            user_email: User's email address
            user_name: User's display name
            
        Returns:
            bool: True if email sent successfully
        """
        if not self._is_configured():
            logger.error("SendGrid not configured for welcome email")
            return False
        
        try:
            subject = f"Welcome to HomeGrubHub, {user_name}!"
            html_content = self._create_welcome_email_html(user_name)
            plain_content = self._create_welcome_email_text(user_name)
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(user_email, user_name),
                subject=subject,
                html_content=Content("text/html", html_content),
                plain_text_content=Content("text/plain", plain_content)
            )
            
            message.tracking_settings = {
                "click_tracking": {"enable": True},
                "open_tracking": {"enable": True}
            }
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Welcome email sent to {user_email}")
                return True
            else:
                logger.error(f"Failed to send welcome email to {user_email}. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending welcome email to {user_email}: {e}")
            return False
    
    def send_billing_notification(self, user_email: str, user_name: str, 
                                 notification_type: str, amount: float = None, 
                                 subscription_plan: str = None) -> bool:
        """
        Send billing-related notifications
        
        Args:
            user_email: User's email address
            user_name: User's display name
            notification_type: 'payment_success', 'payment_failed', 'trial_ending', 'subscription_cancelled'
            amount: Payment amount (if applicable)
            subscription_plan: Plan name (if applicable)
            
        Returns:
            bool: True if email sent successfully
        """
        if not self._is_configured():
            logger.error("SendGrid not configured for billing notification")
            return False
        
        try:
            subject, html_content, plain_content = self._create_billing_notification_content(
                notification_type, user_name, amount, subscription_plan
            )
            
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(user_email, user_name),
                subject=subject,
                html_content=Content("text/html", html_content),
                plain_text_content=Content("text/plain", plain_content)
            )
            
            message.tracking_settings = {
                "click_tracking": {"enable": True},
                "open_tracking": {"enable": True}
            }
            
            response = self.client.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Billing notification ({notification_type}) sent to {user_email}")
                return True
            else:
                logger.error(f"Failed to send billing notification to {user_email}. Status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending billing notification to {user_email}: {e}")
            return False
    
    # ===========================================
    # EMAIL CONTENT TEMPLATES
    # ===========================================
    
    def _create_registration_confirmation_html(self, user_name: str, confirmation_link: str) -> str:
        """Create HTML content for registration confirmation email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to HomeGrubHub</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #28a745; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #ffffff; padding: 30px 20px; border: 1px solid #dee2e6; }}
                .button {{ display: inline-block; background-color: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 14px; color: #6c757d; border-radius: 0 0 8px 8px; }}
                .features {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .features ul {{ margin: 0; padding-left: 20px; }}
                .features li {{ margin-bottom: 8px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0; font-size: 28px;">Welcome to HomeGrubHub!</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Your culinary journey starts here</p>
            </div>
            <div class="content">
                <h2 style="color: #28a745;">Hi {user_name},</h2>
                <p>Thank you for joining HomeGrubHub! We're excited to help you discover amazing recipes, plan your meals, and make cooking more enjoyable.</p>
                
                <p>To get started, please confirm your email address by clicking the button below:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{confirmation_link}" class="button">Confirm Your Email</a>
                </div>
                
                <div class="features">
                    <h3 style="color: #28a745; margin-top: 0;">What you can do with HomeGrubHub:</h3>
                    <ul>
                        <li><strong>Save & organize recipes</strong> - Build your personal recipe collection</li>
                        <li><strong>Smart meal planning</strong> - Plan your week with ease</li>
                        <li><strong>Automated shopping lists</strong> - Never forget an ingredient</li>
                        <li><strong>Nutrition tracking</strong> - Monitor your health goals</li>
                        <li><strong>Join our community</strong> - Share recipes and get inspired</li>
                    </ul>
                </div>
                
                <p>If you didn't create this account, you can safely ignore this email.</p>
                
                <p style="margin-top: 30px;">Happy cooking!<br><strong>The HomeGrubHub Team</strong></p>
            </div>
            <div class="footer">
                <p>This email was sent to {user_name} because you registered for HomeGrubHub.<br>
                Need help? Contact us at <a href="mailto:support@homegrubhub.co.uk">support@homegrubhub.co.uk</a></p>
                <p style="margin-top: 15px; font-size: 12px; color: #999;">
                    HomeGrubHub • Making cooking easier, one recipe at a time
                </p>
            </div>
        </body>
        </html>
        """
    
    def _create_registration_confirmation_text(self, user_name: str, confirmation_link: str) -> str:
        """Create plain text content for registration confirmation email"""
        return f"""
Welcome to HomeGrubHub!

Hi {user_name},

Thank you for joining HomeGrubHub! We're excited to help you discover amazing recipes, plan your meals, and make cooking more enjoyable.

To get started, please confirm your email address by visiting this link:
{confirmation_link}

What you can do with HomeGrubHub:
• Save & organize recipes - Build your personal recipe collection
• Smart meal planning - Plan your week with ease  
• Automated shopping lists - Never forget an ingredient
• Nutrition tracking - Monitor your health goals
• Join our community - Share recipes and get inspired

If you didn't create this account, you can safely ignore this email.

Happy cooking!
The HomeGrubHub Team

---
This email was sent because you registered for HomeGrubHub.
Need help? Contact us at support@homegrubhub.co.uk
HomeGrubHub • Making cooking easier, one recipe at a time
        """
    
    def _create_welcome_email_html(self, user_name: str) -> str:
        """Create HTML content for welcome email (Auth0 users)"""
        dashboard_link = "https://homegrubhub.co.uk/dashboard"
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to HomeGrubHub</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #28a745; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #ffffff; padding: 30px 20px; border: 1px solid #dee2e6; }}
                .button {{ display: inline-block; background-color: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 14px; color: #6c757d; border-radius: 0 0 8px 8px; }}
                .getting-started {{ background-color: #e8f5e8; padding: 20px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0; font-size: 28px;">Welcome, {user_name}!</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">You're all set to start cooking</p>
            </div>
            <div class="content">
                <h2 style="color: #28a745;">Ready to revolutionize your cooking?</h2>
                <p>Your HomeGrubHub account is ready! You now have access to all our features to make meal planning and cooking easier than ever.</p>
                
                <div class="getting-started">
                    <h3 style="color: #28a745; margin-top: 0;">🚀 Quick Start Guide:</h3>
                    <ol style="margin: 0; padding-left: 20px;">
                        <li><strong>Browse recipes</strong> - Discover thousands of delicious recipes</li>
                        <li><strong>Create meal plans</strong> - Plan your week in minutes</li>
                        <li><strong>Generate shopping lists</strong> - Get organized grocery lists automatically</li>
                        <li><strong>Track nutrition</strong> - Monitor your dietary goals</li>
                    </ol>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{dashboard_link}" class="button">Go to Your Dashboard</a>
                </div>
                
                <p>Need help getting started? Check out our <a href="https://homegrubhub.co.uk/support/getting-started" style="color: #28a745;">getting started guide</a> or contact our support team.</p>
                
                <p style="margin-top: 30px;">Happy cooking!<br><strong>The HomeGrubHub Team</strong></p>
            </div>
            <div class="footer">
                <p>Welcome to the HomeGrubHub community!<br>
                Need help? Contact us at <a href="mailto:support@homegrubhub.co.uk">support@homegrubhub.co.uk</a></p>
            </div>
        </body>
        </html>
        """
    
    def _create_welcome_email_text(self, user_name: str) -> str:
        """Create plain text content for welcome email"""
        return f"""
Welcome, {user_name}!

Ready to revolutionize your cooking?

Your HomeGrubHub account is ready! You now have access to all our features to make meal planning and cooking easier than ever.

Quick Start Guide:
1. Browse recipes - Discover thousands of delicious recipes
2. Create meal plans - Plan your week in minutes  
3. Generate shopping lists - Get organized grocery lists automatically
4. Track nutrition - Monitor your dietary goals

Go to your dashboard: https://homegrubhub.co.uk/dashboard

Need help getting started? Check out our getting started guide or contact our support team at support@homegrubhub.co.uk

Happy cooking!
The HomeGrubHub Team

---
Welcome to the HomeGrubHub community!
        """
    
    def _create_password_reset_html(self, user_name: str, reset_link: str, expires_in_hours: int) -> str:
        """Create HTML content for password reset email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Your HomeGrubHub Password</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc3545; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background-color: #ffffff; padding: 30px 20px; border: 1px solid #dee2e6; }}
                .button {{ display: inline-block; background-color: #dc3545; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 14px; color: #6c757d; border-radius: 0 0 8px 8px; }}
                .security-notice {{ background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0; font-size: 28px;">🔐 Password Reset</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Secure your account</p>
            </div>
            <div class="content">
                <h2 style="color: #dc3545;">Hi {user_name},</h2>
                <p>We received a request to reset your HomeGrubHub password. If you made this request, click the button below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" class="button">Reset My Password</a>
                </div>
                
                <div class="warning">
                    <strong>⏰ Important:</strong> This link will expire in {expires_in_hours} hours for security reasons.
                </div>
                
                <div class="security-notice">
                    <h4 style="margin-top: 0; color: #0c5460;">🛡️ Security Notice:</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li>If you didn't request this reset, you can safely ignore this email</li>
                        <li>Your password will not be changed unless you click the link above</li>
                        <li>Never share this email with anyone</li>
                        <li>This link will only work once</li>
                    </ul>
                </div>
                
                <p style="margin-top: 30px;">Best regards,<br><strong>The HomeGrubHub Security Team</strong></p>
            </div>
            <div class="footer">
                <p>This email was sent because a password reset was requested for your account.<br>
                Questions? Contact us at <a href="mailto:support@homegrubhub.co.uk">support@homegrubhub.co.uk</a></p>
            </div>
        </body>
        </html>
        """
    
    def _create_password_reset_text(self, user_name: str, reset_link: str, expires_in_hours: int) -> str:
        """Create plain text content for password reset email"""
        return f"""
Password Reset Request

Hi {user_name},

We received a request to reset your HomeGrubHub password. If you made this request, visit this link to reset your password:

{reset_link}

IMPORTANT: This link will expire in {expires_in_hours} hours for security reasons.

Security Notice:
• If you didn't request this reset, you can safely ignore this email
• Your password will not be changed unless you click the link above  
• Never share this email with anyone
• This link will only work once

Best regards,
The HomeGrubHub Security Team

---
This email was sent because a password reset was requested for your account.
Questions? Contact us at support@homegrubhub.co.uk
        """
    
    def _create_billing_notification_content(self, notification_type: str, user_name: str, 
                                           amount: float = None, subscription_plan: str = None) -> tuple:
        """Create content for billing notifications"""
        
        if notification_type == "payment_success":
            subject = "Payment Confirmed - HomeGrubHub"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Payment Confirmation</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #28a745; color: white; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background-color: #ffffff; padding: 30px 20px; border: 1px solid #dee2e6; }}
                    .amount {{ font-size: 32px; font-weight: bold; color: #28a745; text-align: center; margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; }}
                    .details {{ background-color: #e8f5e8; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 14px; color: #6c757d; border-radius: 0 0 8px 8px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1 style="margin: 0; font-size: 28px;">✅ Payment Confirmed</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Thank you for your payment</p>
                </div>
                <div class="content">
                    <h2 style="color: #28a745;">Hi {user_name},</h2>
                    <p>Your payment has been successfully processed! Thank you for continuing your HomeGrubHub subscription.</p>
                    
                    <div class="amount">£{amount:.2f}</div>
                    
                    <div class="details">
                        <h3 style="color: #28a745; margin-top: 0;">Payment Details:</h3>
                        <p><strong>Plan:</strong> {subscription_plan}</p>
                        <p><strong>Amount:</strong> £{amount:.2f}</p>
                        <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                        <p><strong>Status:</strong> Paid ✅</p>
                    </div>
                    
                    <p>Your subscription is now active and you have full access to all HomeGrubHub features.</p>
                    
                    <p style="margin-top: 30px;">Thank you for your continued support!<br><strong>The HomeGrubHub Team</strong></p>
                </div>
                <div class="footer">
                    <p>Questions about your billing? Contact us at <a href="mailto:support@homegrubhub.co.uk">support@homegrubhub.co.uk</a></p>
                </div>
            </body>
            </html>
            """
            text_content = f"""
Payment Confirmed

Hi {user_name},

Your payment has been successfully processed! Thank you for continuing your HomeGrubHub subscription.

Payment Details:
• Plan: {subscription_plan}
• Amount: £{amount:.2f}
• Date: {datetime.now().strftime('%B %d, %Y')}
• Status: Paid ✅

Your subscription is now active and you have full access to all HomeGrubHub features.

Thank you for your continued support!
The HomeGrubHub Team

---
Questions about your billing? Contact us at support@homegrubhub.co.uk
            """
        
        elif notification_type == "trial_ending":
            subject = "Your HomeGrubHub Trial Ends Soon"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Trial Ending Soon</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #ffc107; color: #212529; padding: 30px 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background-color: #ffffff; padding: 30px 20px; border: 1px solid #dee2e6; }}
                    .button {{ display: inline-block; background-color: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
                    .features {{ background-color: #fff8e1; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 14px; color: #6c757d; border-radius: 0 0 8px 8px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1 style="margin: 0; font-size: 28px;">⏰ Trial Ending Soon</h1>
                    <p style="margin: 10px 0 0 0; font-size: 16px;">Don't lose access to your recipes!</p>
                </div>
                <div class="content">
                    <h2 style="color: #f57c00;">Hi {user_name},</h2>
                    <p>Your HomeGrubHub trial is ending soon! We hope you've enjoyed discovering new recipes and planning your meals with us.</p>
                    
                    <div class="features">
                        <h3 style="color: #f57c00; margin-top: 0;">Don't lose access to:</h3>
                        <ul style="margin: 0; padding-left: 20px;">
                            <li><strong>Unlimited recipes</strong> - Access our full recipe database</li>
                            <li><strong>Smart meal planning</strong> - Plan weeks in advance</li>
                            <li><strong>Automated shopping lists</strong> - Never forget ingredients</li>
                            <li><strong>Nutrition tracking</strong> - Monitor your health goals</li>
                            <li><strong>Recipe collections</strong> - Organize your favorites</li>
                        </ul>
                    </div>
                    
                    <p>Continue your culinary journey with HomeGrubHub:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="https://homegrubhub.co.uk/billing/upgrade" class="button">Continue Subscription</a>
                    </div>
                    
                    <p style="font-size: 14px; color: #666;">Plans start from just £4.99/month. Cancel anytime.</p>
                </div>
                <div class="footer">
                    <p>Questions? Contact us at <a href="mailto:support@homegrubhub.co.uk">support@homegrubhub.co.uk</a></p>
                </div>
            </body>
            </html>
            """
            text_content = f"""
Trial Ending Soon

Hi {user_name},

Your HomeGrubHub trial is ending soon! We hope you've enjoyed discovering new recipes and planning your meals with us.

Don't lose access to:
• Unlimited recipes - Access our full recipe database
• Smart meal planning - Plan weeks in advance  
• Automated shopping lists - Never forget ingredients
• Nutrition tracking - Monitor your health goals
• Recipe collections - Organize your favorites

Continue your culinary journey: https://homegrubhub.co.uk/billing/upgrade

Plans start from just £4.99/month. Cancel anytime.

Questions? Contact us at support@homegrubhub.co.uk
            """
        
        else:
            # Default/fallback content
            subject = "HomeGrubHub Account Update"
            html_content = f"<p>Hi {user_name},</p><p>There's an update on your HomeGrubHub account.</p>"
            text_content = f"Hi {user_name},\n\nThere's an update on your HomeGrubHub account."
        
        return subject, html_content, text_content
    
    def test_connection(self) -> bool:
        """Test SendGrid API connection"""
        if not self._is_configured():
            return False
        
        try:
            # Test with a simple API call to get account details
            response = self.client.user.get()
            return response.status_code == 200
        except Exception as e:
            logger.error(f"SendGrid connection test failed: {e}")
            return False


# Global instance
sendgrid_service = SendGridEmailService()

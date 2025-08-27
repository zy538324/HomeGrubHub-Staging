"""
Email verification and password reset routes
Handles user registration confirmation and password reset functionality using SendGrid
"""

from flask import Blueprint, request, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user, login_user, logout_user
from recipe_app.db import db
from recipe_app.models.models import User
from recipe_app.utils.sendgrid_service import sendgrid_service
import logging

# Create blueprint
email_bp = Blueprint('email', __name__, url_prefix='/email')

logger = logging.getLogger(__name__)

@email_bp.route('/verify/<token>')
def verify_email(token):
    """Verify user email address with token"""
    try:
        user = User.query.filter_by(email_verification_token=token).first()
        
        if not user:
            flash('Invalid or expired verification link.', 'error')
            return redirect(url_for('auth.login'))
        
        if user.verify_email(token):
            db.session.commit()
            
            flash('Your email has been verified! Welcome to HomeGrubHub.', 'success')
            
            # Log the user in if they're not already logged in
            if not current_user.is_authenticated:
                login_user(user)
                return redirect(url_for('main.dashboard'))
            else:
                return redirect(url_for('main.profile'))
        else:
            flash('Email verification failed. Please try again.', 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        logger.error(f"Error verifying email: {e}")
        flash('An error occurred during email verification.', 'error')
        return redirect(url_for('auth.login'))

@email_bp.route('/resend-verification', methods=['POST'])
@login_required
def resend_verification():
    """Resend email verification for current user"""
    try:
        if current_user.email_verified:
            flash('Your email is already verified.', 'info')
            return redirect(url_for('main.profile'))
        
        # Generate new verification token
        token = current_user.generate_email_verification_token()
        db.session.commit()
        
        # Send verification email
        verification_link = url_for('email.verify_email', token=token, _external=True)
        success = sendgrid_service.send_registration_confirmation(
            current_user.email,
            current_user.username,
            verification_link
        )
        
        if success:
            flash('Verification email sent! Please check your inbox.', 'success')
        else:
            flash('Failed to send verification email. Please try again later.', 'error')
            
    except Exception as e:
        logger.error(f"Error resending verification: {e}")
        flash('An error occurred. Please try again later.', 'error')
    
    return redirect(url_for('main.profile'))

@email_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset"""
    if request.method == 'GET':
        return render_template('auth/forgot_password.html')
    
    try:
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address.', 'error')
            return render_template('auth/forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate password reset token
            token = user.generate_password_reset_token()
            db.session.commit()
            
            # Send password reset email
            reset_link = url_for('email.reset_password', token=token, _external=True)
            success = sendgrid_service.send_password_reset(
                user.email,
                user.username,
                reset_link,
                expires_in_hours=24
            )
            
            if success:
                flash('Password reset instructions sent to your email.', 'success')
            else:
                flash('Failed to send reset email. Please try again later.', 'error')
        else:
            # Don't reveal if email exists or not for security
            flash('If that email address is in our system, you will receive password reset instructions.', 'info')
        
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        logger.error(f"Error in forgot password: {e}")
        flash('An error occurred. Please try again later.', 'error')
        return render_template('auth/forgot_password.html')

@email_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password with token"""
    try:
        user = User.query.filter_by(password_reset_token=token).first()
        
        if not user:
            flash('Invalid or expired reset link.', 'error')
            return redirect(url_for('email.forgot_password'))
        
        # Check if token is not too old (24 hours)
        from datetime import datetime
        if user.password_reset_sent_at and \
           (datetime.utcnow() - user.password_reset_sent_at).total_seconds() > 86400:
            flash('Reset link has expired. Please request a new one.', 'error')
            return redirect(url_for('email.forgot_password'))
        
        if request.method == 'GET':
            return render_template('auth/reset_password.html', token=token)
        
        # Handle POST request
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        # Reset password
        if user.reset_password_with_token(token, password):
            db.session.commit()
            flash('Your password has been reset successfully. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Failed to reset password. Please try again.', 'error')
            return redirect(url_for('email.forgot_password'))
            
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        flash('An error occurred. Please try again later.', 'error')
        return redirect(url_for('email.forgot_password'))

@email_bp.route('/test-sendgrid')
@login_required
def test_sendgrid():
    """Test SendGrid connection (admin only)"""
    if not current_user.is_admin:
        flash('Access denied.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Test connection
        connection_ok = sendgrid_service.test_connection()
        
        test_results = []
        test_results.append(f"SendGrid API: {'✅ Connected' if connection_ok else '❌ Failed'}")
        
        # Test sending a welcome email to admin
        if connection_ok:
            success = sendgrid_service.send_welcome_email(
                current_user.email,
                current_user.username
            )
            test_results.append(f"Test Email Send: {'✅ Sent' if success else '❌ Failed'}")
        
        flash(f"SendGrid Test Results: {', '.join(test_results)}", 'info')
        
    except Exception as e:
        logger.error(f"Error testing SendGrid: {e}")
        flash(f'SendGrid test failed: {str(e)}', 'error')
    
    return redirect(url_for('main.admin'))

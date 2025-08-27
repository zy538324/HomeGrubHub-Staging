from flask import Blueprint, redirect, url_for, session, current_app, request
from authlib.integrations.flask_client import OAuth
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from configs.auth0_config import (
    AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_DOMAIN, AUTH0_CALLBACK_URL
)

# Blueprint for Auth0
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/auth/login')
def login():
    auth0 = current_app.auth0
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL)

@auth_bp.route('/callback')
def callback_handling():
    auth0 = current_app.auth0
    token = auth0.authorize_access_token()
    userinfo = auth0.parse_id_token(token)
    from recipe_app.models.models import User, db
    from recipe_app.utils.sendgrid_service import sendgrid_service
    from flask_login import login_user
    import logging
    
    logger = logging.getLogger(__name__)
    
    email = userinfo.get('email')
    user = User.query.filter_by(email=email).first()
    
    is_new_user = False
    if not user:
        # Create a new user with Auth0 info
        is_new_user = True
        user = User(
            username=userinfo.get('name') or email.split('@')[0],
            email=email,
            is_active=True,
            current_plan='Free',  # Default plan
            email_verified=True  # Auth0 handles email verification
        )
        db.session.add(user)
        db.session.commit()
        
        # Send welcome email for new users
        try:
            # Send welcome email (since Auth0 handles email verification)
            sendgrid_service.send_welcome_email(
                user.email, 
                user.username
            )
            logger.info(f"Welcome email sent to new user {email}")
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to new user {email}: {e}")
    
    login_user(user)
    session['user'] = userinfo
    
    # Redirect new users to a welcome/onboarding page, existing users to dashboard
    if is_new_user:
        return redirect(url_for('main.welcome'))  # Create this route for onboarding
    else:
        return redirect(url_for('main.dashboard'))

@auth_bp.route('/auth/logout')
def logout():
    from flask_login import logout_user
    logout_user()  # Log out from Flask-Login
    session.clear()
    
    # Construct Auth0 logout URL explicitly
    auth0_domain = current_app.config.get('AUTH0_DOMAIN', AUTH0_DOMAIN)
    # Try different return URLs that might be allowed
    possible_return_urls = [
        'https://homegrubhub.co.uk/',
        'http://homegrubhub.co.uk/',
        'http://127.0.0.1:8052/',
        'http://localhost:8052/',
        'https://www.homegrubhub.co.uk/'
    ]
    
    # Use the first URL for now, but we need to configure it in Auth0
    return_url = 'https://homegrubhub.co.uk/'
    
    # Make sure we redirect to Auth0, not local domain
    auth0_logout_url = f'https://{auth0_domain}/v2/logout?returnTo={return_url}'
    
    # Debug logging
    current_app.logger.info(f"Auth0 logout URL: {auth0_logout_url}")
    
    # Try JavaScript redirect instead of server redirect to bypass any URL rewriting
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Logging out...</title>
        <script>
            // Try the Auth0 logout, if it fails, redirect to home
            window.location.href = "{auth0_logout_url}";
        </script>
    </head>
    <body>
        <p>Logging out... If you're not redirected automatically, <a href="/">click here to go home</a>.</p>
        <p>Auth0 logout URL: <a href="{auth0_logout_url}">{auth0_logout_url}</a></p>
    </body>
    </html>
    '''

@auth_bp.route('/logout')
def simple_logout():
    """Simple logout that doesn't use Auth0 logout endpoint"""
    from flask_login import logout_user
    logout_user()
    session.clear()
    
    # Just redirect to home page without Auth0 logout
    return redirect('https://homegrubhub.co.uk/')

@auth_bp.route('/auth/logout-simple')
def simple_auth_logout():
    """Alternative logout that bypasses Auth0 logout endpoint"""
    from flask_login import logout_user
    logout_user()
    session.clear()
    
    return redirect('https://homegrubhub.co.uk/')

@auth_bp.route('/test-auth0')
def test_auth0():
    """Test route to check Auth0 configuration"""
    auth0_domain = current_app.config.get('AUTH0_DOMAIN', AUTH0_DOMAIN)
    return_url = 'https://homegrubhub.co.uk/'
    auth0_logout_url = f'https://{auth0_domain}/v2/logout?returnTo={return_url}'
    
    return f'''
    <h2>Auth0 Configuration Test</h2>
    <p><strong>AUTH0_DOMAIN from config:</strong> {current_app.config.get('AUTH0_DOMAIN')}</p>
    <p><strong>AUTH0_DOMAIN from import:</strong> {AUTH0_DOMAIN}</p>
    <p><strong>Final auth0_domain:</strong> {auth0_domain}</p>
    <p><strong>Constructed logout URL:</strong> {auth0_logout_url}</p>
    <p><a href="/auth/logout">Test Logout (JavaScript redirect)</a></p>
    <p><a href="{auth0_logout_url}">Direct Auth0 Logout Link</a></p>
    '''

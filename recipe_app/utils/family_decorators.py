"""
Family decorators for access control and family membership verification
"""

from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def family_required(f):
    """
    Decorator to require user to be part of a family account.
    Redirects to family creation/join page if not in a family.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access family features.', 'error')
            return redirect(url_for('auth.login'))
        
        family = current_user.get_family_account()
        if not family:
            flash('You need to create or join a family account to access this feature.', 'info')
            return redirect(url_for('family.create_family'))
        
        return f(*args, **kwargs)
    return decorated_function


def family_admin_required(f):
    """
    Decorator to require user to be a family administrator.
    Only family creators (primary users) can access admin functions.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access family features.', 'error')
            return redirect(url_for('auth.login'))
        
        family = current_user.get_family_account()
        if not family:
            flash('You need to create or join a family account to access this feature.', 'info')
            return redirect(url_for('family.create_family'))
        
        if not current_user.is_family_admin():
            flash('You must be a family administrator to access this feature.', 'error')
            return redirect(url_for('family.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def family_parent_required(f):
    """
    Decorator to require user to be a parent or admin in the family.
    Used for parental control features and approval management.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access family features.', 'error')
            return redirect(url_for('auth.login'))
        
        family = current_user.get_family_account()
        if not family:
            flash('You need to create or join a family account to access this feature.', 'info')
            return redirect(url_for('family.create_family'))
        
        # Get current user's family role
        user_role = current_user.get_family_role()
        if user_role not in ['admin', 'parent']:
            flash('You must be a parent or family administrator to access this feature.', 'error')
            return redirect(url_for('family.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def family_member_access(member_id_param='member_id'):
    """
    Decorator to ensure user can only access their own family member data
    or data of family members they have permission to access (parents can access children).
    
    Args:
        member_id_param: Name of the parameter containing the member ID
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access family features.', 'error')
                return redirect(url_for('auth.login'))
            
            family = current_user.get_family_account()
            if not family:
                flash('You need to create or join a family account to access this feature.', 'info')
                return redirect(url_for('family.create_family'))
            
            # Get the member ID from the request parameters
            member_id = kwargs.get(member_id_param)
            if not member_id:
                abort(400, 'Member ID required')
            
            # Get current user's family member record
            current_member = next((m for m in family.members if m.user_id == current_user.id), None)
            if not current_member:
                abort(403, 'Access denied')
            
            # Get target member
            target_member = next((m for m in family.members if m.id == member_id), None)
            if not target_member:
                abort(404, 'Family member not found')
            
            # Check access permissions
            user_role = current_member.role
            
            # Family admins can access anyone
            if user_role == 'admin':
                return f(*args, **kwargs)
            
            # Users can access their own data
            if member_id == current_member.id:
                return f(*args, **kwargs)
            
            # Parents can access their children's data
            if user_role == 'parent' and target_member.role == 'child':
                return f(*args, **kwargs)
            
            # Otherwise, access denied
            flash('You do not have permission to access this family member\'s data.', 'error')
            return redirect(url_for('family.dashboard'))
        
        return decorated_function
    return decorator


def ensure_family_context(f):
    """
    Decorator that ensures family context is available in the view.
    Adds family and current_member objects to the function arguments.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access family features.', 'error')
            return redirect(url_for('auth.login'))
        
        family = current_user.get_family_account()
        if not family:
            flash('You need to create or join a family account to access this feature.', 'info')
            return redirect(url_for('family.create_family'))
        
        # Find current user's family member record
        current_member = next((m for m in family.members if m.user_id == current_user.id), None)
        if not current_member:
            flash('Family membership record not found.', 'error')
            return redirect(url_for('family.create_family'))
        
        # Add family context to kwargs
        kwargs['family'] = family
        kwargs['current_member'] = current_member
        
        return f(*args, **kwargs)
    return decorated_function


def check_parental_controls(f):
    """
    Decorator to check if child user is within parental control limits.
    Used to enforce screen time, content restrictions, etc.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return f(*args, **kwargs)  # Let other auth decorators handle this
        
        family = current_user.get_family_account()
        if not family:
            return f(*args, **kwargs)  # No family, no parental controls
        
        # Get current user's family member record
        current_member = next((m for m in family.members if m.user_id == current_user.id), None)
        if not current_member or current_member.role != 'child':
            return f(*args, **kwargs)  # Not a child, no restrictions
        
        # Check for parental controls
        from recipe_app.models.family_models import ParentalControl
        parental_controls = ParentalControl.query.filter_by(
            child_id=current_member.id,
            is_active=True
        ).first()
        
        if not parental_controls:
            return f(*args, **kwargs)  # No parental controls set
        
        # Check time restrictions
        if not parental_controls.is_within_allowed_hours():
            flash('This feature is not available during your current restricted hours.', 'warning')
            return redirect(url_for('family.dashboard'))
        
        # Check screen time limits (basic implementation)
        remaining_time = parental_controls.get_remaining_screen_time()
        if remaining_time is not None and remaining_time <= 0:
            flash('You have reached your screen time limit for today.', 'warning')
            return redirect(url_for('family.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

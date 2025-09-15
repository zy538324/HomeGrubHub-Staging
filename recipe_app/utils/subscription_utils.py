"""
Subscription enforcement utilities
Security decorators to enforce subscription tier restrictions
"""
from functools import wraps
from flask import jsonify, redirect, url_for, flash, request
from flask_login import current_user

from recipe_app.config.tiers import get_available_features


def require_subscription_feature(feature_name):
    """
    Decorator to require specific subscription feature access
    Redirects non-Pro users to upgrade page for Pro features
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this feature.', 'warning')
                return redirect(url_for('main.login'))
            
            if not current_user.can_access_feature(feature_name):
                # Check if it's an AJAX request
                if request.is_json or 'application/json' in request.headers.get('Accept', ''):
                    return jsonify({
                        'error': 'Subscription upgrade required',
                        'feature': feature_name,
                        'current_plan': current_user.current_plan,
                        'upgrade_url': url_for('billing.pricing'),
                        'message': f'This feature requires a higher subscription tier. Please upgrade to access {feature_name}.'
                    }), 403
                
                flash(f'This feature requires a Home subscription. Please upgrade to access {feature_name}.', 'warning')
                return redirect(url_for('billing.pricing'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_home_tier(f=None):
    """Decorator specifically for Home tier features"""
    if f is None:
        # Called with parentheses: @require_home_tier()
        return require_home_features()
    else:
        # Called without parentheses: @require_home_tier
        return require_home_features()(f)

def require_home_features():
    """Decorator for Home tier features"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this feature.', 'warning')
                return redirect(url_for('main.login'))
            
            if 'private_recipes' not in get_available_features(current_user.current_plan):
                if request.is_json or 'application/json' in request.headers.get('Accept', ''):
                    return jsonify({
                        'error': 'Home subscription required',
                        'current_plan': current_user.current_plan,
                        'upgrade_url': url_for('billing.pricing'),
                        'message': 'This feature requires a Home subscription.'
                    }), 403

                flash('This feature requires a Home subscription.', 'warning')
                return redirect(url_for('billing.pricing'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_barcode_scanning():
    """Decorator specifically for barcode scanning features"""
    return require_subscription_feature('barcode_scanning')


def require_advanced_nutrition():
    """Decorator for advanced nutrition features"""
    return require_subscription_feature('nutrition_analysis')


def require_family_tier():
    """Decorator for Family tier and above features"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this feature.', 'warning')
                return redirect(url_for('main.login'))
            
            if 'family_sharing' not in get_available_features(current_user.current_plan):
                if request.is_json or 'application/json' in request.headers.get('Accept', ''):
                    return jsonify({
                        'error': 'Family subscription required',
                        'current_plan': current_user.current_plan,
                        'upgrade_url': url_for('billing.pricing'),
                        'message': 'This feature requires a Family or Pro subscription.'
                    }), 403
                
                flash('This feature requires a Family or Pro subscription.', 'warning')
                return redirect(url_for('billing.pricing'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Updated to support both usages: @require_pro_tier and @require_pro_tier()
def require_pro_tier(f=None):
    """Decorator specifically for Pro tier features"""
    if f is None:
        # Called with parentheses: @require_pro_tier()
        return require_subscription_feature('pantry_tracker_predictive')
    else:
        # Called without parentheses: @require_pro_tier
        return require_subscription_feature('pantry_tracker_predictive')(f)


def check_recipe_limit(f):
    """
    Decorator to enforce recipe limits for Free tier users
    Free users are limited to 10 public recipes
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return f(*args, **kwargs)
        
        # Only check for Free tier users
        if current_user.current_plan == 'Free':
            from recipe_app.models.models import Recipe
            user_recipe_count = Recipe.query.filter_by(
                user_id=current_user.id,
                is_private=False  # Count public recipes only
            ).count()
            
            if user_recipe_count >= 10:
                if request.is_json or 'application/json' in request.headers.get('Accept', ''):
                    return jsonify({
                        'error': 'Recipe limit reached',
                        'current_plan': 'Free',
                        'recipe_limit': 10,
                        'current_count': user_recipe_count,
                        'upgrade_url': url_for('billing.pricing'),
                        'message': 'Free accounts are limited to 10 public recipes. Please upgrade for unlimited recipes.'
                    }), 403
                
                flash('Free accounts are limited to 10 public recipes. Please upgrade for unlimited recipes.', 'warning')
                return redirect(url_for('billing.pricing'))
        
        return f(*args, **kwargs)
    return decorated_function


def get_user_subscription_tier():
    """Get the current user's subscription tier"""
    if not current_user.is_authenticated:
        return 'Guest'
    return current_user.current_plan


def subscription_info_context():
    """
    Template context processor to provide subscription information
    """
    if current_user.is_authenticated:
        features = get_available_features(current_user.current_plan)
        return {
            'user_plan': current_user.current_plan,
            'has_home_features': 'private_recipes' in features,
            'has_family_features': 'family_sharing' in features,
            'has_pro_features': 'advanced_analytics' in features,
            'has_barcode_scanning': 'barcode_scanning' in features,
            'has_multi_store_comparison': 'multi_store_price_comparison' in features,
            'has_smart_forecasting': 'smart_consumption_forecasting' in features,
            'recipe_limit_reached': _check_recipe_limit_status()
        }
    return {
        'user_plan': None,
        'has_home_features': False,
        'has_family_features': False,
        'has_pro_features': False,
        'has_barcode_scanning': False,
        'has_multi_store_comparison': False,
        'has_smart_forecasting': False,
        'recipe_limit_reached': False
    }


def _check_recipe_limit_status():
    """Check if Free tier user has reached recipe limit"""
    if not current_user.is_authenticated or current_user.current_plan != 'Free':
        return False
    
    from recipe_app.models.models import Recipe
    user_recipe_count = Recipe.query.filter_by(
        user_id=current_user.id,
        is_private=False
    ).count()
    
    return user_recipe_count >= 10

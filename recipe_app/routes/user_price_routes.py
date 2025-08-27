"""
User Price Submission Routes
Legal and community-driven price sharing system
"""
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
import json

from recipe_app.db import db
from recipe_app.utils.user_price_service import user_price_service
from recipe_app.utils.postcode_service import postcode_service

user_prices_bp = Blueprint('user_prices', __name__)

@user_prices_bp.route('/prices/submit', methods=['GET', 'POST'])
@login_required
def submit_price():
    """Price submission form and handler"""
    
    if request.method == 'POST':
        # Handle form submission
        price_data = {
            'shop_name': request.form.get('shop_name', '').strip(),
            'brand_name': request.form.get('brand_name', '').strip(),
            'item_name': request.form.get('item_name', '').strip(),
            'size': request.form.get('size', '').strip(),
            'price': request.form.get('price', '').strip(),
            'shop_location': request.form.get('shop_location', '').strip()
        }
        
        # Submit price
        success, message, price_id = user_price_service.submit_price(current_user.id, price_data)
        
        if success:
            flash(f'Thank you! Your price has been submitted and will help other users.', 'success')
            return redirect(url_for('user_prices.submit_price'))
        else:
            flash(f'Error: {message}', 'error')
    
    return render_template('prices/submit_price.html')

@user_prices_bp.route('/api/prices/submit', methods=['POST'])
@login_required
def api_submit_price():
    """API endpoint for price submission"""
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Submit price
        success, message, price_id = user_price_service.submit_price(current_user.id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'price_id': price_id
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@user_prices_bp.route('/api/prices/item/<path:item_name>')
def get_item_prices(item_name):
    """Get user-contributed prices for an item"""
    
    # Get user's postcode for location-based filtering
    user_postcode = request.args.get('postcode')
    if not user_postcode and current_user.is_authenticated:
        user_postcode = getattr(current_user, 'postcode', None)
    
    # Get prices
    prices = user_price_service.get_prices_for_item(item_name, user_postcode)
    
    if prices:
        return jsonify({
            'success': True,
            'item_name': item_name,
            'prices': prices,
            'total_found': len(prices),
            'data_source': 'User-contributed prices',
            'user_postcode': user_postcode
        })
    else:
        return jsonify({
            'success': False,
            'item_name': item_name,
            'prices': [],
            'total_found': 0,
            'message': 'This item is not priced yet. Be the first to contribute a price!',
            'data_source': 'No data available',
            'user_postcode': user_postcode
        })

@user_prices_bp.route('/api/prices/verify/<int:price_id>', methods=['POST'])
@login_required
def verify_price(price_id):
    """Verify the accuracy of a submitted price"""
    
    try:
        data = request.get_json()
        is_accurate = data.get('is_accurate', False)
        comment = data.get('comment', '')
        
        success, message = user_price_service.verify_price(
            current_user.id, 
            price_id, 
            is_accurate, 
            comment
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@user_prices_bp.route('/api/postcode/lookup/<postcode>')
def lookup_postcode(postcode):
    """Lookup postcode information"""
    
    if not postcode_service.validate_postcode(postcode):
        return jsonify({
            'success': False,
            'error': 'Invalid postcode format'
        }), 400
    
    data = postcode_service.lookup_postcode(postcode)
    
    if data:
        return jsonify({
            'success': True,
            'postcode_data': data
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Postcode not found'
        }), 404

@user_prices_bp.route('/prices/browse')
def browse_prices():
    """Browse submitted prices by item"""
    
    # Get search parameters
    search_item = request.args.get('item', '')
    postcode = request.args.get('postcode', '')
    
    prices = []
    if search_item:
        prices = user_price_service.get_prices_for_item(search_item, postcode)
    
    return render_template('prices/browse_prices.html', 
                         prices=prices, 
                         search_item=search_item,
                         postcode=postcode)

@user_prices_bp.route('/prices/my-submissions')
@login_required
def my_submissions():
    """View user's own price submissions"""
    
    from recipe_app.models.user_price_models import UserContributedPrice
    
    user_prices = UserContributedPrice.query.filter_by(
        submitted_by=current_user.id
    ).order_by(UserContributedPrice.submitted_at.desc()).limit(50).all()
    
    submissions = []
    for price in user_prices:
        submissions.append({
            'id': price.id,
            'item_name': price.item_name,
            'shop_name': price.shop_name,
            'price': float(price.price),
            'shop_location': price.shop_location,
            'submitted_at': price.submitted_at,
            'is_verified': price.is_verified,
            'verification_count': price.verification_count
        })
    
    return render_template('prices/my_submissions.html', submissions=submissions)

@user_prices_bp.route('/api/prices/bulk-update', methods=['POST'])
@login_required
def bulk_update_shopping_list_prices():
    """Update shopping list items with user-contributed prices"""
    
    try:
        data = request.get_json()
        shopping_list_id = data.get('shopping_list_id')
        
        from recipe_app.models.advanced_models import ShoppingListItem
        
        # Get shopping list items without prices
        query = ShoppingListItem.query.filter_by(
            user_id=current_user.id, 
            is_purchased=False
        )
        
        if shopping_list_id:
            query = query.filter_by(shopping_list_id=shopping_list_id)
        
        items = query.filter(
            ShoppingListItem.estimated_price.is_(None)
        ).all()
        
        updated_count = 0
        not_found_count = 0
        user_postcode = getattr(current_user, 'postcode', None)
        
        for item in items:
            # Get best price for this item
            best_price = user_price_service.get_best_price_for_item(item.name, user_postcode)
            
            if best_price:
                item.estimated_price = best_price['price']
                # Add metadata to indicate this is user-contributed
                item.notes = f"Price from {best_price['shop_name']} (user-contributed)"
                updated_count += 1
            else:
                not_found_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'not_found_count': not_found_count,
            'message': f"Updated {updated_count} items with user-contributed prices. {not_found_count} items not priced yet.",
            'data_source': 'User-contributed prices'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

# Admin routes disabled - moved to separate admin webapp
# @user_prices_bp.route('/admin/prices/recent')
# @login_required
# def admin_recent_prices():
#     """Admin view moved to separate admin application"""
#     flash('Admin features have been moved to a separate admin portal.', 'info')
#     return redirect(url_for('main.dashboard'))

@user_prices_bp.route('/api/prices/stats')
def price_stats():
    """Get statistics about user-contributed prices"""
    
    from recipe_app.models.user_price_models import UserContributedPrice
    from sqlalchemy import func
    
    try:
        # Total prices
        total_prices = UserContributedPrice.query.count()
        
        # Verified prices
        verified_prices = UserContributedPrice.query.filter_by(is_verified=True).count()
        
        # Unique items
        unique_items = db.session.query(
            func.count(func.distinct(UserContributedPrice.normalized_item_name))
        ).scalar()
        
        # Unique shops
        unique_shops = db.session.query(
            func.count(func.distinct(UserContributedPrice.normalized_shop_name))
        ).scalar()
        
        # Recent submissions (last 7 days)
        from datetime import timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_submissions = UserContributedPrice.query.filter(
            UserContributedPrice.submitted_at >= week_ago
        ).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_prices': total_prices,
                'verified_prices': verified_prices,
                'unique_items': unique_items,
                'unique_shops': unique_shops,
                'recent_submissions': recent_submissions,
                'verification_rate': round((verified_prices / total_prices * 100), 1) if total_prices > 0 else 0
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

"""
Shop Management Routes - Admin only
Manages the list of stores that users can contribute prices for
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime

from recipe_app.db import db
from recipe_app.models.user_price_models import ShopLocation, PriceDataSanitizer
from recipe_app.utils.postcode_service import postcode_service

shop_management_bp = Blueprint('shop_management', __name__)

def admin_redirect():
    """Redirect admin requests to user dashboard with notice"""
    flash('Admin features have been moved to a separate admin portal.', 'info')
    return redirect(url_for('main.dashboard'))

@shop_management_bp.route('/admin/shops')
@login_required
def admin_shops():
    """Admin page moved to separate admin application"""
    return admin_redirect()
    shops = ShopLocation.query.order_by(
        ShopLocation.chain_name.asc(),
        ShopLocation.shop_name.asc()
    ).all()
    
    # Group by chain for better display
    shops_by_chain = {}
    for shop in shops:
        chain = shop.chain_name or 'Independent Stores'
        if chain not in shops_by_chain:
            shops_by_chain[chain] = []
        shops_by_chain[chain].append({
            'id': shop.id,
            'shop_name': shop.shop_name,
            'address_line': shop.address_line,
            'postcode': shop.postcode,
            'store_type': shop.store_type,
            'verified': shop.verified,
            'created_at': shop.created_at.strftime('%Y-%m-%d')
        })
    
    return render_template('admin/shop_management.html', shops_by_chain=shops_by_chain)

@shop_management_bp.route('/admin/shops/add', methods=['POST'])
@login_required
def add_shop():
    """Add a new shop location (Admin only)"""
    
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['shop_name', 'address_line', 'postcode']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate and normalize postcode
        postcode = data['postcode'].strip().upper()
        if not postcode_service.validate_postcode(postcode):
            return jsonify({
                'success': False,
                'error': 'Invalid postcode format'
            }), 400
        
        normalized_postcode = postcode_service.normalize_postcode(postcode)
        
        # Look up postcode data
        postcode_data = postcode_service.lookup_postcode(normalized_postcode)
        if not postcode_data:
            return jsonify({
                'success': False,
                'error': 'Could not verify postcode'
            }), 400
        
        # Check if shop already exists at this location
        existing = ShopLocation.query.filter_by(
            normalized_shop_name=PriceDataSanitizer.normalize_shop_name(data['shop_name']),
            postcode=normalized_postcode
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'error': 'This shop already exists at this location'
            }), 400
        
        # Create new shop
        new_shop = ShopLocation(
            shop_name=data['shop_name'].strip(),
            normalized_shop_name=PriceDataSanitizer.normalize_shop_name(data['shop_name']),
            address_line=data['address_line'].strip(),
            postcode=normalized_postcode,
            postcode_area=postcode_data['postcode_area'],
            latitude=postcode_data.get('latitude'),
            longitude=postcode_data.get('longitude'),
            town=postcode_data.get('town'),
            county=postcode_data.get('county'),
            region=postcode_data.get('region'),
            chain_name=data.get('chain_name', '').strip() or None,
            store_type=data.get('store_type', '').strip() or None,
            verified=True,  # Admin-added shops are automatically verified
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_shop)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Shop added successfully',
            'shop_id': new_shop.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@shop_management_bp.route('/admin/shops/<int:shop_id>/edit', methods=['POST'])
@login_required
def edit_shop(shop_id):
    """Edit an existing shop (Admin only)"""
    
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        shop = ShopLocation.query.get_or_404(shop_id)
        data = request.get_json()
        
        # Update fields
        if 'shop_name' in data:
            shop.shop_name = data['shop_name'].strip()
            shop.normalized_shop_name = PriceDataSanitizer.normalize_shop_name(data['shop_name'])
        
        if 'address_line' in data:
            shop.address_line = data['address_line'].strip()
        
        if 'chain_name' in data:
            shop.chain_name = data['chain_name'].strip() or None
        
        if 'store_type' in data:
            shop.store_type = data['store_type'].strip() or None
        
        if 'verified' in data:
            shop.verified = bool(data['verified'])
        
        # If postcode changed, re-lookup location data
        if 'postcode' in data:
            new_postcode = data['postcode'].strip().upper()
            if not postcode_service.validate_postcode(new_postcode):
                return jsonify({
                    'success': False,
                    'error': 'Invalid postcode format'
                }), 400
            
            normalized_postcode = postcode_service.normalize_postcode(new_postcode)
            postcode_data = postcode_service.lookup_postcode(normalized_postcode)
            
            if postcode_data:
                shop.postcode = normalized_postcode
                shop.postcode_area = postcode_data['postcode_area']
                shop.latitude = postcode_data.get('latitude')
                shop.longitude = postcode_data.get('longitude')
                shop.town = postcode_data.get('town')
                shop.county = postcode_data.get('county')
                shop.region = postcode_data.get('region')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Shop updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@shop_management_bp.route('/admin/shops/<int:shop_id>/delete', methods=['DELETE'])
@login_required
def delete_shop(shop_id):
    """Delete a shop (Admin only)"""
    
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        shop = ShopLocation.query.get_or_404(shop_id)
        
        # Check if shop has associated price data
        from recipe_app.models.user_price_models import UserContributedPrice
        price_count = UserContributedPrice.query.filter_by(
            normalized_shop_name=shop.normalized_shop_name,
            postcode=shop.postcode
        ).count()
        
        if price_count > 0:
            return jsonify({
                'success': False,
                'error': f'Cannot delete shop with {price_count} associated price entries'
            }), 400
        
        db.session.delete(shop)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Shop deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@shop_management_bp.route('/api/shops/search')
def search_shops():
    """Search for shops (for price submission dropdowns)"""
    
    query = request.args.get('q', '').strip()
    postcode = request.args.get('postcode', '').strip()
    
    # Base query
    shops_query = ShopLocation.query.filter(
        ShopLocation.verified == True
    )
    
    # Filter by search term
    if query:
        shops_query = shops_query.filter(
            ShopLocation.shop_name.ilike(f'%{query}%')
        )
    
    # Filter by postcode area if provided
    if postcode:
        postcode_area = PriceDataSanitizer.extract_postcode_area(postcode)
        if postcode_area:
            shops_query = shops_query.filter(
                ShopLocation.postcode_area == postcode_area
            )
    
    # Get results
    shops = shops_query.order_by(
        ShopLocation.chain_name.asc(),
        ShopLocation.shop_name.asc()
    ).limit(20).all()
    
    results = []
    for shop in shops:
        results.append({
            'id': shop.id,
            'shop_name': shop.shop_name,
            'address_line': shop.address_line,
            'postcode': shop.postcode,
            'chain_name': shop.chain_name,
            'store_type': shop.store_type,
            'full_name': f"{shop.shop_name} - {shop.address_line}"
        })
    
    return jsonify({
        'success': True,
        'shops': results,
        'total_found': len(results)
    })

@shop_management_bp.route('/api/shops/suggest', methods=['POST'])
@login_required
def suggest_shop():
    """Allow users to suggest new shops for admin approval"""
    
    try:
        data = request.get_json()
        
        # For now, we'll store suggestions in the same table but mark as unverified
        # Later you could create a separate "shop_suggestions" table
        
        required_fields = ['shop_name', 'address_line', 'postcode']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate postcode
        postcode = data['postcode'].strip().upper()
        if not postcode_service.validate_postcode(postcode):
            return jsonify({
                'success': False,
                'error': 'Invalid postcode format'
            }), 400
        
        normalized_postcode = postcode_service.normalize_postcode(postcode)
        postcode_data = postcode_service.lookup_postcode(normalized_postcode)
        
        # Create suggestion (unverified)
        suggestion = ShopLocation(
            shop_name=data['shop_name'].strip(),
            normalized_shop_name=PriceDataSanitizer.normalize_shop_name(data['shop_name']),
            address_line=data['address_line'].strip(),
            postcode=normalized_postcode,
            postcode_area=postcode_data['postcode_area'] if postcode_data else PriceDataSanitizer.extract_postcode_area(normalized_postcode),
            latitude=postcode_data.get('latitude') if postcode_data else None,
            longitude=postcode_data.get('longitude') if postcode_data else None,
            town=postcode_data.get('town') if postcode_data else None,
            county=postcode_data.get('county') if postcode_data else None,
            region=postcode_data.get('region') if postcode_data else None,
            chain_name=data.get('chain_name', '').strip() or None,
            store_type=data.get('store_type', '').strip() or None,
            verified=False,  # Requires admin approval
            created_at=datetime.utcnow()
        )
        
        db.session.add(suggestion)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Shop suggestion submitted for admin approval',
            'suggestion_id': suggestion.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

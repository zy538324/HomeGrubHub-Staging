"""
Routes for Barcode Scanning and Photo Upload - Pro Tier Features
Security: Enforces subscription requirements for premium features
"""

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import login_required, current_user
from recipe_app.utils.subscription_utils import require_barcode_scanning
from recipe_app.utils.barcode_scanner import BarcodeScanner
from recipe_app.utils.photo_upload import PhotoUploadService
from recipe_app.utils.nutrition_calculator import NutritionCalculator
from recipe_app.models.models import Recipe, db
from recipe_app.models.advanced_models import ScannedProduct
from recipe_app.models.pantry_models import ShoppingListItem, WeeklyShoppingItem, WeeklyShoppingList
from datetime import datetime
import json

# Create blueprint
scanner_upload_bp = Blueprint('scanner_upload', __name__)

# Initialize services
barcode_scanner = BarcodeScanner()

@scanner_upload_bp.route('/barcode-scanner')
@login_required
@require_barcode_scanning()
def barcode_scanner_page():
    """
    Barcode scanner page with camera access
    SECURED: Home tier subscription required
    """
    return render_template('barcode_scanner.html')

@scanner_upload_bp.route('/api/barcode/<barcode>')
@login_required
@require_barcode_scanning()
def get_barcode_data(barcode):
    """
    API endpoint to get product data from barcode
    SECURED: Home tier subscription required
    """
    try:
        product_data = barcode_scanner.get_product_by_barcode(barcode)
        
        if product_data:
            return jsonify({
                'success': True,
                'product': product_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Product not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scanner_upload_bp.route('/api/search-products')
@login_required
@require_barcode_scanning()
def search_products():
    """
    Search for products by name
    SECURED: Home tier subscription required
    """
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Search query is required'
        }), 400
    
    try:
        results = barcode_scanner.search_products_by_name(query)
        return jsonify({
            'success': True,
            'products': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scanner_upload_bp.route('/api/upload-recipe-photo/<int:recipe_id>', methods=['POST'])
@login_required
def upload_recipe_photo(recipe_id):
    """
    Upload photo for recipe - Available to all users
    """
    recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    
    if not recipe:
        return jsonify({
            'success': False,
            'error': 'Recipe not found'
        }), 404
    
    if 'photo' not in request.files:
        return jsonify({
            'success': False,
            'error': 'No photo file provided'
        }), 400
    
    file = request.files['photo']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'error': 'No file selected'
        }), 400
    
    try:
        photo_service = PhotoUploadService()
        photo_url = photo_service.upload_recipe_photo(file, recipe_id)
        
        # Update recipe with photo URL
        recipe.image_url = photo_url
        db.session.commit()
        
        return jsonify({
            'success': True,
            'photo_url': photo_url,
            'message': 'Photo uploaded successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scanner_upload_bp.route('/api/delete-recipe-photo/<int:recipe_id>', methods=['DELETE'])
@login_required
def delete_recipe_photo(recipe_id):
    """
    Delete photo from recipe - Available to all users
    """
    recipe = Recipe.query.filter_by(id=recipe_id, user_id=current_user.id).first()
    
    if not recipe:
        return jsonify({
            'success': False,
            'error': 'Recipe not found'
        }), 404
    
    try:
        if recipe.image_url:
            photo_service = PhotoUploadService()
            photo_service.delete_recipe_photo(recipe.image_url)
            
            recipe.image_url = None
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Photo deleted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scanner_upload_bp.route('/create-recipe-from-barcode', methods=['POST'])
@login_required
@require_barcode_scanning()
def create_recipe_from_barcode():
    """
    Create recipe from barcode scan
    SECURED: Home tier subscription required
    """
    data = request.get_json()
    barcode = data.get('barcode')
    custom_name = data.get('custom_name', '')
    
    if not barcode:
        return jsonify({
            'success': False,
            'error': 'Barcode is required'
        }), 400
    
    try:
        # Get product data
        product_data = barcode_scanner.get_product_by_barcode(barcode)
        
        if not product_data:
            return jsonify({
                'success': False,
                'error': 'Product not found for this barcode'
            }), 404
        
        # Create recipe
        recipe_name = custom_name if custom_name else product_data.get('name', f'Product {barcode}')
        
        recipe = Recipe(
            title=recipe_name,
            description=f"Created from barcode scan: {barcode}",
            ingredients=f"Main ingredient: {product_data.get('name', 'Unknown product')}",
            instructions="1. Use as directed on package",
            servings=1,
            prep_time=5,
            cook_time=0,
            user_id=current_user.id,
            is_private=True,  # Default to private
            source_url=product_data.get('url', ''),
            barcode=barcode
        )
        
        db.session.add(recipe)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'recipe_id': recipe.id,
            'recipe_name': recipe.title,
            'message': 'Recipe created successfully from barcode'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scanner_upload_bp.route('/api/add-to-shopping-list', methods=['POST'])
@login_required
@require_barcode_scanning()
def add_scanned_to_shopping_list():
    """
    Add scanned product to shopping list
    SECURED: Home tier subscription required
    """
    data = request.get_json()
    barcode = data.get('barcode')
    quantity = data.get('quantity', 1)
    
    if not barcode:
        return jsonify({
            'success': False,
            'error': 'Barcode is required'
        }), 400
    
    try:
        # Get product data
        product_data = barcode_scanner.get_product_by_barcode(barcode)
        
        if not product_data:
            return jsonify({
                'success': False,
                'error': 'Product not found for this barcode'
            }), 404
        
        # Check if item already exists in shopping list
        existing_item = ShoppingListItem.query.filter_by(
            user_id=current_user.id,
            item_name=product_data['name'],
            is_purchased=False
        ).first()
        
        if existing_item:
            existing_item.quantity_needed += quantity
            message = f"Updated quantity for {product_data['name']}"
        else:
            shopping_item = ShoppingListItem(
                user_id=current_user.id,
                item_name=product_data['name'],
                category=product_data.get('category', 'Other'),
                quantity_needed=quantity,
                unit='units',
                source='barcode_scan',
                priority=3,
                notes=f"Added via barcode scan: {barcode}"
            )
            db.session.add(shopping_item)
            message = f"Added {product_data['name']} to shopping list"
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@scanner_upload_bp.route('/api/calculate-nutrition', methods=['POST'])
@login_required
@require_barcode_scanning()
def calculate_barcode_nutrition():
    """
    Calculate nutrition from barcode
    SECURED: Home tier subscription required
    """
    data = request.get_json()
    barcode = data.get('barcode')
    servings = data.get('servings', 1)
    portion_size = data.get('portion_size', 100)
    
    if not barcode:
        return jsonify({
            'success': False,
            'error': 'Barcode is required'
        }), 400
    
    try:
        nutrition_calc = NutritionCalculator()
        nutrition_data = nutrition_calc.calculate_product_nutrition(
            barcode, int(servings), portion_size
        )
        
        if nutrition_data:
            return jsonify({
                'success': True,
                'nutrition': nutrition_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Nutrition data not available for this product'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Public endpoints (no subscription required) for basic functionality
@scanner_upload_bp.route('/shopping-list')
@login_required
def shopping_list_view():
    """
    View shopping list - Available to all users
    """
    shopping_items = ShoppingListItem.query.filter_by(
        user_id=current_user.id,
        is_purchased=False
    ).order_by(ShoppingListItem.priority.asc()).all()
    
    return render_template('shopping_list.html', items=shopping_items)

@scanner_upload_bp.route('/api/shopping-list-item/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_shopping_item(item_id):
    """
    Toggle shopping list item purchased status - Available to all users
    """
    item = ShoppingListItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first()
    
    if not item:
        return jsonify({
            'success': False,
            'error': 'Item not found'
        }), 404
    
    try:
        item.is_purchased = not item.is_purchased
        if item.is_purchased:
            item.purchased_at = datetime.utcnow()
        else:
            item.purchased_at = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_purchased': item.is_purchased,
            'message': 'Item status updated'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

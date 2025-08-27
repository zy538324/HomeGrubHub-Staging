"""
Smart shopping routes for ingredient mapping and price integration
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from recipe_app.db import db
from recipe_app.utils.smart_shopping import (
    update_shopping_list_with_smart_mapping,
    ShoppingListPriceService,
    IngredientParser
)
from recipe_app.models.advanced_models import ShoppingList, ShoppingListItem
from recipe_app.models.models import Recipe

smart_shopping_bp = Blueprint('smart_shopping', __name__)

@smart_shopping_bp.route('/shopping/smart-add/<int:recipe_id>', methods=['POST'])
@login_required
def smart_add_recipe_to_shopping_list(recipe_id):
    """Add recipe to shopping list with smart ingredient mapping"""
    try:
        result = update_shopping_list_with_smart_mapping(recipe_id, current_user.id)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']})
        
        return jsonify({
            'success': True,
            'message': f"Added {result['items_added']} items, updated {result['items_updated']} items",
            'items_added': result['items_added'],
            'items_updated': result['items_updated'],
            'price_results': result['price_results']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@smart_shopping_bp.route('/shopping/update-prices', methods=['POST'])
@login_required
def update_shopping_list_prices():
    """Update prices for current shopping list"""
    try:
        shopping_list_id = request.json.get('shopping_list_id') if request.json else None
        
        result = ShoppingListPriceService.add_prices_to_shopping_list(
            current_user.id, shopping_list_id
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@smart_shopping_bp.route('/shopping/optimize', methods=['POST'])
@login_required
def optimize_shopping_list():
    """Optimize shopping list by store and cost"""
    try:
        shopping_list_id = request.json.get('shopping_list_id') if request.json else None
        
        result = ShoppingListPriceService.optimize_shopping_list_by_store(
            current_user.id, shopping_list_id
        )
        
        return jsonify({
            'success': True,
            'optimization': result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@smart_shopping_bp.route('/shopping/parse-ingredient', methods=['POST'])
@login_required
def parse_ingredient():
    """Parse a single ingredient for testing/preview"""
    try:
        ingredient = request.json.get('ingredient', '')
        
        if not ingredient:
            return jsonify({'success': False, 'error': 'Ingredient required'})
        
        mapping = IngredientParser.parse_ingredient(ingredient)
        
        return jsonify({
            'success': True,
            'mapping': {
                'original_ingredient': mapping.original_ingredient,
                'quantity': mapping.quantity,
                'unit': mapping.unit,
                'product_name': mapping.product_name,
                'purchasable_unit': mapping.purchasable_unit,
                'conversion_factor': mapping.conversion_factor,
                'category': mapping.category,
                'notes': mapping.notes
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@smart_shopping_bp.route('/shopping/smart-view')
@login_required
def smart_shopping_view():
    """View smart shopping list with prices and optimization"""
    # Get user's active shopping list
    shopping_list = ShoppingList.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).first()
    
    if not shopping_list:
        # Create default shopping list
        shopping_list = ShoppingList(
            user_id=current_user.id,
            name="My Shopping List",
            is_active=True
        )
        db.session.add(shopping_list)
        db.session.commit()
    
    # Get shopping list items with price information
    items = ShoppingListItem.query.filter_by(
        shopping_list_id=shopping_list.id,
        is_purchased=False
    ).order_by(ShoppingListItem.category, ShoppingListItem.name).all()
    
    # Group items by category
    items_by_category = {}
    total_cost = 0.0
    items_with_prices = 0
    
    for item in items:
        category = item.category or 'other'
        if category not in items_by_category:
            items_by_category[category] = []
        
        items_by_category[category].append(item)
        
        if item.estimated_price:
            total_cost += item.estimated_price
            items_with_prices += 1
    
    # Get recent recipes for quick adding
    recent_recipes = Recipe.query.filter_by(
        user_id=current_user.id
    ).order_by(Recipe.created_at.desc()).limit(10).all()
    
    return render_template('shopping/smart_shopping.html',
                         shopping_list=shopping_list,
                         items_by_category=items_by_category,
                         total_items=len(items),
                         items_with_prices=items_with_prices,
                         total_cost=total_cost,
                         recent_recipes=recent_recipes)

@smart_shopping_bp.route('/shopping/item/<int:item_id>/prices')
@login_required
def get_item_prices(item_id):
    """Get price comparison for a specific shopping list item with on-demand scraping"""
    try:
        item = ShoppingListItem.query.get_or_404(item_id)
        
        # Verify user owns this item
        if item.shopping_list.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'})
        
        # Get user's postcode for location-based pricing
        user_postcode = getattr(current_user, 'postcode', None)
        
        # First try to get user-contributed prices
        from recipe_app.utils.user_price_service import user_price_service
        user_prices = user_price_service.get_prices_for_item(item.name, user_postcode)
        
        if user_prices:
            # Format user-contributed price data
            price_data = []
            for price in user_prices:
                price_data.append({
                    'store': price['shop_name'],
                    'price': price['price'],
                    'name': price['item_name'],
                    'is_estimate': False,
                    'is_user_contributed': True,
                    'confidence': 'verified' if price['is_verified'] else 'user-submitted',
                    'verification_count': price['verification_count'],
                    'scraped_date': f"Submitted {price['days_old']} days ago",
                    'location': price['shop_location'],
                    'price_id': price['id']
                })
            
            # Sort by price
            price_data.sort(key=lambda x: x['price'])
            
            return jsonify({
                'success': True,
                'data_source': 'User-contributed prices',
                'item_name': item.name,
                'prices': price_data,
                'total_found': len(price_data),
                'user_postcode': user_postcode,
                'message': f'Found {len(price_data)} user-contributed prices'
            })
        
        else:
            # Fall back to price estimates if no user-contributed data
            from recipe_app.utils.safe_price_service import safe_price_service
            estimate = safe_price_service.estimate_price(item.name, user_postcode or '')
            
            # Create store comparison estimates
            store_comparisons = safe_price_service.get_store_comparison(item.name, user_postcode or '')
            
            # Format estimated price data with clear indication these are estimates
            price_data = []
            for comparison in store_comparisons:
                price_data.append({
                    'store': comparison['store'],
                    'price': comparison['estimated_price'],
                    'name': item.name,
                    'is_estimate': True,
                    'is_user_contributed': False,
                    'confidence': comparison['confidence'],
                    'scraped_date': 'Estimated based on UK averages',
                    'note': 'This item is not priced yet - be the first to contribute!'
                })
            
            # Sort by price
            price_data.sort(key=lambda x: x['price'])
            
            return jsonify({
                'success': True,
                'data_source': 'Statistical estimates',
                'item_name': item.name,
                'prices': price_data,
                'total_found': len(price_data),
                'user_postcode': user_postcode,
                'no_user_data': True,
                'message': 'No user-contributed prices yet. Showing estimates based on UK averages.',
                'contribute_url': '/prices/submit',
                'cheapest_price': price_data[0]['price'] if price_data else None,
                'cheapest_store': price_data[0]['store'] if price_data else None,
                'stores_checked': len(set(p['store'] for p in price_data)),
            'total_prices_found': len(price_data)
        })
        
    except Exception as e:
        print(f"Error getting prices for item {item_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get price information',
            'debug_error': str(e)
        })

@smart_shopping_bp.route('/shopping/bulk-price-update', methods=['POST'])
@login_required
def bulk_update_prices():
    """Update prices for all items in shopping list using dynamic pricing"""
    try:
        # Get user's shopping list items without prices
        items_without_prices = ShoppingListItem.query.join(ShoppingList).filter(
            ShoppingList.user_id == current_user.id,
            ShoppingListItem.is_purchased == False,
            ShoppingListItem.estimated_price.is_(None)
        ).all()
        
        updated_count = 0
        estimated_count = 0
        error_count = 0
        
        # Get user's postcode for location-based pricing
        user_postcode = getattr(current_user, 'postcode', None)
        
        from recipe_app.utils.user_price_service import user_price_service
        from recipe_app.utils.safe_price_service import safe_price_service
        
        for item in items_without_prices:
            try:
                # First try user-contributed prices
                best_price = user_price_service.get_best_price_for_item(item.name, user_postcode)
                
                if best_price:
                    item.estimated_price = best_price['price']
                    item.notes = f"Price from {best_price['shop_name']} (user-contributed)"
                    updated_count += 1
                else:
                    # Fall back to statistical estimate
                    estimate = safe_price_service.estimate_price(item.name, user_postcode or '')
                    if estimate:
                        item.estimated_price = estimate.estimated_price
                        item.notes = f"Estimated price (UK average) - contribute real prices to help!"
                        estimated_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"Error updating price for {item.name}: {e}")
        
        db.session.commit()
        
        message_parts = []
        if updated_count > 0:
            message_parts.append(f"Updated {updated_count} items with user-contributed prices")
        if estimated_count > 0:
            message_parts.append(f"Added estimates for {estimated_count} items")
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'estimated_count': estimated_count,
            'error_count': error_count,
            'message': '. '.join(message_parts) if message_parts else "No price updates available",
            'user_postcode': user_postcode,
            'contribute_url': '/prices/submit'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@smart_shopping_bp.route('/shopping/ingredient-preview', methods=['POST'])
@login_required
def preview_ingredient_conversion():
    """Preview how recipe ingredients will be converted for shopping"""
    try:
        recipe_id = request.json.get('recipe_id')
        
        if not recipe_id:
            return jsonify({'success': False, 'error': 'Recipe ID required'})
        
        recipe = Recipe.query.get_or_404(recipe_id)
        
        # Parse ingredients
        mappings = ShoppingListPriceService.convert_recipe_to_shopping_items(
            recipe.ingredients, recipe_id
        )
        
        # Format for display
        preview_data = []
        for mapping in mappings:
            preview_data.append({
                'original': mapping.original_ingredient,
                'product_name': mapping.product_name,
                'quantity': mapping.quantity,
                'unit': mapping.unit,
                'purchasable_unit': mapping.purchasable_unit,
                'conversion_factor': mapping.conversion_factor,
                'category': mapping.category,
                'notes': mapping.notes
            })
        
        return jsonify({
            'success': True,
            'recipe_title': recipe.title,
            'conversions': preview_data,
            'total_items': len(preview_data)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

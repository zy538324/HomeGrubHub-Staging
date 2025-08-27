"""
Weekly Shopping List Routes
Enhanced shopping list features for multi-week planning
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from recipe_app.models.pantry_models import WeeklyShoppingList, WeeklyShoppingItem, db
from .scanner_routes import barcode_scanner
import json

weekly_shopping_bp = Blueprint('weekly_shopping', __name__, url_prefix='/weekly-shopping')

def get_or_create_current_week_list(user_id):
    """Get or create the shopping list for the current week"""
    today = date.today()
    monday = today - timedelta(days=today.weekday())  # Get Monday of current week
    week_end = monday + timedelta(days=6)
    
    # Try to get existing list
    weekly_list = WeeklyShoppingList.query.filter_by(
        user_id=user_id,
        week_start_date=monday
    ).first()
    
    # Create if doesn't exist
    if not weekly_list:
        weekly_list = WeeklyShoppingList(
            user_id=user_id,
            week_start_date=monday,
            week_end_date=week_end,
            week_label=WeeklyShoppingList.get_week_label(monday)
        )
        db.session.add(weekly_list)
        db.session.commit()
    
    return weekly_list

@weekly_shopping_bp.route('/api/get-available-lists')
@login_required
def get_available_lists():
    """Get available weekly shopping lists for modal selection"""
    # Get lists for the next 4 weeks
    today = date.today()
    monday = today - timedelta(days=today.weekday())  # Get Monday of current week
    
    lists = []
    for i in range(4):
        week_start = monday + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        
        # Get or create weekly list
        weekly_list = WeeklyShoppingList.query.filter_by(
            user_id=current_user.id,
            week_start_date=week_start
        ).first()
        
        if not weekly_list:
            weekly_list = WeeklyShoppingList(
                user_id=current_user.id,
                week_start_date=week_start,
                week_end_date=week_end,
                week_label=WeeklyShoppingList.get_week_label(week_start)
            )
            db.session.add(weekly_list)
            db.session.commit()
        
        lists.append({
            'id': weekly_list.id,
            'label': weekly_list.week_label,
            'week_start': week_start.strftime('%b %d'),
            'week_end': week_end.strftime('%b %d'),
            'is_current': i == 0,
            'items_count': weekly_list.items.count()
        })
    
    return jsonify({
        'success': True,
        'lists': lists
    })

@weekly_shopping_bp.route('/')
@login_required
def index():
    """View all weekly shopping lists"""
    # Get lists for the next 4 weeks
    today = date.today()
    monday = today - timedelta(days=today.weekday())  # Get Monday of current week
    
    weeks = []
    for i in range(4):
        week_start = monday + timedelta(weeks=i)
        week_end = week_start + timedelta(days=6)
        
        # Get or create weekly list
        weekly_list = WeeklyShoppingList.query.filter_by(
            user_id=current_user.id,
            week_start_date=week_start
        ).first()
        
        if not weekly_list:
            weekly_list = WeeklyShoppingList(
                user_id=current_user.id,
                week_start_date=week_start,
                week_end_date=week_end,
                week_label=WeeklyShoppingList.get_week_label(week_start)
            )
            db.session.add(weekly_list)
        
        weeks.append(weekly_list)
    
    db.session.commit()
    
    return render_template('weekly_shopping/index.html', weeks=weeks)

@weekly_shopping_bp.route('/current')
@login_required
def current_week():
    """Redirect to the current week's shopping list"""
    current_week_list = get_or_create_current_week_list(current_user.id)
    return redirect(url_for('weekly_shopping.view_week', week_id=current_week_list.id))

@weekly_shopping_bp.route('/week/<int:week_id>')
@login_required
def view_week(week_id):
    """View a specific week's shopping list"""
    weekly_list = WeeklyShoppingList.query.filter_by(
        id=week_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Get items grouped by category
    categories = weekly_list.get_items_by_category()
    
    return render_template('weekly_shopping/week_detail.html', 
                         weekly_list=weekly_list, 
                         categories=categories)

@weekly_shopping_bp.route('/api/week/<int:week_id>/add-item', methods=['POST'])
@login_required
def add_item_to_week(week_id):
    """Add an item to a specific week"""
    weekly_list = WeeklyShoppingList.query.filter_by(
        id=week_id,
        user_id=current_user.id
    ).first_or_404()
    
    data = request.get_json()
    
    try:
        new_item = WeeklyShoppingItem(
            weekly_list_id=weekly_list.id,
            item_name=data.get('name', '').strip(),
            category=data.get('category', 'Other'),
            quantity_needed=float(data.get('quantity', 1)),
            unit=data.get('unit', 'item'),
            source='manual',
            priority=int(data.get('priority', 3)),
            notes=data.get('notes', ''),
            estimated_cost=float(data.get('estimated_cost', 0)) if data.get('estimated_cost') else None,
            meal_date=datetime.strptime(data.get('meal_date'), '%Y-%m-%d').date() if data.get('meal_date') else None
        )
        
        db.session.add(new_item)
        weekly_list.update_totals()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Added {new_item.item_name} to week',
            'item': new_item.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@weekly_shopping_bp.route('/api/week/<int:week_id>/add-barcode-item', methods=['POST'])
@login_required
def add_barcode_item_to_week(week_id):
    """Add a scanned barcode item to a specific week"""
    weekly_list = WeeklyShoppingList.query.filter_by(
        id=week_id,
        user_id=current_user.id
    ).first_or_404()
    
    data = request.get_json()
    barcode = data.get('barcode')
    
    if not barcode:
        return jsonify({'success': False, 'error': 'Barcode required'}), 400
    
    try:
        # Get product data
        product_data = barcode_scanner.get_product_by_barcode(barcode)
        
        if not product_data:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
        
        product_name = product_data.get('name', 'Unknown Product')
        
        # Check if item already exists in this week
        existing_item = WeeklyShoppingItem.query.filter_by(
            weekly_list_id=weekly_list.id,
            item_name=product_name,
            source='barcode_scan'
        ).first()
        
        if existing_item:
            existing_item.quantity_needed += 1
            message = f"Increased quantity of {product_name} to {existing_item.quantity_needed}"
        else:
            new_item = WeeklyShoppingItem(
                weekly_list_id=weekly_list.id,
                item_name=product_name,
                category=product_data.get('categories', ['Unknown'])[0] if product_data.get('categories') else 'Unknown',
                quantity_needed=1,
                unit='item',
                source='barcode_scan',
                priority=3,
                notes=f'Added via barcode scan: {barcode}',
                meal_date=datetime.strptime(data.get('meal_date'), '%Y-%m-%d').date() if data.get('meal_date') else None
            )
            db.session.add(new_item)
            message = f"Added {product_name} to week"
        
        weekly_list.update_totals()
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

@weekly_shopping_bp.route('/api/item/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_item_purchased(item_id):
    """Toggle item purchased status"""
    try:
        item = WeeklyShoppingItem.query.join(WeeklyShoppingList).filter(
            WeeklyShoppingItem.id == item_id,
            WeeklyShoppingList.user_id == current_user.id
        ).first()
        
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404
        
        # Handle JSON or form data
        data = {}
        if request.is_json:
            data = request.get_json() or {}
        elif request.form:
            data = request.form.to_dict()
        
        if not item.is_purchased:
            actual_cost = data.get('actual_cost')
            if actual_cost:
                try:
                    actual_cost = float(actual_cost)
                except ValueError:
                    actual_cost = None
            item.mark_as_purchased(actual_cost)
        else:
            item.is_purchased = False
            item.purchased_at = None
            item.actual_cost = None
            if item.weekly_list:
                item.weekly_list.update_totals()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'is_purchased': item.is_purchased,
            'actual_cost': float(item.actual_cost) if item.actual_cost else None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@weekly_shopping_bp.route('/api/item/<int:item_id>/edit', methods=['POST'])
@login_required
def edit_item(item_id):
    """Edit a shopping list item"""
    try:
        item = WeeklyShoppingItem.query.join(WeeklyShoppingList).filter(
            WeeklyShoppingItem.id == item_id,
            WeeklyShoppingList.user_id == current_user.id
        ).first()
        
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Update fields if provided
        if 'item_name' in data:
            item.item_name = data['item_name'].strip()
        if 'quantity_needed' in data:
            item.quantity_needed = float(data['quantity_needed'])
        if 'unit' in data:
            item.unit = data['unit']
        if 'category' in data:
            item.category = data['category']
        if 'estimated_cost' in data:
            item.estimated_cost = float(data['estimated_cost']) if data['estimated_cost'] else None
        if 'actual_cost' in data:
            item.actual_cost = float(data['actual_cost']) if data['actual_cost'] else None
        if 'priority' in data:
            item.priority = int(data['priority'])
        if 'notes' in data:
            item.notes = data['notes']
        if 'meal_date' in data:
            if data['meal_date']:
                item.meal_date = datetime.strptime(data['meal_date'], '%Y-%m-%d').date()
            else:
                item.meal_date = None
        
        # Update weekly list totals
        if item.weekly_list:
            item.weekly_list.update_totals()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item': item.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@weekly_shopping_bp.route('/api/item/<int:item_id>/delete', methods=['DELETE'])
@login_required
def delete_item(item_id):
    """Delete a shopping list item"""
    try:
        item = WeeklyShoppingItem.query.join(WeeklyShoppingList).filter(
            WeeklyShoppingItem.id == item_id,
            WeeklyShoppingList.user_id == current_user.id
        ).first()
        
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404
        
        weekly_list = item.weekly_list
        item_name = item.item_name
        
        db.session.delete(item)
        
        # Update weekly list totals
        if weekly_list:
            weekly_list.update_totals()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Deleted {item_name}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@weekly_shopping_bp.route('/api/week/<int:week_id>/clear-purchased', methods=['POST'])
@login_required
def clear_purchased_items(week_id):
    """Clear all purchased items from a week"""
    try:
        weekly_list = WeeklyShoppingList.query.filter_by(
            id=week_id,
            user_id=current_user.id
        ).first()
        
        if not weekly_list:
            return jsonify({
                'success': False,
                'error': 'Week not found'
            }), 404
        
        # Get all purchased items
        purchased_items = WeeklyShoppingItem.query.filter_by(
            weekly_list_id=week_id,
            is_purchased=True
        ).all()
        
        # Save price data to community database before deleting
        price_contributions = 0
        for item in purchased_items:
            if item.actual_cost and item.actual_cost > 0:
                # Try to contribute to community price database
                try:
                    from recipe_app.models.user_price_models import UserContributedPrice, PriceDataSanitizer
                    
                    # Create a community price entry
                    price_entry = UserContributedPrice(
                        shop_name="Unknown Store",  # We don't track store in weekly shopping yet
                        item_name=item.item_name,
                        size=f"{item.quantity_needed} {item.unit}" if item.quantity_needed != 1 else None,
                        price=item.actual_cost,
                        price_per_unit=item.actual_cost / item.quantity_needed if item.quantity_needed > 0 else item.actual_cost,
                        shop_location="User Location",  # Could be enhanced with user's postcode
                        submitted_by=current_user.id,
                        normalized_item_name=PriceDataSanitizer.normalize_item_name(item.item_name),
                        normalized_shop_name=PriceDataSanitizer.normalize_shop_name("Unknown Store")
                    )
                    db.session.add(price_entry)
                    price_contributions += 1
                except Exception as e:
                    # Don't fail the clearing if price contribution fails
                    print(f"Failed to contribute price for {item.item_name}: {e}")
        
        # Delete purchased items
        deleted_count = len(purchased_items)
        for item in purchased_items:
            db.session.delete(item)
        
        # Update weekly list totals
        weekly_list.update_totals()
        
        db.session.commit()
        
        message = f'Cleared {deleted_count} purchased items'
        if price_contributions > 0:
            message += f' and contributed {price_contributions} prices to community database'
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_count': deleted_count,
            'price_contributions': price_contributions
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@weekly_shopping_bp.route('/api/item/<int:item_id>/price-suggestions')
@login_required  
def get_price_suggestions(item_id):
    """Get price suggestions from community database"""
    try:
        item = WeeklyShoppingItem.query.join(WeeklyShoppingList).filter(
            WeeklyShoppingItem.id == item_id,
            WeeklyShoppingList.user_id == current_user.id
        ).first()
        
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404
        
        from recipe_app.models.user_price_models import UserContributedPrice, PriceDataSanitizer
        from sqlalchemy import func, desc
        
        # Search for similar items in community database
        normalized_name = PriceDataSanitizer.normalize_item_name(item.item_name)
        
        # Get recent prices for this item (last 30 days)
        recent_prices = UserContributedPrice.query.filter(
            UserContributedPrice.normalized_item_name.ilike(f'%{normalized_name}%')
        ).filter(
            UserContributedPrice.submitted_at >= datetime.utcnow() - timedelta(days=30)
        ).order_by(desc(UserContributedPrice.submitted_at)).limit(10).all()
        
        suggestions = []
        total_price = 0
        count = 0
        
        for price_entry in recent_prices:
            suggestions.append({
                'shop_name': price_entry.shop_name,
                'price': float(price_entry.price),
                'price_per_unit': float(price_entry.price_per_unit) if price_entry.price_per_unit else None,
                'size': price_entry.size,
                'submitted_at': price_entry.submitted_at.strftime('%Y-%m-%d'),
                'verification_count': price_entry.verification_count,
                'is_verified': price_entry.is_verified
            })
            total_price += float(price_entry.price)
            count += 1
        
        average_price = round(total_price / count, 2) if count > 0 else None
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'average_price': average_price,
            'suggestion_count': count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@weekly_shopping_bp.route('/api/week/<int:week_id>/copy-to-next', methods=['POST'])
@login_required
def copy_week_to_next(week_id):
    """Copy a week's shopping list to the next week"""
    try:
        source_week = WeeklyShoppingList.query.filter_by(
            id=week_id,
            user_id=current_user.id
        ).first()
        
        if not source_week:
            return jsonify({
                'success': False,
                'error': f'Source week {week_id} not found'
            }), 404
        # Calculate next week's dates
        next_week_start = source_week.week_start_date + timedelta(weeks=1)
        next_week_end = next_week_start + timedelta(days=6)
        
        # Check if next week already exists
        existing_week = WeeklyShoppingList.query.filter_by(
            user_id=current_user.id,
            week_start_date=next_week_start
        ).first()
        
        if existing_week:
            # Instead of failing, merge items into existing week
            copied_count = 0
            for item in source_week.items.filter_by(is_purchased=False):
                # Check if item already exists in next week
                existing_item = WeeklyShoppingItem.query.filter_by(
                    weekly_list_id=existing_week.id,
                    item_name=item.item_name
                ).first()
                
                if not existing_item:
                    new_item = WeeklyShoppingItem(
                        weekly_list_id=existing_week.id,
                        item_name=item.item_name,
                        category=item.category,
                        quantity_needed=item.quantity_needed,
                        unit=item.unit,
                        source='copied',
                        priority=item.priority,
                        estimated_cost=item.estimated_cost,
                        notes=f'Copied from previous week. {item.notes}' if item.notes else 'Copied from previous week',
                        meal_date=item.meal_date + timedelta(weeks=1) if item.meal_date else None
                    )
                    db.session.add(new_item)
                    copied_count += 1
            
            existing_week.update_totals()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Merged {copied_count} new items into existing next week list',
                'new_week_id': existing_week.id
            })
        
        # Create new week
        new_week = WeeklyShoppingList(
            user_id=current_user.id,
            week_start_date=next_week_start,
            week_end_date=next_week_end,
            week_label=WeeklyShoppingList.get_week_label(next_week_start),
            budget_target=source_week.budget_target
        )
        db.session.add(new_week)
        db.session.flush()  # Get the ID
        
        # Copy unpurchased items
        copied_count = 0
        for item in source_week.items.filter_by(is_purchased=False):
            new_item = WeeklyShoppingItem(
                weekly_list_id=new_week.id,
                item_name=item.item_name,
                category=item.category,
                quantity_needed=item.quantity_needed,
                unit=item.unit,
                source='copied',
                priority=item.priority,
                estimated_cost=item.estimated_cost,
                notes=f'Copied from previous week. {item.notes}' if item.notes else 'Copied from previous week',
                meal_date=item.meal_date + timedelta(weeks=1) if item.meal_date else None
            )
            db.session.add(new_item)
            copied_count += 1
        
        new_week.update_totals()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Copied {copied_count} items to next week ({new_week.week_label})',
            'new_week_id': new_week.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in copy_week_to_next: {str(e)}")  # Add debugging
        return jsonify({
            'success': False,
            'error': f'Failed to copy items: {str(e)}'
        }), 500

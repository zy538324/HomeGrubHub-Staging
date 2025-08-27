"""
Pantry management routes for inventory tracking and shopping list integration
"""
from flask import render_template, flash, redirect, url_for, request, Blueprint, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from recipe_app.db import db
from recipe_app.models.pantry_models import PantryItem, PantryCategory, PantryUsageLog, ShoppingListItem
from recipe_app.forms.pantry_forms import PantryItemForm, AddPantryItemForm, PantryQuickAddForm, ShoppingListForm
from recipe_app.models.models import Recipe
from recipe_app.utils.uk_price_service import uk_price_service
# Import smart ingredient parser to safely map recipe ingredients to purchasable products
from recipe_app.utils.smart_shopping import IngredientParser

pantry_bp = Blueprint('pantry', __name__, url_prefix='/pantry')


def update_pantry_from_purchase(shopping_item, actual_quantity=None, actual_cost=None):
    """
    Helper function to update pantry when a shopping item is purchased
    Returns tuple (success, message)
    """
    try:
        if actual_quantity is None:
            actual_quantity = shopping_item.quantity_needed
        
        # First, try to find existing pantry item with same name
        pantry_item = PantryItem.query.filter_by(
            user_id=current_user.id,
            name=shopping_item.item_name
        ).first()
        
        if pantry_item:
            # Update existing pantry item quantity
            old_quantity = pantry_item.current_quantity
            pantry_item.current_quantity += actual_quantity
            pantry_item.updated_at = datetime.utcnow()
            
            # Update cost information if provided
            if actual_cost:
                # Calculate cost per unit from the purchase
                cost_per_unit = actual_cost / actual_quantity if actual_quantity > 0 else actual_cost
                pantry_item.cost_per_unit = cost_per_unit
                pantry_item.total_cost = pantry_item.current_quantity * cost_per_unit
            
            # Update purchase date
            pantry_item.last_purchased = date.today()
            
            # Create usage log for the pantry update
            usage_log = PantryUsageLog(
                user_id=current_user.id,
                quantity_change=actual_quantity,
                old_quantity=old_quantity,
                new_quantity=pantry_item.current_quantity,
                reason='purchase',
                timestamp=datetime.utcnow(),
                notes=f'Purchased from shopping list: {shopping_item.notes or ""}'
            )
            # Set the relationship to link to the existing pantry item
            usage_log.item = pantry_item
            db.session.add(usage_log)
            
            return True, f"Added {actual_quantity} {shopping_item.unit} to existing pantry stock"
            
        else:
            # Create new pantry item if it doesn't exist
            # Try to determine category based on item name (basic logic)
            category = None
            item_name_lower = shopping_item.item_name.lower()
            
            # Basic category matching
            if any(word in item_name_lower for word in ['milk', 'cheese', 'yogurt', 'butter']):
                category = PantryCategory.query.filter_by(user_id=current_user.id, name='Dairy').first()
            elif any(word in item_name_lower for word in ['apple', 'banana', 'orange', 'berry']):
                category = PantryCategory.query.filter_by(user_id=current_user.id, name='Fruits').first()
            elif any(word in item_name_lower for word in ['carrot', 'onion', 'potato', 'lettuce']):
                category = PantryCategory.query.filter_by(user_id=current_user.id, name='Vegetables').first()
            elif any(word in item_name_lower for word in ['chicken', 'beef', 'pork', 'fish']):
                category = PantryCategory.query.filter_by(user_id=current_user.id, name='Meat & Fish').first()
            else:
                category = PantryCategory.query.filter_by(user_id=current_user.id, name='Other').first()
            
            # Calculate cost per unit if actual cost provided
            cost_per_unit = None
            total_cost = actual_cost
            if actual_cost and actual_quantity > 0:
                cost_per_unit = actual_cost / actual_quantity
            
            new_pantry_item = PantryItem(
                user_id=current_user.id,
                name=shopping_item.item_name,
                current_quantity=actual_quantity,
                unit=shopping_item.unit,
                minimum_quantity=1.0,  # Default minimum
                ideal_quantity=actual_quantity * 2,  # Suggest double for ideal stock
                category_id=category.id if category else None,
                cost_per_unit=cost_per_unit,
                total_cost=total_cost,
                last_purchased=date.today(),
                notes=f'Auto-created from shopping list purchase'
            )
            db.session.add(new_pantry_item)
            
            # Create initial usage log using the relationship
            # This will automatically set the item_id when the pantry_item gets its ID
            usage_log = PantryUsageLog(
                user_id=current_user.id,
                quantity_change=actual_quantity,
                old_quantity=0.0,
                new_quantity=actual_quantity,
                reason='purchase',
                timestamp=datetime.utcnow(),
                notes=f'Initial stock from shopping list purchase'
            )
            # Use the relationship to link them
            usage_log.item = new_pantry_item
            db.session.add(usage_log)
            
            return True, f"Created new pantry item with {actual_quantity} {shopping_item.unit}"
            
    except Exception as e:
        print(f"Error updating pantry from purchase: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error updating pantry: {str(e)}"


def remove_pantry_from_unpurchase(shopping_item, actual_quantity=None):
    """
    Helper function to remove pantry quantity when a purchase is undone
    Returns tuple (success, message)
    """
    try:
        if actual_quantity is None:
            actual_quantity = shopping_item.quantity_needed
            
        # Find existing pantry item
        pantry_item = PantryItem.query.filter_by(
            user_id=current_user.id,
            name=shopping_item.item_name
        ).first()
        
        if pantry_item:
            old_quantity = pantry_item.current_quantity
            
            # Reduce quantity (but don't go below 0)
            reduction = min(actual_quantity, pantry_item.current_quantity)
            pantry_item.current_quantity -= reduction
            pantry_item.updated_at = datetime.utcnow()
            
            # Create usage log for the reduction
            usage_log = PantryUsageLog(
                user_id=current_user.id,
                quantity_change=-reduction,
                old_quantity=old_quantity,
                new_quantity=pantry_item.current_quantity,
                reason='purchase_cancelled',
                timestamp=datetime.utcnow(),
                notes=f'Purchase cancelled from shopping list'
            )
            # Set the relationship to link to the existing pantry item
            usage_log.item = pantry_item
            db.session.add(usage_log)
            
            if reduction < actual_quantity:
                return True, f"Reduced pantry by {reduction} {shopping_item.unit} (was only {old_quantity} available)"
            else:
                return True, f"Reduced pantry by {reduction} {shopping_item.unit}"
        else:
            return True, "No pantry item found to adjust"
            
    except Exception as e:
        print(f"Error removing pantry from unpurchase: {e}")
        import traceback
        traceback.print_exc()
        return False, f"Error updating pantry: {str(e)}"


def ensure_default_categories(user_id):
    """Ensure user has default pantry categories"""
    existing_categories = PantryCategory.query.filter_by(user_id=user_id).count()
    
    if existing_categories == 0:
        # Create default categories for this user
        default_categories = [
            {'name': 'Dairy', 'icon': 'fas fa-cheese', 'color': '#FFE4B5', 'sort_order': 1},
            {'name': 'Fruits', 'icon': 'fas fa-apple-alt', 'color': '#FF6B6B', 'sort_order': 2},
            {'name': 'Vegetables', 'icon': 'fas fa-carrot', 'color': '#4ECDC4', 'sort_order': 3},
            {'name': 'Meat & Fish', 'icon': 'fas fa-fish', 'color': '#45B7D1', 'sort_order': 4},
            {'name': 'Grains & Bread', 'icon': 'fas fa-bread-slice', 'color': '#96CEB4', 'sort_order': 5},
            {'name': 'Pantry Staples', 'icon': 'fas fa-box', 'color': '#FFEAA7', 'sort_order': 6},
            {'name': 'Beverages', 'icon': 'fas fa-coffee', 'color': '#DDA0DD', 'sort_order': 7},
            {'name': 'Other', 'icon': 'fas fa-question', 'color': '#6c757d', 'sort_order': 8}
        ]
        
        for cat_data in default_categories:
            category = PantryCategory(
                user_id=user_id,
                name=cat_data['name'],
                icon=cat_data['icon'],
                color=cat_data['color'],
                sort_order=cat_data['sort_order']
            )
            db.session.add(category)
        
        db.session.commit()


@pantry_bp.route('/')
@login_required
def index():
    """Main pantry dashboard"""
    # Ensure user has default categories
    ensure_default_categories(current_user.id)
    # Get all user's pantry items
    pantry_items = PantryItem.query.filter_by(user_id=current_user.id).all()
    
    # Categorize items
    categories = PantryCategory.query.filter_by(user_id=current_user.id).order_by(PantryCategory.sort_order).all()
    
    # Get items by status
    low_stock_items = [item for item in pantry_items if item.is_low_stock]
    expiring_soon_items = [item for item in pantry_items if item.is_expiring_soon]
    out_of_stock_items = [item for item in pantry_items if item.current_quantity <= 0]
    
    # Statistics
    total_items = len(pantry_items)
    total_value = sum(item.total_cost or 0 for item in pantry_items)
    
    # Recent usage
    recent_logs = PantryUsageLog.query.filter_by(user_id=current_user.id)\
        .order_by(PantryUsageLog.timestamp.desc()).limit(10).all()
    
    return render_template('pantry/index.html',
                         pantry_items=pantry_items,
                         categories=categories,
                         low_stock_items=low_stock_items,
                         expiring_soon_items=expiring_soon_items,
                         out_of_stock_items=out_of_stock_items,
                         total_items=total_items,
                         total_value=total_value,
                         recent_logs=recent_logs)


@pantry_bp.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    """Add new pantry item"""
    form = AddPantryItemForm()
    
    # Populate category choices
    categories = PantryCategory.query.filter_by(user_id=current_user.id).order_by(PantryCategory.name).all()
    form.category_id.choices = [(0, 'No Category')] + [(cat.id, cat.name) for cat in categories]
    
    if form.validate_on_submit():
        # Check if item already exists
        existing_item = PantryItem.query.filter_by(
            user_id=current_user.id,
            name=form.name.data.strip()
        ).first()
        
        if existing_item:
            flash(f'Item "{form.name.data}" already exists in your pantry. Use the update function to modify quantities.', 'warning')
            return redirect(url_for('pantry.edit_item', id=existing_item.id))
        
        # Create new pantry item
        item = PantryItem(
            user_id=current_user.id,
            name=form.name.data.strip(),
            brand=form.brand.data.strip() if form.brand.data else None,
            current_quantity=form.current_quantity.data,
            unit=form.unit.data,
            minimum_quantity=form.minimum_quantity.data,
            ideal_quantity=form.ideal_quantity.data,
            category_id=form.category_id.data if form.category_id.data != 0 else None,
            storage_location=form.storage_location.data,
            expiry_date=form.expiry_date.data,
            cost_per_unit=form.cost_per_unit.data,
            notes=form.notes.data
        )
        
        # Calculate total cost
        if item.cost_per_unit and item.current_quantity:
            item.total_cost = item.cost_per_unit * item.current_quantity
        
        # Set last purchased date
        if form.last_purchased.data:
            item.last_purchased = form.last_purchased.data
        else:
            item.last_purchased = date.today()
        
        try:
            # First add and commit the item to get an ID
            db.session.add(item)
            db.session.commit()
            
            # Now create initial usage log with the correct item_id
            log = PantryUsageLog(
                item_id=item.id,
                user_id=current_user.id,
                quantity_change=item.current_quantity,
                old_quantity=0,
                new_quantity=item.current_quantity,
                reason='initial_stock',
                timestamp=datetime.utcnow()
            )
            db.session.add(log)
            db.session.commit()
            
            flash(f'Added "{item.name}" to your pantry!', 'success')
            return redirect(url_for('pantry.index'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding item to pantry. Please try again.', 'error')
            print(f"Error adding pantry item: {e}")
    
    return render_template('pantry/add_item.html', form=form)


@pantry_bp.route('/edit_item/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    """Edit existing pantry item"""
    item = PantryItem.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = PantryItemForm(obj=item)
    
    # Populate category choices
    categories = PantryCategory.query.filter_by(user_id=current_user.id).order_by(PantryCategory.name).all()
    form.category_id.choices = [(0, 'No Category')] + [(cat.id, cat.name) for cat in categories]
    
    if form.validate_on_submit():
        old_quantity = item.current_quantity
        
        # Update item fields
        item.name = form.name.data.strip()
        item.brand = form.brand.data.strip() if form.brand.data else None
        item.current_quantity = form.current_quantity.data
        item.unit = form.unit.data
        item.minimum_quantity = form.minimum_quantity.data
        item.ideal_quantity = form.ideal_quantity.data
        item.category_id = form.category_id.data if form.category_id.data != 0 else None
        item.storage_location = form.storage_location.data
        item.expiry_date = form.expiry_date.data
        item.cost_per_unit = form.cost_per_unit.data
        item.notes = form.notes.data
        item.last_purchased = form.last_purchased.data
        
        # Recalculate total cost
        if item.cost_per_unit and item.current_quantity:
            item.total_cost = item.cost_per_unit * item.current_quantity
        
        # Update status flags
        item.is_running_low = item.is_low_stock
        item.updated_at = datetime.utcnow()
        
        # Log quantity change if different
        if old_quantity != item.current_quantity:
            log = PantryUsageLog(
                item_id=item.id,
                user_id=current_user.id,
                quantity_change=item.current_quantity - old_quantity,
                old_quantity=old_quantity,
                new_quantity=item.current_quantity,
                reason='manual_adjustment',
                timestamp=datetime.utcnow()
            )
            db.session.add(log)
        
        try:
            db.session.commit()
            flash(f'Updated "{item.name}" in your pantry!', 'success')
            return redirect(url_for('pantry.index'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating item. Please try again.', 'error')
            print(f"Error updating pantry item: {e}")
    
    return render_template('pantry/edit_item.html', form=form, item=item)


@pantry_bp.route('/delete_item/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    """Delete pantry item"""
    item = PantryItem.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(item)
        db.session.commit()
        flash(f'Removed "{item.name}" from your pantry.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error removing item. Please try again.', 'error')
        print(f"Error deleting pantry item: {e}")
    
    return redirect(url_for('pantry.index'))


@pantry_bp.route('/quick_add', methods=['POST'])
@login_required
def quick_add():
    """Quick add pantry item via AJAX"""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'success': False, 'error': 'Item name is required'})
    
    try:
        # Check if item already exists
        existing_item = PantryItem.query.filter_by(
            user_id=current_user.id,
            name=data['name'].strip()
        ).first()
        
        if existing_item:
            return jsonify({
                'success': False, 
                'error': 'Item already exists',
                'existing_item_id': existing_item.id
            })
        
        # Create new item
        item = PantryItem(
            user_id=current_user.id,
            name=data['name'].strip(),
            current_quantity=data.get('quantity', 1),
            unit=data.get('unit', 'units'),
            minimum_quantity=data.get('minimum_quantity', 1),
            ideal_quantity=data.get('ideal_quantity', 5),
            storage_location=data.get('storage_location', ''),
            last_purchased=date.today()
        )
        
        db.session.add(item)
        db.session.flush()  # Get ID
        
        # Create usage log
        log = PantryUsageLog(
            item_id=item.id,
            user_id=current_user.id,
            quantity_change=item.current_quantity,
            old_quantity=0,
            new_quantity=item.current_quantity,
            reason='initial_stock'
        )
        db.session.add(log)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item': item.to_dict(),
            'message': f'Added {item.name} to pantry'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@pantry_bp.route('/add_from_barcode', methods=['POST'])
@login_required  
def add_from_barcode():
    """Add item to pantry from barcode scan with nutritional data"""
    data = request.get_json()
    
    if not data or not data.get('barcode'):
        return jsonify({'success': False, 'error': 'Barcode is required'})
    
    try:
        barcode = data['barcode']
        product_name = data.get('product_name', f'Barcode Item {barcode}')
        brand = data.get('brand', '')
        quantity = float(data.get('quantity', 1))
        unit = data.get('unit', 'units')
        
        # Nutritional data (stored as hidden metadata for recipe use)
        nutrition_data = data.get('nutrition', {})
        
        # Check if item already exists by barcode
        existing_item = PantryItem.query.filter_by(
            user_id=current_user.id,
            barcode=barcode
        ).first()
        
        if existing_item:
            # Update existing item quantity
            old_quantity = existing_item.current_quantity
            existing_item.current_quantity += quantity
            existing_item.updated_at = datetime.utcnow()
            existing_item.last_purchased = date.today()
            
            # Create usage log for quantity update
            log = PantryUsageLog(
                item_id=existing_item.id,
                user_id=current_user.id,
                quantity_change=quantity,
                old_quantity=old_quantity,
                new_quantity=existing_item.current_quantity,
                reason='barcode_scan_addition'
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'action': 'updated',
                'item': existing_item.to_dict(),
                'message': f'Updated {existing_item.name} quantity (+{quantity} {unit})'
            })
        
        # Create new pantry item
        item = PantryItem(
            user_id=current_user.id,
            name=product_name,
            brand=brand,
            barcode=barcode,
            current_quantity=quantity,
            unit=unit,
            minimum_quantity=1,
            ideal_quantity=max(3, quantity),
            last_purchased=date.today(),
            notes=f'Added via barcode scan. Nutrition data: {nutrition_data}' if nutrition_data else 'Added via barcode scan'
        )
        
        db.session.add(item)
        db.session.flush()  # Get ID
        
        # Create initial usage log
        log = PantryUsageLog(
            item_id=item.id,
            user_id=current_user.id,
            quantity_change=quantity,
            old_quantity=0,
            new_quantity=quantity,
            reason='barcode_scan_initial'
        )
        db.session.add(log)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'action': 'created',
            'item': item.to_dict(),
            'message': f'Added {product_name} to pantry ({quantity} {unit})'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@pantry_bp.route('/update_quantity/<int:id>', methods=['POST'])
@login_required
def update_quantity(id):
    """Update item quantity via AJAX"""
    item = PantryItem.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    
    if not data or 'amount' not in data:
        return jsonify({'success': False, 'error': 'Amount is required'})
    
    try:
        amount = float(data['amount'])
        operation = data.get('operation', 'set')  # 'add', 'subtract', 'set'
        reason = data.get('reason', 'manual_adjustment')
        
        item.update_quantity(amount, operation, reason)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_quantity': item.current_quantity,
            'stock_status': item.stock_status,
            'is_low_stock': item.is_low_stock,
            'message': f'Updated "{item.name}" quantity'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@pantry_bp.route('/shopping_list')
@login_required
def shopping_list():
    """View shopping list with location-specific UK price estimates"""
    # Get all shopping list items
    shopping_items = ShoppingListItem.query.filter_by(
        user_id=current_user.id,
        is_purchased=False
    ).order_by(ShoppingListItem.priority, ShoppingListItem.created_at).all()
    
    # Check if user has postcode for location-specific pricing
    user_postcode = getattr(current_user, 'postcode', None)
    
    if user_postcode:
        # Use location-specific pricing
        shopping_items = uk_price_service.enrich_shopping_list_with_location_prices(
            shopping_items, user_postcode
        )
    else:
        # Fall back to general UK pricing
        shopping_items = uk_price_service.enrich_shopping_list_with_prices(shopping_items)
    
    # Group by category/store section
    items_by_category = {}
    for item in shopping_items:
        category = item.category or item.store_section or 'Other'
        if category not in items_by_category:
            items_by_category[category] = []
        items_by_category[category].append(item)
    
    # Calculate total estimated cost
    total_estimated_cost = sum(item.estimated_cost or 0 for item in shopping_items)
    
    # Get recently purchased items
    recent_purchases = ShoppingListItem.query.filter_by(
        user_id=current_user.id,
        is_purchased=True
    ).order_by(ShoppingListItem.purchased_at.desc()).limit(10).all()
    
    # Get store recommendations if postcode available
    store_recommendations = None
    if user_postcode:
        store_recommendations = uk_price_service.get_store_recommendations(user_postcode)
    
    return render_template('pantry/shopping_list.html',
                         items_by_category=items_by_category,
                         total_estimated_cost=total_estimated_cost,
                         recent_purchases=recent_purchases,
                         user_postcode=user_postcode,
                         store_recommendations=store_recommendations)


@pantry_bp.route('/generate_shopping_list', methods=['POST'])
@login_required
def generate_shopping_list():
    """Generate shopping list from low stock items"""
    try:
        # Remove existing auto-generated shopping list items
        ShoppingListItem.query.filter_by(
            user_id=current_user.id,
            source='low_stock',
            is_purchased=False
        ).delete()
        
        # Find low stock items
        low_stock_items = PantryItem.query.filter_by(user_id=current_user.id)\
            .filter(PantryItem.current_quantity <= PantryItem.minimum_quantity).all()
        
        added_count = 0
        for item in low_stock_items:
            # Calculate quantity needed to reach ideal stock
            quantity_needed = max(0, item.ideal_quantity - item.current_quantity)
            
            if quantity_needed > 0:
                # Get UK price estimate
                estimated_cost = uk_price_service.estimate_uk_price(
                    item.name, quantity_needed, item.unit
                )
                
                # Use existing cost if available, otherwise use UK estimate
                if not estimated_cost and item.cost_per_unit:
                    estimated_cost = item.cost_per_unit * quantity_needed
                
                # Get store section suggestion
                store_section = uk_price_service.suggest_store_section(item.name)
                
                shopping_item = ShoppingListItem(
                    user_id=current_user.id,
                    item_name=item.name,
                    category=item.category.name if item.category else None,
                    quantity_needed=quantity_needed,
                    unit=item.unit,
                    source='low_stock',
                    pantry_item_id=item.id,
                    priority=1 if item.current_quantity <= 0 else 2,  # Higher priority for out of stock
                    estimated_cost=estimated_cost,
                    store_section=store_section
                )
                db.session.add(shopping_item)
                added_count += 1
        
        db.session.commit()
        flash(f'Generated shopping list with {added_count} items based on low stock.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error generating shopping list. Please try again.', 'error')
        print(f"Error generating shopping list: {e}")
    
    return redirect(url_for('pantry.shopping_list'))


@pantry_bp.route('/debug_shopping_items')
@login_required
def debug_shopping_items():
    """Debug endpoint to check shopping list items"""
    try:
        items = ShoppingListItem.query.filter_by(user_id=current_user.id).all()
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'item_name': item.item_name,
                'is_purchased': item.is_purchased,
                'user_id': item.user_id
            })
        
        return jsonify({
            'success': True,
            'current_user_id': current_user.id,
            'total_items': len(items),
            'items': items_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@pantry_bp.route('/delete_shopping_item/<int:id>', methods=['POST'])
@login_required
def delete_shopping_item(id):
    """Delete a single shopping list item"""
    try:
        item = ShoppingListItem.query.filter_by(id=id, user_id=current_user.id).first()
        if not item:
            return jsonify({'success': False, 'error': 'Shopping list item not found'}), 404
        
        item_name = item.item_name
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Removed "{item_name}" from shopping list'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting shopping item {id}: {e}")
        return jsonify({'success': False, 'error': 'Database error'}), 500


@pantry_bp.route('/bulk_delete_shopping_items', methods=['POST'])
@login_required
def bulk_delete_shopping_items():
    """Delete multiple shopping list items"""
    try:
        data = request.get_json()
        if not data or 'item_ids' not in data:
            return jsonify({'success': False, 'error': 'Item IDs required'}), 400
        
        item_ids = data['item_ids']
        if not isinstance(item_ids, list) or not item_ids:
            return jsonify({'success': False, 'error': 'Invalid item IDs format'}), 400
        
        # Find and delete items that belong to the current user
        deleted_count = 0
        deleted_names = []
        
        for item_id in item_ids:
            item = ShoppingListItem.query.filter_by(id=item_id, user_id=current_user.id).first()
            if item:
                deleted_names.append(item.item_name)
                db.session.delete(item)
                deleted_count += 1
        
        if deleted_count == 0:
            return jsonify({'success': False, 'error': 'No valid items found to delete'}), 404
        
        db.session.commit()
        
        message = f'Removed {deleted_count} item{"s" if deleted_count != 1 else ""} from shopping list'
        if deleted_count <= 3:  # Show names for small deletions
            message = f'Removed {", ".join(deleted_names)} from shopping list'
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error bulk deleting shopping items: {e}")
        return jsonify({'success': False, 'error': 'Database error'}), 500


@pantry_bp.route('/clear_shopping_list', methods=['POST'])
@login_required
def clear_shopping_list():
    """Clear all shopping list items for the current user"""
    try:
        data = request.get_json() or {}
        clear_type = data.get('clear_type', 'all')  # 'all', 'purchased', 'unpurchased'
        
        query = ShoppingListItem.query.filter_by(user_id=current_user.id)
        
        if clear_type == 'purchased':
            query = query.filter_by(is_purchased=True)
            message = 'Cleared all purchased items from shopping list'
        elif clear_type == 'unpurchased':
            query = query.filter_by(is_purchased=False)
            message = 'Cleared all unpurchased items from shopping list'
        else:
            message = 'Cleared entire shopping list'
        
        deleted_count = query.count()
        query.delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{message} ({deleted_count} items removed)',
            'deleted_count': deleted_count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing shopping list: {e}")
        return jsonify({'success': False, 'error': 'Database error'}), 500


@pantry_bp.route('/bulk_shopping_action', methods=['POST'])
@login_required
def bulk_shopping_action():
    """Perform bulk actions on shopping list items"""
    try:
        data = request.get_json()
        if not data or 'item_ids' not in data or 'action' not in data:
            return jsonify({'success': False, 'error': 'Item IDs and action required'}), 400
        
        item_ids = data['item_ids']
        action = data['action']
        
        if not isinstance(item_ids, list) or not item_ids:
            return jsonify({'success': False, 'error': 'Invalid item IDs format'}), 400
        
        if action not in ['mark_purchased', 'mark_unpurchased', 'delete']:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        processed_count = 0
        processed_names = []
        pantry_updates = []
        
        for item_id in item_ids:
            item = ShoppingListItem.query.filter_by(id=item_id, user_id=current_user.id).first()
            if item:
                processed_names.append(item.item_name)
                
                if action == 'mark_purchased':
                    if not item.is_purchased:
                        item.is_purchased = True
                        item.purchased_at = datetime.utcnow()
                        
                        # Update pantry
                        success, pantry_msg = update_pantry_from_purchase(item)
                        if success:
                            pantry_updates.append(f"{item.item_name}: {pantry_msg}")
                        
                        processed_count += 1
                elif action == 'mark_unpurchased':
                    if item.is_purchased:
                        item.is_purchased = False
                        item.purchased_at = None
                        item.actual_cost = None
                        
                        # Remove from pantry
                        success, pantry_msg = remove_pantry_from_unpurchase(item)
                        if success:
                            pantry_updates.append(f"{item.item_name}: {pantry_msg}")
                        
                        processed_count += 1
                elif action == 'delete':
                    db.session.delete(item)
                    processed_count += 1
        
        if processed_count == 0:
            return jsonify({'success': False, 'error': f'No items needed {action.replace("_", " ")}'}), 400
        
        db.session.commit()
        
        # Generate appropriate message
        if action == 'mark_purchased':
            message = f'Marked {processed_count} item{"s" if processed_count != 1 else ""} as purchased'
            if pantry_updates:
                message += f' and updated pantry inventory'
        elif action == 'mark_unpurchased':
            message = f'Marked {processed_count} item{"s" if processed_count != 1 else ""} as not purchased'
            if pantry_updates:
                message += f' and adjusted pantry inventory'
        elif action == 'delete':
            message = f'Deleted {processed_count} item{"s" if processed_count != 1 else ""} from shopping list'
        
        if processed_count <= 3 and action != 'delete':  # Show names for small operations (except delete)
            item_list = ", ".join(processed_names[:processed_count])
            if action == 'mark_purchased':
                message = f'Marked {item_list} as purchased'
                if pantry_updates:
                    message += f' and updated pantry'
            elif action == 'mark_unpurchased':
                message = f'Marked {item_list} as not purchased'
                if pantry_updates:
                    message += f' and adjusted pantry'
        
        return jsonify({
            'success': True,
            'message': message,
            'processed_count': processed_count,
            'pantry_updates': pantry_updates if pantry_updates else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error performing bulk action {action}: {e}")
        return jsonify({'success': False, 'error': 'Database error'}), 500


@pantry_bp.route('/toggle_purchased/<int:id>', methods=['POST'])
@login_required
def toggle_purchased(id):
    """Toggle the purchased status of a shopping list item with pantry integration"""
    try:
        item = ShoppingListItem.query.filter_by(id=id, user_id=current_user.id).first()
        if not item:
            return jsonify({'success': False, 'error': 'Shopping list item not found'}), 404
        
        pantry_message = ""
        
        if item.is_purchased:
            # Mark as unpurchased and remove from pantry
            item.is_purchased = False
            item.purchased_at = None
            item.actual_cost = None
            
            # Flush shopping item changes first
            db.session.flush()
            
            # Remove from pantry
            success, pantry_msg = remove_pantry_from_unpurchase(item)
            if success:
                pantry_message = f" and {pantry_msg.lower()}"
            
            message = f'Marked "{item.item_name}" as not purchased{pantry_message}'
        else:
            # Mark as purchased and add to pantry
            item.is_purchased = True
            item.purchased_at = datetime.utcnow()
            
            # Flush shopping item changes first
            db.session.flush()
            
            # Add to pantry
            success, pantry_msg = update_pantry_from_purchase(item)
            if success:
                pantry_message = f" and {pantry_msg.lower()}"
            
            message = f'Marked "{item.item_name}" as purchased{pantry_message}'
        
        # Final commit of all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'is_purchased': item.is_purchased
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling purchase status for item {id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Database error'}), 500


@pantry_bp.route('/mark_purchased/<int:id>', methods=['POST'])
@login_required
def mark_purchased(id):
    """Mark shopping list item as purchased and update pantry inventory"""
    print(f"DEBUG: mark_purchased called with id={id}, user={current_user.id}")
    print(f"DEBUG: current_user type: {type(current_user.id)}, value: '{current_user.id}'")
    
    try:
        print(f"DEBUG: About to query for item {id} with user {current_user.id}")
        
        # Check if the user_id in the database might be stored differently
        all_items = ShoppingListItem.query.filter_by(id=id).all()
        print(f"DEBUG: All items with id {id}: {[(item.id, item.user_id, type(item.user_id)) for item in all_items]}")
        
        item = ShoppingListItem.query.filter_by(id=id, user_id=current_user.id).first()
        print(f"DEBUG: Query result for user match: {item}")
        
        # Also try string conversion
        item_alt = ShoppingListItem.query.filter_by(id=id, user_id=str(current_user.id)).first()
        print(f"DEBUG: Query result with string user_id: {item_alt}")
        
        if not item and not item_alt:
            print(f"DEBUG: Shopping list item {id} not found for user {current_user.id}")
            return jsonify({'success': False, 'error': 'Shopping list item not found'}), 404
        
        # Use whichever query worked
        item = item or item_alt
        print(f"DEBUG: Final item: {item.item_name}, is_purchased: {item.is_purchased}")
        
        if item.is_purchased:
            print(f"DEBUG: Item {id} already marked as purchased")
            return jsonify({
                'success': True, 
                'message': f'"{item.item_name}" was already marked as purchased'
            }), 200
            
    except Exception as e:
        print(f"DEBUG: Error finding shopping list item: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Database error finding item'}), 500
    
    # Get data from request - handle both JSON and form data
    if request.is_json:
        data = request.get_json() or {}
    elif request.form:
        data = request.form.to_dict()
    else:
        data = {}
    
    print(f"DEBUG: Request data: {data}")
    
    actual_cost = data.get('actual_cost')
    if actual_cost:
        try:
            actual_cost = float(actual_cost)
        except (ValueError, TypeError):
            actual_cost = None
    
    actual_quantity = data.get('actual_quantity', item.quantity_needed)
    if actual_quantity:
        try:
            actual_quantity = float(actual_quantity)
        except (ValueError, TypeError):
            actual_quantity = item.quantity_needed
    
    print(f"DEBUG: Parsed data - cost: {actual_cost}, quantity: {actual_quantity}")
    
    try:
        # Update pantry using the helper function
        success, pantry_message = update_pantry_from_purchase(item, actual_quantity, actual_cost)
        
        if not success:
            return jsonify({'success': False, 'error': pantry_message}), 500
        
        # Mark shopping list item as purchased
        item.is_purchased = True
        item.purchased_at = datetime.utcnow()
        if actual_cost:
            item.actual_cost = actual_cost
        
        # Commit all changes together
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Marked "{item.item_name}" as purchased and {pantry_message.lower()}'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        error_msg = str(e)
        print(f"Error marking item {id} as purchased: {error_msg}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Database error: {error_msg}'}), 500


@pantry_bp.route('/use_for_recipe', methods=['POST'])
@login_required
def use_for_recipe():
    """Reduce pantry quantities when cooking a recipe"""
    data = request.get_json()
    
    if not data or 'recipe_id' not in data:
        return jsonify({'success': False, 'error': 'Recipe ID is required'})
    
    try:
        recipe_id = data['recipe_id']
        servings_cooked = data.get('servings_cooked', 1)
        
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'})
        
        # Parse recipe ingredients and try to match with pantry items
        ingredients_text = recipe.ingredients.lower()
        ingredients_lines = [line.strip() for line in ingredients_text.split('\n') if line.strip()]
        
        updated_items = []
        warnings = []
        
        for ingredient_line in ingredients_lines:
            # Simple ingredient matching - try to find pantry items by name
            pantry_items = PantryItem.query.filter_by(user_id=current_user.id).all()
            
            for pantry_item in pantry_items:
                item_name_lower = pantry_item.name.lower()
                
                # Check if pantry item name appears in ingredient line
                if item_name_lower in ingredient_line:
                    # Estimate usage amount (this is simplified - in real app you'd want better parsing)
                    estimated_usage = 1.0 * servings_cooked  # Default to 1 unit per serving
                    
                    if pantry_item.current_quantity >= estimated_usage:
                        pantry_item.update_quantity(
                            estimated_usage, 
                            operation='subtract', 
                            reason='used_in_recipe'
                        )
                        updated_items.append({
                            'name': pantry_item.name,
                            'used': estimated_usage,
                            'remaining': pantry_item.current_quantity
                        })
                    else:
                        warnings.append(f'Not enough {pantry_item.name} in pantry')
                    
                    break  # Only match first pantry item per ingredient
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'updated_items': updated_items,
            'warnings': warnings,
            'message': f'Updated pantry for recipe: {recipe.title}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@pantry_bp.route('/analytics')
@login_required  
def analytics():
    """Pantry analytics and insights"""
    # Usage trends
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_usage = PantryUsageLog.query.filter_by(user_id=current_user.id)\
        .filter(PantryUsageLog.timestamp >= thirty_days_ago)\
        .order_by(PantryUsageLog.timestamp.desc()).all()
    
    # Most used items
    usage_by_item = {}
    for log in recent_usage:
        if log.reason == 'used_in_recipe' and log.quantity_change < 0:
            item_name = log.item.name if log.item else 'Unknown'
            usage_by_item[item_name] = usage_by_item.get(item_name, 0) + abs(log.quantity_change)
    
    most_used_items = sorted(usage_by_item.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Waste tracking (expired items)
    expired_logs = PantryUsageLog.query.filter_by(user_id=current_user.id, reason='expired')\
        .filter(PantryUsageLog.timestamp >= thirty_days_ago).all()
    
    # Cost analysis
    total_pantry_value = sum(item.total_cost or 0 for item in PantryItem.query.filter_by(user_id=current_user.id).all())
    monthly_purchases = sum(log.item.cost_per_unit * abs(log.quantity_change) for log in recent_usage 
                           if log.reason == 'purchased' and log.item and log.item.cost_per_unit)
    
    # Stock status distribution
    stock_status_data = {
        "labels": ["In Stock", "Low Stock", "Out of Stock"],
        "values": [
            PantryItem.query.filter(PantryItem.user_id == current_user.id, PantryItem.current_quantity > 0).count(),
            PantryItem.query.filter(PantryItem.user_id == current_user.id, PantryItem.current_quantity <= PantryItem.minimum_quantity).count(),
            PantryItem.query.filter(PantryItem.user_id == current_user.id, PantryItem.current_quantity == 0).count()
        ]
    }
    
    # Expiry distribution
    expiry_soon_count = PantryItem.query.filter_by(user_id=current_user.id)\
        .filter(PantryItem.expiry_date <= date.today() + timedelta(days=7)).count()
    expired_count = PantryItem.query.filter_by(user_id=current_user.id).filter(PantryItem.expiry_date < date.today()).count()
    
    expiry_data = {
        "labels": ["Not Expired", "Expiring Soon", "Expired"],
        "values": [
            PantryItem.query.filter_by(user_id=current_user.id).count() - expiry_soon_count - expired_count,
            expiry_soon_count,
            expired_count
        ]
    }
    
    # Recent usage logs (detailed)
    usage_logs = recent_usage[:10]  # Limit to 10 for display
    
    # Pass empty data if no logs
    stock_status_data = stock_status_data or {"labels": [], "values": []}
    expiry_data = expiry_data or {"labels": [], "values": []}
    return render_template(
        'pantry/analytics.html',
        stock_status_data=stock_status_data,
        expiry_data=expiry_data,
        usage_logs=usage_logs
    )


@pantry_bp.route('/get_uk_prices/<int:item_id>')
@login_required
def get_uk_prices(item_id):
    """Get UK supermarket price comparison for a shopping list item"""
    try:
        item = ShoppingListItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
        
        # Check if user has postcode for location-specific pricing
        user_postcode = getattr(current_user, 'postcode', None)
        
        if user_postcode:
            # Get location-specific pricing
            location_pricing = uk_price_service.get_location_specific_prices(
                item.item_name, item.quantity_needed, item.unit, user_postcode
            )
            
            # Also get general price comparison
            price_comparison = uk_price_service.get_supermarket_comparison(item.item_name)
            
            return jsonify({
                'success': True,
                'item_name': item.item_name,
                'quantity': item.quantity_needed,
                'unit': item.unit,
                'has_location_data': True,
                'postcode': user_postcode,
                'location_pricing': location_pricing,
                'general_comparison': price_comparison,
                'store_section': item.store_section
            })
        else:
            # Fall back to general UK pricing
            price_comparison = uk_price_service.get_supermarket_comparison(item.item_name)
            
            # Get estimated price for the specific quantity
            total_estimated = uk_price_service.estimate_uk_price(
                item.item_name, 
                item.quantity_needed, 
                item.unit
            )
            
            # Search Open Food Facts for product details
            product_info = uk_price_service.search_product_by_name(item.item_name)
            
            return jsonify({
                'success': True,
                'item_name': item.item_name,
                'quantity': item.quantity_needed,
                'unit': item.unit,
                'has_location_data': False,
                'price_comparison': price_comparison,
                'total_estimated': total_estimated,
                'product_info': product_info[:3] if product_info else [],  # Limit to top 3 matches
                'store_section': item.store_section
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@pantry_bp.route('/update_price_estimate/<int:item_id>', methods=['POST'])
@login_required
def update_price_estimate(item_id):
    """Update price estimate for a shopping list item"""
    try:
        item = ShoppingListItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
        data = request.get_json()
        
        new_price = data.get('estimated_cost')
        if new_price:
            item.estimated_cost = float(new_price)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Updated price estimate for {item.item_name}',
                'new_price': item.estimated_cost
            })
        else:
            return jsonify({'success': False, 'error': 'Price is required'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@pantry_bp.route('/get_pantry_status')
@login_required
def get_pantry_status():
    """Get current pantry status for dashboard updates"""
    try:
        # Get all user's pantry items
        pantry_items = PantryItem.query.filter_by(user_id=current_user.id).all()
        
        # Calculate statistics
        total_items = len(pantry_items)
        low_stock_count = len([item for item in pantry_items if item.is_low_stock])
        out_of_stock_count = len([item for item in pantry_items if item.current_quantity <= 0])
        total_value = sum(item.total_cost or 0 for item in pantry_items)
        
        # Get recent pantry items (last 5 updated)
        recent_items = sorted(
            pantry_items, 
            key=lambda x: x.updated_at or x.created_at, 
            reverse=True
        )[:5]
        
        recent_items_data = []
        for item in recent_items:
            recent_items_data.append({
                'id': item.id,
                'name': item.name,
                'current_quantity': item.current_quantity,
                'unit': item.unit,
                'is_low_stock': item.is_low_stock,
                'stock_status': item.stock_status
            })
        
        return jsonify({
            'success': True,
            'stats': {
                'total_items': total_items,
                'low_stock_count': low_stock_count,
                'out_of_stock_count': out_of_stock_count,
                'total_value': total_value
            },
            'recent_items': recent_items_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@pantry_bp.route('/get_shopping_list_comparison')
@login_required
def get_shopping_list_comparison():
    """Get location-specific price comparison for entire shopping list"""
    try:
        user_postcode = getattr(current_user, 'postcode', None)
        
        if not user_postcode:
            return jsonify({
                'success': False, 
                'error': 'Postcode required for location-specific pricing'
            })
        
        # Get active shopping list items
        shopping_items = ShoppingListItem.query.filter_by(
            user_id=current_user.id,
            is_purchased=False
        ).all()
        
        if not shopping_items:
            return jsonify({
                'success': False,
                'error': 'No items in shopping list'
            })
        
        # Get location-specific comparison
        comparison = uk_price_service.get_shopping_list_location_comparison(
            shopping_items, user_postcode
        )
        
        return jsonify({
            'success': True,
            'comparison': comparison
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@pantry_bp.route('/shopping_items')
@login_required
def list_shopping_items_json():
    """List user's shopping list items (non-weekly) as JSON."""
    try:
        items = ShoppingListItem.query.filter_by(user_id=current_user.id).order_by(ShoppingListItem.created_at.desc()).all()
        return jsonify({
            'success': True,
            'items': [item.to_dict() for item in items]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@pantry_bp.route('/shopping_items', methods=['POST'])
@login_required
def add_shopping_item_json():
    """Add a new shopping list item (non-weekly) via JSON."""
    try:
        data = request.get_json() or {}
        name = (data.get('name') or data.get('item_name') or '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Item name is required'}), 400
        category = (data.get('category') or 'Other').strip()
        quantity = data.get('quantity') or data.get('quantity_needed') or 1
        unit = (data.get('unit') or 'item').strip()
        priority = int(data.get('priority') or 3)
        notes = data.get('notes')
        estimated_cost = data.get('estimated_cost')

        try:
            quantity_val = float(quantity)
        except (TypeError, ValueError):
            quantity_val = 1.0

        item = ShoppingListItem(
            user_id=current_user.id,
            item_name=name,
            category=category,
            quantity_needed=quantity_val,
            unit=unit,
            source='manual',
            priority=priority,
            notes=notes,
            estimated_cost=float(estimated_cost) if estimated_cost is not None else None,
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'item': item.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@pantry_bp.route('/shopping_items/add_recipe', methods=['POST'])
@login_required
def add_recipe_ingredients_to_shopping_list():
    """Add a recipe's ingredients to the user's non-weekly shopping list as JSON.
    This performs server-side parsing and mapping to avoid exposing recipe data to the client.
    Request JSON: { "recipe_id": number, "servings": optional number }
    Response: { success, items_added, items_updated, message }
    """
    try:
        data = request.get_json() or {}
        recipe_id = data.get('recipe_id')
        servings = data.get('servings') or 1

        if not recipe_id:
            return jsonify({'success': False, 'error': 'Recipe ID required'}), 400

        try:
            servings = float(servings)
            if servings <= 0:
                servings = 1
        except (TypeError, ValueError):
            servings = 1

        # Load recipe without exposing details to the client
        recipe = Recipe.query.get(recipe_id)
        if not recipe:
            return jsonify({'success': False, 'error': 'Recipe not found'}), 404

        # Basic privacy check: block private recipes from other users
        if getattr(recipe, 'is_private', False) and recipe.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        ingredients_text = (recipe.ingredients or '').strip()
        if not ingredients_text:
            return jsonify({'success': False, 'error': 'Recipe has no ingredients to add'}), 400

        lines = [ln.strip() for ln in ingredients_text.split('\n') if ln.strip() and len(ln.strip()) > 2]
        items_added = 0
        items_updated = 0

        for line in lines:
            try:
                mapping = IngredientParser.parse_ingredient(line)

                # Compute quantity in purchasable units, scaled by servings
                base_qty = float(mapping.quantity or 1)
                conv = float(mapping.conversion_factor or 1)
                qty_needed = max(1.0, base_qty * conv * float(servings))

                # Find existing unpurchased item for this user with same product name
                existing = ShoppingListItem.query.filter_by(
                    user_id=current_user.id,
                    item_name=mapping.product_name,
                    is_purchased=False
                ).first()

                if existing:
                    try:
                        existing.quantity_needed = float(existing.quantity_needed or 0) + qty_needed
                    except (TypeError, ValueError):
                        existing.quantity_needed = qty_needed
                    # Only update unit/category if empty
                    if not getattr(existing, 'unit', None):
                        existing.unit = mapping.purchasable_unit
                    if not getattr(existing, 'category', None):
                        existing.category = mapping.category
                    # Append note minimally to avoid leaking full ingredient
                    if not existing.notes:
                        existing.notes = f'From recipe: {getattr(recipe, "title", "")[:40]}'
                    items_updated += 1
                else:
                    new_item = ShoppingListItem(
                        user_id=current_user.id,
                        item_name=mapping.product_name,
                        category=mapping.category,
                        quantity_needed=qty_needed,
                        unit=mapping.purchasable_unit,
                        source='recipe',
                        priority=3,
                        notes=f'From recipe: {getattr(recipe, "title", "")[:60]}'
                    )
                    db.session.add(new_item)
                    items_added += 1
            except Exception:
                # Skip problematic line, continue with others
                continue

        db.session.commit()

        message = f'Added {items_added} item(s)'
        if items_updated:
            message += f', updated {items_updated} existing'

        return jsonify({
            'success': True,
            'items_added': items_added,
            'items_updated': items_updated,
            'message': message
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

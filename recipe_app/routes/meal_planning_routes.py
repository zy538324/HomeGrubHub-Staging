from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from recipe_app.models import Recipe, User, MealPlan, MealPlanEntry, ShoppingListItem
from recipe_app.models.pantry_models import WeeklyShoppingList, WeeklyShoppingItem
from recipe_app.utils.smart_shopping import IngredientParser
from recipe_app.db import db
from datetime import datetime, timedelta, date
from recipe_app.main.analytics import UserEvent
import json

meal_planning_bp = Blueprint('meal_planning', __name__)

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

@meal_planning_bp.route('/meal-plan/list')
@login_required
def list_meal_plans():
    """API endpoint to get user's meal plans"""
    meal_plans = MealPlan.query.filter_by(user_id=current_user.id).all()
    
    plans_data = []
    for plan in meal_plans:
        plans_data.append({
            'id': plan.id,
            'name': plan.name,
            'start_date': plan.start_date.strftime('%Y-%m-%d'),
            'end_date': plan.end_date.strftime('%Y-%m-%d'),
            'is_active': plan.is_active
        })
    
    return jsonify({
        'success': True,
        'meal_plans': plans_data
    })

@meal_planning_bp.route('/shopping-list/add-recipe', methods=['POST'])
@login_required  
def add_recipe_to_shopping_list():
    """Add a recipe's ingredients to the weekly shopping list"""
    try:
        data = request.get_json()
        recipe_id = data.get('recipe_id')
        
        if not recipe_id:
            return jsonify({'success': False, 'error': 'Recipe ID required'})
        
        # Get recipe
        recipe = Recipe.query.get_or_404(recipe_id)
        
        # Get or create current week's shopping list
        weekly_list = get_or_create_current_week_list(current_user.id)
        
        items_added = 0
        items_skipped = 0
        
        # Parse ingredients and add to weekly shopping list
        if recipe.ingredients:
            ingredients_lines = recipe.ingredients.strip().split('\n')
            for ingredient_line in ingredients_lines:
                ingredient_line = ingredient_line.strip()
                if ingredient_line and len(ingredient_line) > 2:  # Skip very short lines
                    
                    # Use smart ingredient parser to convert to purchasable products
                    mapping = IngredientParser.parse_ingredient(ingredient_line)
                    
                    # Check if product already exists in this week's shopping list
                    existing_item = WeeklyShoppingItem.query.filter_by(
                        weekly_list_id=weekly_list.id,
                        item_name=mapping.product_name,
                        is_purchased=False
                    ).first()
                    
                    if not existing_item:
                        # Calculate realistic quantity needed based on purchasable units
                        quantity_needed = max(1, int(mapping.quantity * mapping.conversion_factor))
                        
                        shopping_item = WeeklyShoppingItem(
                            weekly_list_id=weekly_list.id,
                            item_name=mapping.product_name,
                            quantity_needed=quantity_needed,
                            unit=mapping.purchasable_unit,
                            category=mapping.category,
                            notes=f'From recipe: {recipe.title} (Original: {mapping.original_ingredient})',
                            source='meal_plan',
                            recipe_id=recipe_id
                        )
                        db.session.add(shopping_item)
                        items_added += 1
                    else:
                        # If item exists, optionally increase quantity if needed
                        items_skipped += 1
        
        db.session.commit()
        
        # Log the event
        event = UserEvent(
            user_id=current_user.id,
            event_type='recipe_added_to_weekly_shopping_list',
            event_data=f'Recipe: {recipe.title} (ID: {recipe_id}) added to week {weekly_list.week_label}'
        )
        db.session.add(event)
        db.session.commit()
        
        message = f'Added {items_added} ingredients to this week\'s shopping list'
        if items_skipped > 0:
            message += f' ({items_skipped} already in list)'
            
        return jsonify({
            'success': True, 
            'message': message,
            'items_added': items_added,
            'items_skipped': items_skipped,
            'week_label': weekly_list.week_label
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error adding recipe to shopping list: {e}")
        return jsonify({'success': False, 'error': 'Failed to add recipe to shopping list'})

@meal_planning_bp.route('/meal-planning')
@login_required
def meal_planner():
    """Main meal planning page"""
    if not current_user.can_access_feature('meal_planning'):
        flash('Meal planning is not available in your current plan.', 'warning')
        return redirect(url_for('billing.pricing'))
    
    # Get current meal plan or create one
    current_meal_plan = MealPlan.query.filter_by(user_id=current_user.id).first()
    
    # Calculate nutrition stats if available
    weekly_nutrition = {
        'total_calories': 0,
        'total_protein': 0,
        'total_recipes': 0,
        'unique_recipes': 0,
        'estimated_cost': 0.0,
        'avg_calories_per_day': 0,
        'avg_protein_per_day': 0,
        'cost_per_day': 0.0
    }
    
    if current_meal_plan:
        # Basic nutrition calculation (you can enhance this)
        planned_meals = current_meal_plan.planned_meals
        weekly_nutrition['total_recipes'] = len(planned_meals)
        weekly_nutrition['unique_recipes'] = len(set(meal.recipe_id for meal in planned_meals))
        
        # Mock calculations for now
        weekly_nutrition['total_calories'] = len(planned_meals) * 400  # Estimate
        weekly_nutrition['total_protein'] = len(planned_meals) * 25   # Estimate
        weekly_nutrition['estimated_cost'] = len(planned_meals) * 3.50  # Estimate
        
        if len(planned_meals) > 0:
            weekly_nutrition['avg_calories_per_day'] = weekly_nutrition['total_calories'] / 7
            weekly_nutrition['avg_protein_per_day'] = weekly_nutrition['total_protein'] / 7
            weekly_nutrition['cost_per_day'] = weekly_nutrition['estimated_cost'] / 7
    
    return render_template('meal_planning.html', 
                         current_meal_plan=current_meal_plan,
                         weekly_nutrition=weekly_nutrition,
                         timedelta=timedelta)

@meal_planning_bp.route('/meal-plan/drag-drop', methods=['POST'])
@login_required
def drag_drop_meal():
    """Handle drag and drop meal planning"""
    if not current_user.can_access_feature('meal_planning'):
        return jsonify({'success': False, 'error': 'Feature not available in your plan'}), 403
    
    data = request.get_json()
    recipe_id = data.get('recipe_id')
    day = data.get('day')
    meal_type = data.get('meal_type')
    meal_plan_id = data.get('meal_plan_id')
    servings = data.get('servings', 1)
    
    # Validate input
    recipe = Recipe.query.get_or_404(recipe_id)
    meal_plan = MealPlan.query.filter_by(id=meal_plan_id, user_id=current_user.id).first_or_404()
    
    # Check if meal already exists for this slot
    # Convert day index to actual date
    meal_date = meal_plan.start_date + timedelta(days=int(day))
    
    existing_meal = MealPlanEntry.query.filter_by(
        meal_plan_id=meal_plan_id,
        planned_date=meal_date,
        meal_type=meal_type
    ).first()
    
    if existing_meal:
        # Replace existing meal
        existing_meal.recipe_id = recipe_id
        existing_meal.planned_servings = servings
    else:
        # Create new planned meal
        planned_meal = MealPlanEntry(
            meal_plan_id=meal_plan_id,
            recipe_id=recipe_id,
            planned_date=meal_date,
            meal_type=meal_type,
            planned_servings=servings
        )
        db.session.add(planned_meal)
    
    db.session.commit()
    
    # Log event
    event = UserEvent(
        user_id=current_user.id,
        event_type='meal_planned',
        event_data=f'Recipe: {recipe.title}, Day: {day}, Meal: {meal_type}'
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Meal added to plan'})

@meal_planning_bp.route('/meal-plan/remove-meal/<int:meal_id>', methods=['DELETE'])
@login_required
def remove_meal(meal_id):
    """Remove a meal from the plan"""
    meal = MealPlanEntry.query.filter_by(id=meal_id).first_or_404()
    
    # Check ownership through meal plan
    if meal.meal_plan.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    db.session.delete(meal)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Meal removed'})

@meal_planning_bp.route('/meal-plan/shopping-list/<int:meal_plan_id>')
@login_required
def generate_shopping_list(meal_plan_id):
    """Generate shopping list from meal plan"""
    if not current_user.can_access_feature('shopping_list_generation'):
        flash('Shopping list generation requires Home plan', 'warning')
        return redirect(url_for('main.meal_planning'))
    
    meal_plan = MealPlan.query.filter_by(id=meal_plan_id, user_id=current_user.id).first_or_404()
    
    # Delete existing shopping list items for this meal plan
    ShoppingListItem.query.filter_by(
        user_id=current_user.id,
        source='meal_plan',
        meal_plan_id=meal_plan_id
    ).delete()
    
    # Aggregate ingredients from all planned meals
    ingredient_quantities = {}
    items_added = 0
    
    for planned_meal in meal_plan.planned_meals:
        recipe = planned_meal.recipe
        servings_multiplier = planned_meal.planned_servings / (recipe.servings or 1)
        
        # Parse ingredients (simplified - in production you'd want more sophisticated parsing)
        if recipe.ingredients:
            ingredients = recipe.ingredients.split('\n')
            for ingredient in ingredients:
                ingredient = ingredient.strip()
                if ingredient and len(ingredient) > 2:
                    # Simple aggregation - in production you'd parse quantities and units
                    if ingredient in ingredient_quantities:
                        ingredient_quantities[ingredient] += servings_multiplier
                    else:
                        ingredient_quantities[ingredient] = servings_multiplier
    
    # Create shopping list items
    for ingredient, quantity in ingredient_quantities.items():
        # Parse ingredient line to extract item name and quantity
        parts = ingredient.split(' ', 2)
        item_quantity = quantity
        unit = 'item'
        item_name = ingredient
        
        # Try to extract quantity if first part is a number
        try:
            if parts and len(parts) > 1:
                base_qty = float(parts[0])
                item_quantity = base_qty * quantity
                if len(parts) > 2:
                    unit = parts[1]
                    item_name = parts[2]
                else:
                    item_name = ' '.join(parts[1:])
        except ValueError:
            # If parsing fails, use the whole line as item name
            pass
        
        shopping_item = ShoppingListItem(
            user_id=current_user.id,
            item_name=item_name,
            quantity_needed=item_quantity,
            unit=unit,
            source='meal_plan',
            meal_plan_id=meal_plan_id,
            priority=3,
            notes=f'From meal plan: {meal_plan.name}'
        )
        db.session.add(shopping_item)
        items_added += 1
    
    db.session.commit()
    
    # Log event
    event = UserEvent(
        user_id=current_user.id,
        event_type='shopping_list_generated',
        event_data=f'Meal plan: {meal_plan.name}, Items: {len(ingredient_quantities)}'
    )
    db.session.add(event)
    db.session.commit()
    
    flash(f'Generated shopping list with {items_added} items from meal plan', 'success')
    return redirect(url_for('pantry.shopping_list'))

@meal_planning_bp.route('/meal-plan/duplicate/<int:meal_plan_id>')
@login_required
def duplicate_meal_plan(meal_plan_id):
    """Duplicate a meal plan for the next week"""
    if not current_user.can_access_feature('meal_planning'):
        flash('Meal planning requires Home plan', 'warning')
        return redirect(url_for('main.dashboard'))
    
    original_plan = MealPlan.query.filter_by(id=meal_plan_id, user_id=current_user.id).first_or_404()
    
    # Create new meal plan for next week
    new_start_date = original_plan.end_date + timedelta(days=1)
    new_end_date = new_start_date + timedelta(days=6)
    
    new_plan = MealPlan(
        user_id=current_user.id,
        name=f"{original_plan.name} (Copy)",
        start_date=new_start_date,
        end_date=new_end_date,
        created_at=datetime.utcnow()
    )
    db.session.add(new_plan)
    db.session.flush()
    
    # Copy all planned meals
    for planned_meal in original_plan.planned_meals:
        # Calculate the offset from original start date
        days_offset = (planned_meal.planned_date - original_plan.start_date).days
        new_planned_date = new_start_date + timedelta(days=days_offset)
        
        new_planned_meal = MealPlanEntry(
            meal_plan_id=new_plan.id,
            recipe_id=planned_meal.recipe_id,
            planned_date=new_planned_date,
            meal_type=planned_meal.meal_type,
            planned_servings=planned_meal.planned_servings
        )
        db.session.add(new_planned_meal)
    
    db.session.commit()
    
    flash(f'Meal plan duplicated for {new_start_date.strftime("%B %d")}', 'success')
    return redirect(url_for('main.meal_planning'))

@meal_planning_bp.route('/meal-plan/current.json')
@login_required
def current_meal_plan_json():
    """Return the current active meal plan and its entries as JSON (creates one if absent)."""
    # Try get active or most recent meal plan, else create this week
    plan = MealPlan.query.filter_by(user_id=current_user.id, is_active=True).order_by(MealPlan.start_date.desc()).first()
    if not plan:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        plan = MealPlan(
            user_id=current_user.id,
            name=f"Week of {monday.strftime('%Y-%m-%d')}",
            start_date=monday,
            end_date=monday + timedelta(days=6),
            is_active=True
        )
        db.session.add(plan)
        db.session.commit()
    entries = []
    for e in plan.planned_meals:
        entries.append({
            'id': e.id,
            'recipe_id': e.recipe_id,
            'recipe_title': getattr(e.recipe, 'title', None),
            'planned_date': e.planned_date.strftime('%Y-%m-%d'),
            'meal_type': e.meal_type,
            'planned_servings': e.planned_servings,
            'is_completed': e.is_completed
        })
    return jsonify({
        'success': True,
        'meal_plan': {
            'id': plan.id,
            'name': plan.name,
            'start_date': plan.start_date.strftime('%Y-%m-%d'),
            'end_date': plan.end_date.strftime('%Y-%m-%d'),
            'is_active': plan.is_active,
            'entries': entries
        }
    })

@meal_planning_bp.route('/meal-plan/<int:meal_plan_id>/entries.json')
@login_required
def meal_plan_entries_json(meal_plan_id):
    """Return entries for a given meal plan as JSON."""
    plan = MealPlan.query.filter_by(id=meal_plan_id, user_id=current_user.id).first_or_404()
    entries = []
    for e in plan.planned_meals:
        entries.append({
            'id': e.id,
            'recipe_id': e.recipe_id,
            'recipe_title': getattr(e.recipe, 'title', None),
            'planned_date': e.planned_date.strftime('%Y-%m-%d'),
            'meal_type': e.meal_type,
            'planned_servings': e.planned_servings,
            'is_completed': e.is_completed
        })
    return jsonify({'success': True, 'entries': entries})

@meal_planning_bp.route('/meal-plan/add-entry', methods=['POST'])
@login_required
def add_entry_by_date():
    """Add or replace a meal plan entry by explicit date (mobile-friendly).
    JSON: { meal_plan_id, recipe_id, planned_date: 'YYYY-MM-DD', meal_type, servings }
    """
    data = request.get_json() or {}
    meal_plan_id = data.get('meal_plan_id')
    recipe_id = data.get('recipe_id')
    planned_date_str = data.get('planned_date')
    meal_type = data.get('meal_type')
    servings = int(data.get('servings') or 1)

    if not all([meal_plan_id, recipe_id, planned_date_str, meal_type]):
        return jsonify({'success': False, 'error': 'meal_plan_id, recipe_id, planned_date, meal_type required'}), 400

    recipe = Recipe.query.get_or_404(recipe_id)
    plan = MealPlan.query.filter_by(id=meal_plan_id, user_id=current_user.id).first_or_404()

    try:
        planned_date = datetime.strptime(planned_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'planned_date must be YYYY-MM-DD'}), 400

    existing = MealPlanEntry.query.filter_by(
        meal_plan_id=meal_plan_id,
        planned_date=planned_date,
        meal_type=meal_type
    ).first()

    if existing:
        existing.recipe_id = recipe_id
        existing.planned_servings = servings
    else:
        entry = MealPlanEntry(
            meal_plan_id=meal_plan_id,
            recipe_id=recipe_id,
            planned_date=planned_date,
            meal_type=meal_type,
            planned_servings=servings
        )
        db.session.add(entry)

    db.session.commit()

    # Log event
    event = UserEvent(
        user_id=current_user.id,
        event_type='meal_planned',
        event_data=f'Recipe: {recipe.title}, Date: {planned_date_str}, Meal: {meal_type}'
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Meal added to plan'})

@meal_planning_bp.route('/meal-plan/generate-shopping-list.json', methods=['POST'])
@login_required
def generate_shopping_list_json():
    """Generate shopping list from a meal plan and return a JSON result (non-weekly list)."""
    if not current_user.can_access_feature('shopping_list_generation'):
        return jsonify({'success': False, 'error': 'Feature not available in your plan'}), 403

    data = request.get_json() or {}
    meal_plan_id = data.get('meal_plan_id')
    if not meal_plan_id:
        return jsonify({'success': False, 'error': 'meal_plan_id required'}), 400

    meal_plan = MealPlan.query.filter_by(id=meal_plan_id, user_id=current_user.id).first_or_404()

    # Clear prior meal_plan sourced items
    ShoppingListItem.query.filter_by(
        user_id=current_user.id,
        source='meal_plan',
        meal_plan_id=meal_plan_id
    ).delete()

    items_added = 0

    for planned_meal in meal_plan.planned_meals:
        recipe = planned_meal.recipe
        if not recipe or not recipe.ingredients:
            continue
        # Scale by servings where possible via IngredientParser
        lines = [ln.strip() for ln in recipe.ingredients.split('\n') if ln.strip() and len(ln.strip()) > 2]
        for line in lines:
            try:
                mapping = IngredientParser.parse_ingredient(line)
                base_qty = float(mapping.quantity or 1)
                conv = float(mapping.conversion_factor or 1)
                qty_needed = max(1.0, base_qty * conv * float(planned_meal.planned_servings or 1))

                item = ShoppingListItem(
                    user_id=current_user.id,
                    item_name=mapping.product_name,
                    category=mapping.category,
                    quantity_needed=qty_needed,
                    unit=mapping.purchasable_unit,
                    source='meal_plan',
                    meal_plan_id=meal_plan_id,
                    priority=3,
                    notes=f'From meal plan: {meal_plan.name}'
                )
                db.session.add(item)
                items_added += 1
            except Exception:
                continue

    db.session.commit()

    # Log event
    event = UserEvent(
        user_id=current_user.id,
        event_type='shopping_list_generated',
        event_data=f'Meal plan: {meal_plan.name}, Items: {items_added}'
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({'success': True, 'items_added': items_added, 'message': f'Added {items_added} items'})

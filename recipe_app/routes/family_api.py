"""
Family Tier API Routes
HomeGrubHub Multi-Tier Nutrition Platform
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_, func
import json
import string
import random

from recipe_app.db import db
from recipe_app.models.models import Recipe, User
from recipe_app.models.family_models import (
    FamilyAccount, FamilyMember, FamilyMealPlan, FamilyShoppingList,
    FamilyChallenge, FamilyChallengeProgress, FamilyAchievement
)
from recipe_app.models.nutrition_tracking import Food, Meal, NutritionLog
from recipe_app.models.fitness_models import WeightLog, WorkoutLog
from recipe_app.routes.nutrition_tracking_api import require_tier
from recipe_app.utils.family_decorators import check_parental_controls

# Create Family blueprint
family_bp = Blueprint('family', __name__, url_prefix='/family')

# ============================================================================
# FAMILY ACCOUNT MANAGEMENT
# ============================================================================

@family_bp.route('/dashboard')
@login_required
@require_tier(['family', 'pro'])
@check_parental_controls
def family_dashboard():
    """Main family dashboard with overview of all family members and activities"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        return redirect(url_for('family.create_family'))
    
    # Get family members with recent activity
    family_members = FamilyMember.query.filter_by(
        family_id=family_account.id,
        is_active=True
    ).options(joinedload(FamilyMember.user)).all()
    
    # Get recent family meal plans
    recent_meals = FamilyMealPlan.query.filter_by(
        family_id=family_account.id
    ).filter(
        FamilyMealPlan.date >= date.today() - timedelta(days=7)
    ).order_by(FamilyMealPlan.date.desc()).limit(10).all()
    
    # Get active family challenges
    active_challenges = FamilyChallenge.query.filter_by(
        family_id=family_account.id,
        is_active=True
    ).filter(
        FamilyChallenge.end_date >= date.today()
    ).all()
    
    # Calculate family nutrition summary
    family_nutrition = calculate_family_nutrition_summary(family_account.id)
    
    # Get recent achievements
    recent_achievements = FamilyAchievement.query.filter_by(
        family_id=family_account.id
    ).order_by(FamilyAchievement.earned_date.desc()).limit(5).all()
    
    return render_template('family/dashboard.html',
                         family_account=family_account,
                         family_members=family_members,
                         recent_meals=recent_meals,
                         active_challenges=active_challenges,
                         family_nutrition=family_nutrition,
                         recent_achievements=recent_achievements)


@family_bp.route('/member/<int:member_id>')
@login_required
@require_tier(['family', 'pro'])
@check_parental_controls
def member_detail(member_id):
    """View detailed information for a specific family member"""
    family_account = current_user.get_family_account()
    if not family_account:
        return redirect(url_for('family.create_family'))

    member = FamilyMember.query.filter_by(
        id=member_id, family_id=family_account.id
    ).first_or_404()

    viewer = FamilyMember.query.filter_by(
        family_id=family_account.id, user_id=current_user.id
    ).first()

    is_owner = family_account.primary_user_id == current_user.id
    if not (is_owner or (viewer and viewer.has_permission('view_all_data')) or (viewer and viewer.id == member.id)):
        flash('You do not have permission to view this member.', 'danger')
        return redirect(url_for('family.family_dashboard'))

    upcoming_meals = FamilyMealPlan.query.filter(
        FamilyMealPlan.family_id == family_account.id,
        FamilyMealPlan.assigned_cook == member.id,
        FamilyMealPlan.date >= date.today()
    ).order_by(FamilyMealPlan.date.asc()).limit(7).all()

    recent_nutrition = NutritionLog.query.filter_by(
        user_id=member.user_id
    ).order_by(NutritionLog.log_date.desc()).limit(7).all()

    recent_weights = WeightLog.query.filter_by(
        user_id=member.user_id
    ).order_by(WeightLog.log_date.desc()).limit(7).all()

    recent_workouts = WorkoutLog.query.filter_by(
        user_id=member.user_id
    ).order_by(WorkoutLog.workout_date.desc()).limit(7).all()

    return render_template(
        'family/member_detail.html',
        member=member,
        upcoming_meals=upcoming_meals,
        recent_nutrition=recent_nutrition,
        recent_weights=recent_weights,
        recent_workouts=recent_workouts
    )

@family_bp.route('/create-family')
@login_required
@require_tier(['family', 'pro'])
def create_family():
    """Create new family account interface"""
    # Check if user already has a family account
    if current_user.get_family_account():
        flash('You already have a family account!', 'info')
        return redirect(url_for('family.family_dashboard'))
    
    return render_template('family/create_family.html')

@family_bp.route('/create-family', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def create_family_post():
    """Create new family account"""
    try:
        data = request.get_json() if request.is_json else request.form
        family_name = data.get('family_name', '').strip()
        max_members = int(data.get('max_members', 6))
        
        if not family_name:
            return jsonify({'success': False, 'message': 'Family name is required'})
        
        if max_members < 2 or max_members > 6:
            return jsonify({'success': False, 'message': 'Family size must be between 2-6 members'})
        
        # Create family account
        family_account = FamilyAccount(
            primary_user_id=current_user.id,
            family_name=family_name,
            max_members=max_members
        )
        family_account.generate_family_code()
        
        db.session.add(family_account)
        db.session.flush()  # Get the family ID
        
        # Add primary user as admin family member
        primary_member = FamilyMember(
            family_id=family_account.id,
            user_id=current_user.id,
            role='admin',
            age_group='adult',
            display_name=current_user.username or 'Admin',
            permissions={
                'manage_members': True,
                'manage_meals': True,
                'manage_budget': True,
                'create_challenges': True,
                'view_all_data': True
            }
        )
        
        db.session.add(primary_member)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Family account created successfully!',
            'family_code': family_account.family_code,
            'redirect': url_for('family.family_dashboard')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creating family: {str(e)}'})

@family_bp.route('/join-family')
@login_required
@require_tier(['family', 'pro'])
def join_family():
    """Join existing family account interface"""
    if current_user.get_family_account():
        flash('You are already part of a family account!', 'info')
        return redirect(url_for('family.family_dashboard'))
    
    return render_template('family/join_family.html')

@family_bp.route('/join-family', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def join_family_post():
    """Join existing family account using family code"""
    try:
        data = request.get_json() if request.is_json else request.form
        family_code = data.get('family_code', '').strip().upper()
        display_name = data.get('display_name', '').strip()
        age_group = data.get('age_group', 'adult')
        
        if not family_code:
            return jsonify({'success': False, 'message': 'Family code is required'})
        
        if not display_name:
            return jsonify({'success': False, 'message': 'Display name is required'})
        
        # Find family account
        family_account = FamilyAccount.query.filter_by(
            family_code=family_code,
            subscription_status='active'
        ).first()
        
        if not family_account:
            return jsonify({'success': False, 'message': 'Invalid family code'})
        
        # Check if family is full
        current_member_count = FamilyMember.query.filter_by(
            family_id=family_account.id,
            is_active=True
        ).count()
        
        if current_member_count >= family_account.max_members:
            return jsonify({'success': False, 'message': 'This family account is full'})
        
        # Check if user is already a member
        existing_member = FamilyMember.query.filter_by(
            family_id=family_account.id,
            user_id=current_user.id
        ).first()
        
        if existing_member:
            return jsonify({'success': False, 'message': 'You are already a member of this family'})
        
        # Add user as family member
        role = 'child' if age_group == 'child' else 'teen' if age_group == 'teen' else 'member'
        
        family_member = FamilyMember(
            family_id=family_account.id,
            user_id=current_user.id,
            role=role,
            age_group=age_group,
            display_name=display_name,
            permissions={
                'manage_members': False,
                'manage_meals': role != 'child',
                'manage_budget': False,
                'create_challenges': role != 'child',
                'view_all_data': False
            }
        )
        
        db.session.add(family_member)
        
        # Update family member count
        family_account.current_members = current_member_count + 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Welcome to the {family_account.family_name} family!',
            'redirect': url_for('family.family_dashboard')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error joining family: {str(e)}'})

@family_bp.route('/manage-members')
@login_required
@require_tier(['family', 'pro'])
def manage_members():
    """Family member management interface"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        return redirect(url_for('family.create_family'))
    
    # Check if user has permission to manage members
    user_member = FamilyMember.query.filter_by(
        family_id=family_account.id,
        user_id=current_user.id
    ).first()
    
    if not user_member or not user_member.has_permission('manage_members'):
        flash('You do not have permission to manage family members', 'error')
        return redirect(url_for('family.family_dashboard'))
    
    family_members = FamilyMember.query.filter_by(
        family_id=family_account.id
    ).options(joinedload(FamilyMember.user)).all()
    
    return render_template('family/manage_members.html',
                         family_account=family_account,
                         family_members=family_members)

@family_bp.route('/update-member-role', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def update_member_role():
    """Update family member role and permissions"""
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        new_role = data.get('new_role')
        
        # Get family account and check permissions
        family_account = current_user.get_family_account()
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        user_member = FamilyMember.query.filter_by(
            family_id=family_account.id,
            user_id=current_user.id
        ).first()
        
        if not user_member or not user_member.has_permission('manage_members'):
            return jsonify({'success': False, 'message': 'Permission denied'})
        
        # Get target member
        target_member = FamilyMember.query.filter_by(
            id=member_id,
            family_id=family_account.id
        ).first()
        
        if not target_member:
            return jsonify({'success': False, 'message': 'Member not found'})
        
        # Cannot change primary user role
        if target_member.user_id == family_account.primary_user_id:
            return jsonify({'success': False, 'message': 'Cannot change primary user role'})
        
        # Update role and permissions
        target_member.role = new_role
        target_member.permissions = get_default_permissions(new_role)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Updated {target_member.display_name} role to {new_role}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating role: {str(e)}'})

@family_bp.route('/invite-member', methods=['POST'])
@login_required
def invite_member():
    """Invite a new member to the family"""
    # Manual tier check instead of decorator
    if not current_user.can_access_feature('family_sharing'):
        flash('Family features require a Family or Pro subscription.', 'error')
        return redirect(url_for('billing.pricing'))
        
    family_account = current_user.get_family_account()
    
    if not family_account:
        flash('You must be part of a family to invite members.', 'error')
        return redirect(url_for('family.create_family'))
    
    # Check if user has permission to invite members
    user_member = FamilyMember.query.filter_by(
        family_id=family_account.id,
        user_id=current_user.id
    ).first()
    
    if not user_member or not user_member.has_permission('manage_members'):
        flash('You do not have permission to invite family members.', 'error')
        return redirect(url_for('family.manage_members'))
    
    try:
        email = request.form.get('email')
        role = request.form.get('role', 'child')
        message = request.form.get('message', '')
        
        # Check if user already exists
        from recipe_app.models.models import User
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            # Check if already a family member
            existing_member = FamilyMember.query.filter_by(
                family_id=family_account.id,
                user_id=existing_user.id
            ).first()
            
            if existing_member:
                flash(f'{email} is already a member of this family.', 'warning')
                return redirect(url_for('family.manage_members'))
        
        # For now, we'll create a simple invitation system
        # In a real application, you'd send an email invitation
        if existing_user:
            # Add user directly to family if they already have an account
            new_member = FamilyMember(
                family_id=family_account.id,
                user_id=existing_user.id,
                role=role,
                is_active=True,
                joined_at=datetime.utcnow()
            )
            db.session.add(new_member)
            db.session.commit()
            
            flash(f'Successfully added {existing_user.username} to the family!', 'success')
        else:
            # For non-existing users, we'll show a message
            # In a real app, you'd create an invitation record and send an email
            flash(f'Invitation functionality coming soon! For now, {email} needs to create an account first, then you can add them to the family.', 'info')
        
        return redirect(url_for('family.manage_members'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error inviting member: {str(e)}', 'error')
        return redirect(url_for('family.manage_members'))

@family_bp.route('/remove-member', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def remove_member():
    """Remove family member from family account"""
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        
        # Get family account and check permissions
        family_account = current_user.get_family_account()
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        user_member = FamilyMember.query.filter_by(
            family_id=family_account.id,
            user_id=current_user.id
        ).first()
        
        if not user_member or not user_member.has_permission('manage_members'):
            return jsonify({'success': False, 'message': 'Permission denied'})
        
        # Get target member
        target_member = FamilyMember.query.filter_by(
            id=member_id,
            family_id=family_account.id
        ).first()
        
        if not target_member:
            return jsonify({'success': False, 'message': 'Member not found'})
        
        # Cannot remove primary user
        if target_member.user_id == family_account.primary_user_id:
            return jsonify({'success': False, 'message': 'Cannot remove primary user'})
        
        # Soft delete - set as inactive
        target_member.is_active = False
        
        # Update family member count
        family_account.current_members = FamilyMember.query.filter_by(
            family_id=family_account.id,
            is_active=True
        ).count() - 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Removed {target_member.display_name} from family'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error removing member: {str(e)}'})

@family_bp.route('/meal-planning')
@login_required
@require_tier(['family', 'pro'])
def family_meal_planning():
    """Family meal planning calendar interface"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        return redirect(url_for('family.create_family'))
    
    # Get current week's meal plans
    week_offset = request.args.get('week', 0, type=int)
    start_date = date.today() + timedelta(weeks=week_offset)
    start_date = start_date - timedelta(days=start_date.weekday())  # Start of week (Monday)
    
    end_date = start_date + timedelta(days=6)
    
    meal_plans = FamilyMealPlan.query.filter_by(
        family_id=family_account.id
    ).filter(
        and_(FamilyMealPlan.date >= start_date, FamilyMealPlan.date <= end_date)
    ).options(
        joinedload(FamilyMealPlan.cook),
        joinedload(FamilyMealPlan.recipe)
    ).all()
    
    # Get family members for cooking assignments
    family_members = FamilyMember.query.filter_by(
        family_id=family_account.id,
        is_active=True
    ).all()
    
    # Get saved family recipes
    saved_recipes = Recipe.query.filter_by(
        user_id=family_account.primary_user_id
    ).limit(50).all()
    
    # Calculate weekly statistics
    total_planned_meals = len(meal_plans)
    unique_cooks = len(set(plan.assigned_cook for plan in meal_plans if plan.assigned_cook))
    estimated_prep_time = sum(plan.prep_time or 0 for plan in meal_plans)
    estimated_cost = sum(plan.estimated_cost or 0 for plan in meal_plans)
    
    # Cooking assignments
    cooking_assignments = []
    cook_counts = {}
    for plan in meal_plans:
        if plan.cook:
            cook_counts[plan.cook.display_name] = cook_counts.get(plan.cook.display_name, 0) + 1
    
    for cook_name, count in cook_counts.items():
        cooking_assignments.append({'cook_name': cook_name, 'meal_count': count})
    
    # Convert meal plans to JSON for JavaScript
    meal_plans_json = {}
    for plan in meal_plans:
        meal_plans_json[plan.id] = {
            'id': plan.id,
            'date': plan.date.isoformat(),
            'meal_type': plan.meal_type,
            'recipe_id': plan.recipe_id,
            'recipe_name': plan.recipe_name or (plan.recipe.title if plan.recipe else ''),  # Fixed: was .name, should be .title
            'assigned_cook': plan.assigned_cook,
            'servings_planned': plan.servings_planned,
            'prep_time': plan.prep_time,
            'difficulty_level': plan.difficulty_level,
            'cooking_notes': plan.cooking_notes
        }
    
    return render_template('family/meal_planning.html',
                         family_account=family_account,
                         meal_plans=meal_plans,
                         meal_plans_json=json.dumps(meal_plans_json),
                         family_members=family_members,
                         saved_recipes=saved_recipes,
                         start_date=start_date,
                         week_offset=week_offset,
                         total_planned_meals=total_planned_meals,
                         unique_cooks=unique_cooks,
                         estimated_prep_time=estimated_prep_time,
                         estimated_cost=estimated_cost,
                         cooking_assignments=cooking_assignments,
                         get_meal_plan=get_meal_plan_helper,
                         timedelta=timedelta)

@family_bp.route('/save-meal-plan', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def save_meal_plan():
    """Save or update family meal plan"""
    try:
        data = request.get_json()
        family_account = current_user.get_family_account()
        
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        # Check if updating existing meal plan
        meal_plan_id = data.get('id')
        if meal_plan_id:
            meal_plan = FamilyMealPlan.query.filter_by(
                id=meal_plan_id,
                family_id=family_account.id
            ).first()
            
            if not meal_plan:
                return jsonify({'success': False, 'message': 'Meal plan not found'})
        else:
            # Create new meal plan
            meal_plan = FamilyMealPlan(family_id=family_account.id)
        
        # Update meal plan data
        meal_plan.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        meal_plan.meal_type = data['meal_type']
        meal_plan.recipe_id = data.get('recipe_id')
        meal_plan.recipe_name = data.get('recipe_name')
        meal_plan.assigned_cook = data.get('assigned_cook') or None
        meal_plan.servings_planned = data.get('servings_planned', 1)
        meal_plan.prep_time = data.get('prep_time')
        meal_plan.difficulty_level = data.get('difficulty_level', 'medium')
        meal_plan.cooking_notes = data.get('cooking_notes', '')
        meal_plan.member_preferences = data.get('member_preferences', {})
        
        # Set creator if new meal plan
        if not meal_plan_id:
            current_member = FamilyMember.query.filter_by(
                family_id=family_account.id,
                user_id=current_user.id
            ).first()
            meal_plan.created_by = current_member.id if current_member else None
        
        if not meal_plan_id:
            db.session.add(meal_plan)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Meal plan saved successfully!',
            'meal_plan_id': meal_plan.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error saving meal plan: {str(e)}'})

@family_bp.route('/delete-meal-plan', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def delete_meal_plan():
    """Delete family meal plan"""
    try:
        data = request.get_json()
        meal_plan_id = data.get('id')
        
        family_account = current_user.get_family_account()
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        meal_plan = FamilyMealPlan.query.filter_by(
            id=meal_plan_id,
            family_id=family_account.id
        ).first()
        
        if not meal_plan:
            return jsonify({'success': False, 'message': 'Meal plan not found'})
        
        db.session.delete(meal_plan)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Meal plan deleted successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting meal plan: {str(e)}'})

# ============================================================================
# FAMILY SHOPPING LIST MANAGEMENT
# ============================================================================

@family_bp.route('/shopping')
@login_required
@require_tier(['family', 'pro'])
def family_shopping():
    """Family shopping list management interface"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        return redirect(url_for('family.create_family'))
    
    # Get family shopping list
    shopping_items = FamilyShoppingList.query.filter_by(
        family_id=family_account.id,
        purchased=False
    ).options(
        joinedload(FamilyShoppingList.requester),
        joinedload(FamilyShoppingList.meal_plan)
    ).order_by(
        FamilyShoppingList.priority.desc(),
        FamilyShoppingList.category,
        FamilyShoppingList.item_name
    ).all()
    
    # Group by category
    shopping_by_category = {}
    total_estimated_cost = 0
    
    for item in shopping_items:
        category = item.category or 'Other'
        if category not in shopping_by_category:
            shopping_by_category[category] = []
        shopping_by_category[category].append(item)
        total_estimated_cost += item.estimated_cost or 0
    
    # Get family members for requests
    family_members = FamilyMember.query.filter_by(
        family_id=family_account.id,
        is_active=True
    ).all()
    
    # Get recent purchases
    recent_purchases = FamilyShoppingList.query.filter_by(
        family_id=family_account.id,
        purchased=True
    ).order_by(FamilyShoppingList.purchased_at.desc()).limit(20).all()
    
    # Category icon helper function
    def get_category_icon(category):
        icons = {
            'Produce': 'apple-alt',
            'Meat & Seafood': 'fish', 
            'Dairy': 'cheese',
            'Pantry': 'box',
            'Frozen': 'snowflake',
            'Beverages': 'coffee',
            'Snacks': 'cookie',
            'Household': 'home',
            'Other': 'shopping-basket'
        }
        return icons.get(category, 'shopping-basket')
    
    return render_template('family/shopping.html',
                         family_account=family_account,
                         shopping_by_category=shopping_by_category,
                         total_estimated_cost=total_estimated_cost,
                         family_members=family_members,
                         recent_purchases=recent_purchases,
                         get_category_icon=get_category_icon)

@family_bp.route('/add-shopping-item', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def add_shopping_item():
    """Add item to family shopping list"""
    try:
        data = request.get_json()
        family_account = current_user.get_family_account()
        
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        # Get current family member
        current_member = FamilyMember.query.filter_by(
            family_id=family_account.id,
            user_id=current_user.id
        ).first()
        
        # Create shopping item
        shopping_item = FamilyShoppingList(
            family_id=family_account.id,
            item_name=data['item_name'],
            category=data.get('category', 'Other'),
            quantity=data.get('quantity', 1),
            unit=data.get('unit'),
            brand=data.get('brand'),
            priority=data.get('priority', 'medium'),
            estimated_cost=data.get('estimated_cost'),
            notes=data.get('notes'),
            requested_by=current_member.id if current_member else None
        )
        
        db.session.add(shopping_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item added to shopping list!',
            'item_id': shopping_item.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error adding item: {str(e)}'})

@family_bp.route('/mark-purchased', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def mark_purchased():
    """Mark shopping item as purchased"""
    try:
        data = request.get_json()
        item_id = data.get('id')
        
        family_account = current_user.get_family_account()
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        shopping_item = FamilyShoppingList.query.filter_by(
            id=item_id,
            family_id=family_account.id
        ).first()
        
        if not shopping_item:
            return jsonify({'success': False, 'message': 'Item not found'})
        
        shopping_item.purchased = True
        shopping_item.purchased_at = datetime.now()
        
        # Record who marked it as purchased
        current_member = FamilyMember.query.filter_by(
            family_id=family_account.id,
            user_id=current_user.id
        ).first()
        
        if current_member:
            shopping_item.purchased_by = current_member.id
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item marked as purchased!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error marking as purchased: {str(e)}'})

@family_bp.route('/remove-shopping-item', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def remove_shopping_item():
    """Remove item from shopping list"""
    try:
        data = request.get_json()
        item_id = data.get('id')
        
        family_account = current_user.get_family_account()
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        shopping_item = FamilyShoppingList.query.filter_by(
            id=item_id,
            family_id=family_account.id
        ).first()
        
        if not shopping_item:
            return jsonify({'success': False, 'message': 'Item not found'})
        
        db.session.delete(shopping_item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item removed from shopping list!'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error removing item: {str(e)}'})

@family_bp.route('/generate-shopping-from-meals', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def generate_shopping_from_meals():
    """Generate shopping list items from upcoming meal plans"""
    try:
        family_account = current_user.get_family_account()
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        # Get upcoming meal plans (next 7 days)
        start_date = date.today()
        end_date = start_date + timedelta(days=7)
        
        meal_plans = FamilyMealPlan.query.filter_by(
            family_id=family_account.id
        ).filter(
            and_(FamilyMealPlan.date >= start_date, FamilyMealPlan.date <= end_date)
        ).options(joinedload(FamilyMealPlan.recipe)).all()
        
        current_member = FamilyMember.query.filter_by(
            family_id=family_account.id,
            user_id=current_user.id
        ).first()
        
        items_added = 0
        
        # Generate shopping items from recipes
        for meal_plan in meal_plans:
            if meal_plan.recipe and hasattr(meal_plan.recipe, 'ingredients'):
                # This would integrate with recipe ingredients
                # For now, create generic items based on meal types
                generic_items = get_generic_meal_ingredients(meal_plan.meal_type, meal_plan.recipe_name)
                
                for item_data in generic_items:
                    # Check if item already exists
                    existing = FamilyShoppingList.query.filter_by(
                        family_id=family_account.id,
                        item_name=item_data['name'],
                        purchased=False
                    ).first()
                    
                    if not existing:
                        shopping_item = FamilyShoppingList(
                            family_id=family_account.id,
                            item_name=item_data['name'],
                            category=item_data['category'],
                            quantity=item_data['quantity'],
                            unit=item_data.get('unit'),
                            priority='medium',
                            meal_plan_id=meal_plan.id,
                            requested_by=current_member.id if current_member else None,
                            notes=f"For {meal_plan.recipe_name or 'planned meal'} on {meal_plan.date.strftime('%b %d')}"
                        )
                        
                        db.session.add(shopping_item)
                        items_added += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Added {items_added} items from meal plans!',
            'items_added': items_added
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error generating shopping list: {str(e)}'})

@family_bp.route('/mark-all-purchased', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def mark_all_purchased():
    """Mark all shopping items as purchased"""
    try:
        family_account = current_user.get_family_account()
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        current_member = FamilyMember.query.filter_by(
            family_id=family_account.id,
            user_id=current_user.id
        ).first()
        
        # Update all unpurchased items
        items_updated = FamilyShoppingList.query.filter_by(
            family_id=family_account.id,
            purchased=False
        ).update({
            'purchased': True,
            'purchased_at': datetime.now(),
            'purchased_by': current_member.id if current_member else None
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Marked {items_updated} items as purchased!',
            'items_updated': items_updated
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error marking all as purchased: {str(e)}'})

@family_bp.route('/export-shopping-list')
@login_required
@require_tier(['family', 'pro'])
def export_shopping_list():
    """Export shopping list as text file"""
    family_account = current_user.get_family_account()
    if not family_account:
        return redirect(url_for('family.create_family'))
    
    # Get shopping items grouped by category
    shopping_items = FamilyShoppingList.query.filter_by(
        family_id=family_account.id,
        purchased=False
    ).order_by(
        FamilyShoppingList.category,
        FamilyShoppingList.item_name
    ).all()
    
    # Group by category
    shopping_by_category = {}
    for item in shopping_items:
        category = item.category or 'Other'
        if category not in shopping_by_category:
            shopping_by_category[category] = []
        shopping_by_category[category].append(item)
    
    # Generate text content
    content = f"{family_account.family_name} Shopping List\n"
    content += f"Generated on {date.today().strftime('%B %d, %Y')}\n"
    content += "=" * 50 + "\n\n"
    
    for category, items in shopping_by_category.items():
        content += f"{category.upper()}\n"
        content += "-" * len(category) + "\n"
        
        for item in items:
            content += f"☐ {item.item_name}"
            if item.quantity and item.quantity != 1:
                content += f" (Qty: {item.quantity}"
                if item.unit:
                    content += f" {item.unit}"
                content += ")"
            if item.brand:
                content += f" - {item.brand}"
            if item.priority == 'high':
                content += " [HIGH PRIORITY]"
            content += "\n"
            
            if item.notes:
                content += f"   Note: {item.notes}\n"
        
        content += "\n"
    
    # Return as downloadable file
    from flask import Response
    return Response(
        content,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename="{family_account.family_name.replace(" ", "_")}_shopping_list.txt"'
        }
    )

# ============================================================================
# FAMILY CHALLENGES MANAGEMENT
# ============================================================================

@family_bp.route('/challenges')
@login_required
@require_tier(['family', 'pro'])
def family_challenges():
    """Family challenges and achievements interface"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        return redirect(url_for('family.create_family'))
    
    # Get active challenges
    active_challenges = FamilyChallenge.query.filter_by(
        family_id=family_account.id,
        is_active=True
    ).filter(
        FamilyChallenge.end_date >= date.today()
    ).options(joinedload(FamilyChallenge.progress_entries)).all()
    
    # Get completed challenges
    completed_challenges = FamilyChallenge.query.filter_by(
        family_id=family_account.id,
        is_completed=True
    ).order_by(FamilyChallenge.completion_date.desc()).limit(10).all()
    
    # Get family achievements
    family_achievements = FamilyAchievement.query.filter_by(
        family_id=family_account.id
    ).options(joinedload(FamilyAchievement.member)).order_by(
        FamilyAchievement.earned_date.desc()
    ).limit(20).all()
    
    # Get family members
    family_members = FamilyMember.query.filter_by(
        family_id=family_account.id,
        is_active=True
    ).all()
    
    # Helper function for challenge icons
    def get_challenge_icon(challenge_type):
        icons = {
            'cooking': 'utensils',
            'meal_planning': 'calendar-alt',
            'healthy_eating': 'apple-alt',
            'exercise': 'running',
            'custom': 'star'
        }
        return icons.get(challenge_type, 'trophy')
    
    return render_template('family/challenges.html',
                         family_account=family_account,
                         active_challenges=active_challenges,
                         completed_challenges=completed_challenges,
                         family_achievements=family_achievements,
                         family_members=family_members,
                         get_challenge_icon=get_challenge_icon,
                         date=date,
                         timedelta=timedelta)

@family_bp.route('/create-challenge', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def create_challenge():
    """Create new family challenge"""
    try:
        data = request.get_json()
        family_account = current_user.get_family_account()
        
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        # Check permissions
        current_member = FamilyMember.query.filter_by(
            family_id=family_account.id,
            user_id=current_user.id
        ).first()
        
        if not current_member or not current_member.has_permission('create_challenges'):
            return jsonify({'success': False, 'message': 'Permission denied'})
        
        # Create challenge
        challenge = FamilyChallenge(
            family_id=family_account.id,
            title=data['title'],
            description=data.get('description', ''),
            challenge_type=data.get('challenge_type', 'custom'),
            target_value=data['target_value'],
            unit=data.get('unit', 'points'),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
            rewards=data.get('rewards'),
            created_by=current_member.id
        )
        
        db.session.add(challenge)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Challenge created successfully!',
            'challenge_id': challenge.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error creating challenge: {str(e)}'})

@family_bp.route('/log-challenge-progress', methods=['POST'])
@login_required
@require_tier(['family', 'pro'])
def log_challenge_progress():
    """Log progress for family challenge"""
    try:
        data = request.get_json()
        challenge_id = data.get('challenge_id')
        progress_amount = data.get('progress', 0)
        
        family_account = current_user.get_family_account()
        if not family_account:
            return jsonify({'success': False, 'message': 'No family account found'})
        
        # Get challenge
        challenge = FamilyChallenge.query.filter_by(
            id=challenge_id,
            family_id=family_account.id
        ).first()
        
        if not challenge:
            return jsonify({'success': False, 'message': 'Challenge not found'})
        
        if not challenge.is_active or challenge.end_date < date.today():
            return jsonify({'success': False, 'message': 'Challenge is not active'})
        
        # Get current member
        current_member = FamilyMember.query.filter_by(
            family_id=family_account.id,
            user_id=current_user.id
        ).first()
        
        # Log progress
        progress_entry = FamilyChallengeProgress(
            challenge_id=challenge.id,
            member_id=current_member.id if current_member else None,
            progress_amount=progress_amount,
            notes=data.get('notes', '')
        )
        
        db.session.add(progress_entry)
        
        # Update challenge progress
        challenge.current_progress = (challenge.current_progress or 0) + progress_amount
        
        # Check if challenge is completed
        if challenge.current_progress >= challenge.target_value:
            challenge.is_completed = True
            challenge.completion_date = date.today()
            
            # Award achievements
            award_challenge_achievements(challenge, family_account)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Progress logged successfully!',
            'new_progress': challenge.current_progress,
            'challenge_completed': challenge.is_completed
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error logging progress: {str(e)}'})

@family_bp.route('/family-achievements')
@login_required
@require_tier(['family', 'pro'])
def family_achievements_list():
    """Get family achievements list"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        return jsonify({'success': False, 'message': 'No family account found'})
    
    achievements = FamilyAchievement.query.filter_by(
        family_id=family_account.id
    ).options(joinedload(FamilyAchievement.member)).order_by(
        FamilyAchievement.earned_date.desc()
    ).all()
    
    achievements_data = []
    for achievement in achievements:
        achievements_data.append({
            'id': achievement.id,
            'achievement_name': achievement.achievement_name,
            'achievement_description': achievement.achievement_description,
            'member_name': achievement.member.display_name if achievement.member else 'Family',
            'earned_date': achievement.earned_date.strftime('%Y-%m-%d'),
            'badge_data': achievement.badge_data
        })
    
    return jsonify({
        'success': True,
        'achievements': achievements_data
    })

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_family_nutrition_summary(family_id):
    """Calculate comprehensive family nutrition summary"""
    try:
        # Get all family members
        family_members = FamilyMember.query.filter_by(
            family_id=family_id,
            is_active=True
        ).all()
        
        if not family_members:
            return {}
        
        # Calculate family nutrition metrics for last 7 days
        end_date = date.today()
        start_date = end_date - timedelta(days=6)
        
        family_nutrition = {
            'total_members': len(family_members),
            'avg_daily_calories': 0,
            'avg_daily_protein': 0,
            'avg_daily_carbs': 0,
            'avg_daily_fat': 0,
            'family_health_score': 0,
            'top_performing_member': None,
            'improvement_areas': [],
            'weekly_trend': 'stable'
        }
        
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        member_scores = {}
        
        for member in family_members:
            # Get member's recent meals
            member_meals = Meal.query.filter_by(
                user_id=member.user_id
            ).filter(
                and_(Meal.meal_date >= start_date, Meal.meal_date <= end_date)
            ).all()
            
            member_calories = sum(meal.calories or 0 for meal in member_meals) / 7
            member_protein = sum(meal.protein or 0 for meal in member_meals) / 7
            member_carbs = sum(meal.carbohydrates or 0 for meal in member_meals) / 7
            member_fat = sum(meal.fat or 0 for meal in member_meals) / 7
            
            total_calories += member_calories
            total_protein += member_protein
            total_carbs += member_carbs
            total_fat += member_fat
            
            # Calculate member health score (simplified)
            member_score = calculate_member_health_score(member_calories, member_protein, member_carbs, member_fat, member.age_group)
            member_scores[member.display_name] = member_score
        
        # Calculate averages
        family_nutrition['avg_daily_calories'] = round(total_calories / len(family_members))
        family_nutrition['avg_daily_protein'] = round(total_protein / len(family_members), 1)
        family_nutrition['avg_daily_carbs'] = round(total_carbs / len(family_members), 1)
        family_nutrition['avg_daily_fat'] = round(total_fat / len(family_members), 1)
        
        # Calculate family health score
        family_nutrition['family_health_score'] = round(sum(member_scores.values()) / len(member_scores), 1)
        
        # Find top performing member
        if member_scores:
            family_nutrition['top_performing_member'] = max(member_scores, key=member_scores.get)
        
        return family_nutrition
        
    except Exception as e:
        print(f"Error calculating family nutrition summary: {e}")
        return {}

def calculate_member_health_score(calories, protein, carbs, fat, age_group):
    """Calculate health score for family member based on age group"""
    try:
        # Age-appropriate calorie targets
        calorie_targets = {
            'child': 1800,
            'teen': 2200,
            'adult': 2000
        }
        
        target_calories = calorie_targets.get(age_group, 2000)
        
        # Basic scoring algorithm
        calorie_score = max(0, 100 - abs(calories - target_calories) / target_calories * 100)
        protein_score = min(100, (protein / (target_calories * 0.15 / 4)) * 100)  # 15% of calories from protein
        
        # Average the scores
        health_score = (calorie_score + protein_score) / 2
        
        return max(1, min(10, health_score / 10))
        
    except Exception:
        return 5.0  # Default neutral score

def get_default_permissions(role):
    """Get default permissions for family member role"""
    permissions = {
        'admin': {
            'manage_members': True,
            'manage_meals': True,
            'manage_budget': True,
            'create_challenges': True,
            'view_all_data': True
        },
        'parent': {
            'manage_members': False,
            'manage_meals': True,
            'manage_budget': True,
            'create_challenges': True,
            'view_all_data': True
        },
        'member': {
            'manage_members': False,
            'manage_meals': True,
            'manage_budget': False,
            'create_challenges': True,
            'view_all_data': False
        },
        'teen': {
            'manage_members': False,
            'manage_meals': True,
            'manage_budget': False,
            'create_challenges': True,
            'view_all_data': False
        },
        'child': {
            'manage_members': False,
            'manage_meals': False,
            'manage_budget': False,
            'create_challenges': False,
            'view_all_data': False
        }
    }
    
    return permissions.get(role, permissions['member'])

def get_meal_plan_helper(meal_plans, target_date, meal_type):
    """Helper function to get meal plan for specific date and meal type"""
    for plan in meal_plans:
        if plan.date == target_date and plan.meal_type == meal_type:
            return plan
    return None

def calculate_family_health_score(family_account):
    """Calculate family health score based on meal planning and achievements"""
    score = 70  # Base score
    
    # Meal planning consistency (last 7 days)
    recent_meal_plans = FamilyMealPlan.query.filter_by(
        family_id=family_account.id
    ).filter(
        FamilyMealPlan.date >= date.today() - timedelta(days=7)
    ).count()
    
    if recent_meal_plans >= 14:  # 2 meals per day
        score += 15
    elif recent_meal_plans >= 7:  # 1 meal per day
        score += 10
    elif recent_meal_plans >= 3:  # Few meals planned
        score += 5
    
    # Family challenge participation
    active_challenges = FamilyChallenge.query.filter_by(
        family_id=family_account.id,
        is_active=True
    ).count()
    
    score += min(active_challenges * 3, 10)
    
    # Recent achievements
    recent_achievements = FamilyAchievement.query.filter_by(
        family_id=family_account.id
    ).filter(
        FamilyAchievement.earned_date >= date.today() - timedelta(days=30)
    ).count()
    
    score += min(recent_achievements * 2, 10)
    
    return min(score, 100)  # Cap at 100

def get_family_activity_data(family_account, days=30):
    """Get family activity data for dashboard analytics"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    # Get meal planning activity
    meal_plans = FamilyMealPlan.query.filter_by(
        family_id=family_account.id
    ).filter(
        and_(FamilyMealPlan.date >= start_date, FamilyMealPlan.date <= end_date)
    ).all()
    
    # Get shopping activity
    shopping_items = FamilyShoppingList.query.filter_by(
        family_id=family_account.id
    ).filter(
        FamilyShoppingList.created_at >= start_date
    ).all()
    
    # Get challenge activity
    challenges = FamilyChallenge.query.filter_by(
        family_id=family_account.id
    ).filter(
        FamilyChallenge.start_date >= start_date
    ).all()
    
    # Get achievements
    achievements = FamilyAchievement.query.filter_by(
        family_id=family_account.id
    ).filter(
        FamilyAchievement.earned_date >= start_date
    ).all()
    
    return {
        'meal_plans_count': len(meal_plans),
        'shopping_items_count': len(shopping_items),
        'challenges_count': len(challenges),
        'achievements_count': len(achievements),
        'active_days': len(set(
            [plan.date for plan in meal_plans] +
            [item.created_at.date() for item in shopping_items] +
            [challenge.start_date for challenge in challenges] +
            [achievement.earned_date for achievement in achievements]
        ))
    }

def get_generic_meal_ingredients(meal_type, recipe_name=None):
    """Generate generic ingredients based on meal type and recipe name"""
    # This is a simplified implementation
    # In a full system, this would integrate with a recipe database
    
    base_ingredients = {
        'breakfast': [
            {'name': 'Eggs', 'category': 'Dairy', 'quantity': 6, 'unit': 'pieces'},
            {'name': 'Bread', 'category': 'Pantry', 'quantity': 1, 'unit': 'loaf'},
            {'name': 'Milk', 'category': 'Dairy', 'quantity': 1, 'unit': 'gallon'},
            {'name': 'Cereal', 'category': 'Pantry', 'quantity': 1, 'unit': 'box'},
        ],
        'lunch': [
            {'name': 'Lunch Meat', 'category': 'Meat & Seafood', 'quantity': 1, 'unit': 'lb'},
            {'name': 'Cheese Slices', 'category': 'Dairy', 'quantity': 1, 'unit': 'package'},
            {'name': 'Lettuce', 'category': 'Produce', 'quantity': 1, 'unit': 'head'},
            {'name': 'Tomatoes', 'category': 'Produce', 'quantity': 2, 'unit': 'pieces'},
        ],
        'dinner': [
            {'name': 'Chicken Breast', 'category': 'Meat & Seafood', 'quantity': 2, 'unit': 'lbs'},
            {'name': 'Rice', 'category': 'Pantry', 'quantity': 1, 'unit': 'bag'},
            {'name': 'Mixed Vegetables', 'category': 'Frozen', 'quantity': 1, 'unit': 'bag'},
            {'name': 'Onions', 'category': 'Produce', 'quantity': 2, 'unit': 'pieces'},
        ],
        'snack': [
            {'name': 'Apples', 'category': 'Produce', 'quantity': 6, 'unit': 'pieces'},
            {'name': 'Crackers', 'category': 'Snacks', 'quantity': 1, 'unit': 'box'},
            {'name': 'Cheese Sticks', 'category': 'Dairy', 'quantity': 1, 'unit': 'package'},
        ]
    }
    
    ingredients = base_ingredients.get(meal_type, base_ingredients['dinner'])
    
    # Customize based on recipe name if provided
    if recipe_name:
        recipe_lower = recipe_name.lower()
        
        if 'pasta' in recipe_lower:
            ingredients = [
                {'name': 'Pasta', 'category': 'Pantry', 'quantity': 1, 'unit': 'box'},
                {'name': 'Pasta Sauce', 'category': 'Pantry', 'quantity': 1, 'unit': 'jar'},
                {'name': 'Ground Beef', 'category': 'Meat & Seafood', 'quantity': 1, 'unit': 'lb'},
                {'name': 'Parmesan Cheese', 'category': 'Dairy', 'quantity': 1, 'unit': 'container'},
            ]
        elif 'taco' in recipe_lower:
            ingredients = [
                {'name': 'Taco Shells', 'category': 'Pantry', 'quantity': 1, 'unit': 'box'},
                {'name': 'Ground Beef', 'category': 'Meat & Seafood', 'quantity': 1, 'unit': 'lb'},
                {'name': 'Taco Seasoning', 'category': 'Pantry', 'quantity': 1, 'unit': 'packet'},
                {'name': 'Lettuce', 'category': 'Produce', 'quantity': 1, 'unit': 'head'},
                {'name': 'Tomatoes', 'category': 'Produce', 'quantity': 2, 'unit': 'pieces'},
                {'name': 'Shredded Cheese', 'category': 'Dairy', 'quantity': 1, 'unit': 'bag'},
            ]
        elif 'salad' in recipe_lower:
            ingredients = [
                {'name': 'Mixed Greens', 'category': 'Produce', 'quantity': 1, 'unit': 'bag'},
                {'name': 'Carrots', 'category': 'Produce', 'quantity': 3, 'unit': 'pieces'},
                {'name': 'Cucumber', 'category': 'Produce', 'quantity': 1, 'unit': 'piece'},
                {'name': 'Salad Dressing', 'category': 'Pantry', 'quantity': 1, 'unit': 'bottle'},
            ]
        elif 'soup' in recipe_lower:
            ingredients = [
                {'name': 'Broth', 'category': 'Pantry', 'quantity': 2, 'unit': 'cans'},
                {'name': 'Mixed Vegetables', 'category': 'Frozen', 'quantity': 1, 'unit': 'bag'},
                {'name': 'Carrots', 'category': 'Produce', 'quantity': 3, 'unit': 'pieces'},
                {'name': 'Celery', 'category': 'Produce', 'quantity': 3, 'unit': 'stalks'},
            ]
    
    return ingredients[:4]  # Limit to 4 ingredients per meal

def award_challenge_achievements(challenge, family_account):
    """Award achievements when challenges are completed"""
    try:
        # Get all family members
        family_members = FamilyMember.query.filter_by(
            family_id=family_account.id,
            is_active=True
        ).all()
        
        # Award challenge completion achievement
        achievement_name = f"{challenge.title} Champion"
        achievement_description = f"Successfully completed the '{challenge.title}' family challenge!"
        
        # Award to all family members
        for member in family_members:
            # Check if already earned
            existing = FamilyAchievement.query.filter_by(
                family_id=family_account.id,
                member_id=member.id,
                achievement_name=achievement_name
            ).first()
            
            if not existing:
                achievement = FamilyAchievement(
                    family_id=family_account.id,
                    member_id=member.id,
                    achievement_name=achievement_name,
                    achievement_description=achievement_description,
                    badge_data={
                        'type': challenge.challenge_type,
                        'challenge_id': challenge.id,
                        'target_value': challenge.target_value,
                        'unit': challenge.unit
                    }
                )
                db.session.add(achievement)
        
        # Check for milestone achievements
        completed_challenges_count = FamilyChallenge.query.filter_by(
            family_id=family_account.id,
            is_completed=True
        ).count()
        
        milestone_achievements = {
            1: "First Family Challenge",
            5: "Challenge Enthusiast", 
            10: "Challenge Master",
            25: "Challenge Legend"
        }
        
        if completed_challenges_count in milestone_achievements:
            milestone_name = milestone_achievements[completed_challenges_count]
            milestone_description = f"Completed {completed_challenges_count} family challenges together!"
            
            for member in family_members:
                existing = FamilyAchievement.query.filter_by(
                    family_id=family_account.id,
                    member_id=member.id,
                    achievement_name=milestone_name
                ).first()
                
                if not existing:
                    achievement = FamilyAchievement(
                        family_id=family_account.id,
                        member_id=member.id,
                        achievement_name=milestone_name,
                        achievement_description=milestone_description,
                        badge_data={
                            'type': 'milestone',
                            'milestone': completed_challenges_count,
                            'category': 'challenges'
                        }
                    )
                    db.session.add(achievement)
    
    except Exception as e:
        print(f"Error awarding achievements: {e}")


def get_family_member_permissions(role):
    """Get permissions for family member based on role"""
    permissions = {
        'admin': {
            'manage_members': True,
            'manage_meals': True,
            'manage_budget': True,
            'create_challenges': True,
            'view_all_data': True
        },
        'parent': {
            'manage_members': True,  # Can manage children only
            'manage_meals': True,
            'manage_budget': True,
            'create_challenges': True,
            'view_all_data': True
        },
        'member': {
            'manage_members': False,
            'manage_meals': True,
            'manage_budget': False,
            'create_challenges': True,
            'view_all_data': False
        }
    }
    
    return permissions.get(role, permissions['member'])

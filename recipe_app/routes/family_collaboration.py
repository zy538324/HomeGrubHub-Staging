"""
Enhanced Family Collaboration Routes
Handles cooking assignments, recipe collections, messaging, and shopping coordination
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from recipe_app.db import db
from recipe_app.models.family_models import (
    FamilyAccount, FamilyMember, FamilyMealPlan, 
    FamilyShoppingList, FamilyChallenge, FamilyMessage
)
from recipe_app.models.family_collaboration import (
    FamilyCookingAssignment, FamilyRecipeCollection, 
    FamilyShoppingRequest
)
from recipe_app.models.models import Recipe

# Create blueprint
family_collab_bp = Blueprint('family_collab', __name__, url_prefix='/family')


# Cooking Assignments
@family_collab_bp.route('/cooking-assignments')
@login_required
def cooking_assignments():
    """Display and manage family cooking assignments"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        flash('You must be part of a family to view cooking assignments.', 'error')
        return redirect(url_for('family.create_family'))
    
    # Get family member
    family_member = current_user.get_family_member_record()
    if not family_member:
        flash('Family member profile not found.', 'error')
        return redirect(url_for('family.family_dashboard'))
    
    # Get current and upcoming assignments
    current_assignments = FamilyCookingAssignment.query.filter_by(
        family_id=family_account.id
    ).filter(
        FamilyCookingAssignment.cooking_date >= date.today()
    ).order_by(FamilyCookingAssignment.cooking_date.asc()).all()
    
    # Get assignment statistics
    assignment_stats = {
        'total_assignments': FamilyCookingAssignment.query.filter_by(family_id=family_account.id).count(),
        'completed_this_week': FamilyCookingAssignment.query.filter_by(
            family_id=family_account.id, status='completed'
        ).filter(
            FamilyCookingAssignment.completed_at >= datetime.now() - timedelta(weeks=1)
        ).count(),
        'upcoming_assignments': len([a for a in current_assignments if a.status in ['assigned', 'accepted']]),
        'most_active_cook': 'John'  # Placeholder
    }
    
    # Get family members
    family_members = FamilyMember.query.filter_by(family_id=family_account.id).all()
    
    return render_template('family/cooking_assignments.html',
                         family_account=family_account,
                         current_member=family_member,
                         current_assignments=current_assignments,
                         assignment_stats=assignment_stats,
                         family_members=family_members,
                         today=date.today())


@family_collab_bp.route('/create-cooking-assignment', methods=['POST'])
@login_required
def create_cooking_assignment():
    """Create a new cooking assignment"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        flash('You must be part of a family to create assignments.', 'error')
        return redirect(url_for('family.create_family'))
    
    try:
        # Create new cooking assignment
        assignment = FamilyCookingAssignment(
            family_id=family_account.id,
            assigned_by=current_user.get_family_member_record().id,
            assigned_member_id=int(request.form['assigned_member_id']),
            cooking_date=datetime.strptime(request.form['cooking_date'], '%Y-%m-%d').date(),
            meal_types=request.form.getlist('meal_types'),
            required_skill_level=request.form.get('required_skill_level', 'intermediate'),
            estimated_time_minutes=int(request.form['estimated_time_minutes']) if request.form.get('estimated_time_minutes') else None,
            cooking_notes=request.form.get('cooking_notes'),
            prep_instructions=request.form.get('prep_instructions'),
            assignment_type=request.form.get('assignment_type', 'specific'),
            recurring_pattern=request.form.get('recurring_pattern') if request.form.get('assignment_type') == 'recurring' else None,
            helper_members=request.form.getlist('helper_members')
        )
        
        db.session.add(assignment)
        db.session.commit()
        flash('Cooking assignment created successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating assignment: {str(e)}', 'error')
    
    return redirect(url_for('family_collab.cooking_assignments'))


# Recipe Collection
@family_collab_bp.route('/recipe-collection')
@login_required
def family_recipe_collection():
    """Display family recipe collection with ratings and favorites"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        flash('You must be part of a family to view recipe collection.', 'error')
        return redirect(url_for('family.create_family'))
    
    # Get family recipes with search/filter
    search_query = request.args.get('search', '')
    category_filter = request.args.get('category', '')
    rating_filter = request.args.get('rating', '')
    added_by_filter = request.args.get('added_by', '')
    
    family_recipes_query = FamilyRecipeCollection.query.filter_by(family_id=family_account.id)
    
    if search_query:
        family_recipes_query = family_recipes_query.join(Recipe).filter(
            Recipe.name.ilike(f'%{search_query}%')
        )
    
    family_recipes = family_recipes_query.all()
    
    # Get collection statistics
    collection_stats = {
        'total_recipes': len(family_recipes),
        'avg_rating': 4.2,  # Placeholder
        'recipes_cooked_this_month': 12,  # Placeholder
        'family_favorites': len([r for r in family_recipes if r.is_family_favorite])
    }
    
    # Get family members
    family_members = FamilyMember.query.filter_by(family_id=family_account.id).all()
    
    # Get recent activity (placeholder)
    recent_activity = []
    top_favorites = [r for r in family_recipes if r.is_family_favorite][:5]
    
    return render_template('family/recipe_collection.html',
                         family_account=family_account,
                         family_recipes=family_recipes,
                         collection_stats=collection_stats,
                         family_members=family_members,
                         recent_activity=recent_activity,
                         top_favorites=top_favorites)


@family_collab_bp.route('/add-recipe-to-collection', methods=['POST'])
@login_required
def add_recipe_to_collection():
    """Add a recipe to the family collection"""
    family_account = current_user.get_family_account()
    family_member = current_user.get_family_member_record()
    
    if not family_account or not family_member:
        flash('Family membership required.', 'error')
        return redirect(url_for('family.family_dashboard'))
    
    try:
        # This is a simplified version - in reality you'd parse the URL and create a recipe
        recipe_url = request.form['recipe_url']
        family_notes = request.form.get('family_notes', '')
        is_favorite = 'is_family_favorite' in request.form
        
        # For demo purposes, create a placeholder recipe entry
        flash('Recipe added to family collection! (Demo mode)', 'success')
        
    except Exception as e:
        flash(f'Error adding recipe: {str(e)}', 'error')
    
    return redirect(url_for('family_collab.family_recipe_collection'))


# Family Messages
@family_collab_bp.route('/messages')
@login_required
def family_messages():
    """Display family message center"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        flash('You must be part of a family to view messages.', 'error')
        return redirect(url_for('family.create_family'))
    
    # Get family messages
    family_messages_list = FamilyMessage.query.filter_by(
        family_id=family_account.id
    ).order_by(FamilyMessage.created_at.desc()).limit(50).all()
    
    # Get message statistics
    message_stats = {
        'total_messages': FamilyMessage.query.filter_by(family_id=family_account.id).count(),
        'messages_this_week': FamilyMessage.query.filter_by(family_id=family_account.id).filter(
            FamilyMessage.created_at >= datetime.now() - timedelta(weeks=1)
        ).count(),
        'active_conversations': 5,  # Placeholder
        'most_active_member': 'Mom'  # Placeholder
    }
    
    # Get family members
    family_members = FamilyMember.query.filter_by(family_id=family_account.id).all()
    
    return render_template('family/messages.html',
                         family_account=family_account,
                         family_messages=family_messages_list,
                         message_stats=message_stats,
                         family_members=family_members,
                         today=date.today())


@family_collab_bp.route('/send-message', methods=['POST'])
@login_required
def send_family_message():
    """Send a message to the family"""
    family_account = current_user.get_family_account()
    family_member = current_user.get_family_member_record()
    
    if not family_account or not family_member:
        flash('Family membership required.', 'error')
        return redirect(url_for('family.family_dashboard'))
    
    try:
        message = FamilyMessage(
            family_id=family_account.id,
            sender_id=family_member.id,
            message=request.form['content'],
            message_type=request.form.get('message_type', 'general'),
            priority=request.form.get('priority', 'normal')
        )
        
        db.session.add(message)
        db.session.commit()
        flash('Message sent successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error sending message: {str(e)}', 'error')
    
    return redirect(url_for('family_collab.family_messages'))


# Shopping Coordination
@family_collab_bp.route('/shopping-coordination')
@login_required
def shopping_coordination():
    """Display shopping coordination center"""
    family_account = current_user.get_family_account()
    
    if not family_account:
        flash('You must be part of a family to view shopping coordination.', 'error')
        return redirect(url_for('family.create_family'))
    
    # Get shopping requests
    shopping_requests = FamilyShoppingRequest.query.filter_by(
        family_id=family_account.id
    ).order_by(FamilyShoppingRequest.created_at.desc()).all()
    
    # Get shopping statistics
    shopping_stats = {
        'total_requests': len(shopping_requests),
        'pending_requests': len([r for r in shopping_requests if r.status == 'pending']),
        'approved_requests': len([r for r in shopping_requests if r.status == 'approved']),
        'weekly_budget': 150.00  # Placeholder
    }
    
    # Get family members
    family_members = FamilyMember.query.filter_by(family_id=family_account.id).all()
    
    return render_template('family/shopping_coordination.html',
                         family_account=family_account,
                         shopping_requests=shopping_requests,
                         shopping_stats=shopping_stats,
                         family_members=family_members,
                         today=date.today(),
                         upcoming_shopping=[],  # Placeholder
                         family_budget=None)  # Placeholder


@family_collab_bp.route('/create-shopping-request', methods=['POST'])
@login_required
def create_shopping_request():
    """Create a new shopping request"""
    family_account = current_user.get_family_account()
    family_member = current_user.get_family_member_record()
    
    if not family_account or not family_member:
        flash('Family membership required.', 'error')
        return redirect(url_for('family.family_dashboard'))
    
    try:
        # Create shopping request
        request_obj = FamilyShoppingRequest(
            family_id=family_account.id,
            requested_by=family_member.id,
            shopping_items=request.form['shopping_items'],
            needed_by_date=datetime.strptime(request.form['needed_by_date'], '%Y-%m-%d').date() if request.form.get('needed_by_date') else None,
            priority=request.form.get('priority', 'normal'),
            estimated_cost=float(request.form['estimated_cost']) if request.form.get('estimated_cost') else None,
            notes=request.form.get('notes', ''),
            requires_approval='requires_approval' in request.form
        )
        
        db.session.add(request_obj)
        db.session.commit()
        flash('Shopping request created successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating shopping request: {str(e)}', 'error')
    
    return redirect(url_for('family_collab.shopping_coordination'))


# AJAX Endpoints for dynamic updates
@family_collab_bp.route('/accept-cooking-assignment/<int:assignment_id>', methods=['POST'])
@login_required
def accept_cooking_assignment(assignment_id):
    """Accept a cooking assignment"""
    try:
        assignment = FamilyCookingAssignment.query.get_or_404(assignment_id)
        assignment.status = 'accepted'
        assignment.accepted_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Assignment accepted!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@family_collab_bp.route('/rate-recipe/<int:collection_id>', methods=['POST'])
@login_required
def rate_recipe(collection_id):
    """Rate a recipe in the family collection"""
    try:
        # This would use the FamilyRecipeRating model
        flash('Recipe rated successfully! (Demo mode)', 'success')
        return jsonify({'success': True, 'message': 'Recipe rated!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@family_collab_bp.route('/toggle-recipe-favorite/<int:collection_id>', methods=['POST'])
@login_required
def toggle_recipe_favorite(collection_id):
    """Toggle recipe favorite status"""
    try:
        recipe_collection = FamilyRecipeCollection.query.get_or_404(collection_id)
        recipe_collection.is_family_favorite = not recipe_collection.is_family_favorite
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'is_favorite': recipe_collection.is_family_favorite,
            'message': 'Favorite status updated!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@family_collab_bp.route('/approve-shopping-request/<int:request_id>', methods=['POST'])
@login_required
def approve_shopping_request(request_id):
    """Approve a shopping request"""
    try:
        shopping_request = FamilyShoppingRequest.query.get_or_404(request_id)
        family_member = current_user.get_family_member_record()
        
        # Check if user can approve (parent/guardian)
        if family_member.role not in ['parent', 'guardian']:
            return jsonify({'success': False, 'message': 'Only parents/guardians can approve requests'})
        
        shopping_request.status = 'approved'
        shopping_request.approved_by = family_member.id
        shopping_request.approved_at = datetime.utcnow()
        shopping_request.approval_notes = request.form.get('approval_notes', '')
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Shopping request approved!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

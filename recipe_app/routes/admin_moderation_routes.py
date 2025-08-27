from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from .. import db
from recipe_app.models.models import Recipe, User, RecipeReview, RecipePhoto, RecipeCollection
from recipe_app.models.advanced_models import Challenge, ChallengeParticipation
from datetime import datetime
from ..main.analytics import UserEvent, log_fault

admin_moderation_bp = Blueprint('admin_moderation', __name__)

@admin_moderation_bp.route('/admin/moderation')
@login_required
def moderation_dashboard():
    """Admin moderation dashboard"""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get recipes needing moderation (reported, recent uploads, etc.)
    recent_recipes = Recipe.query.order_by(Recipe.created_at.desc()).limit(20).all()
    flagged_reviews = RecipeReview.query.filter_by(is_flagged=True).all() if hasattr(RecipeReview, 'is_flagged') else []
    
    # Get statistics
    stats = {
        'total_recipes': Recipe.query.count(),
        'recipes_today': Recipe.query.filter(Recipe.created_at >= datetime.utcnow().date()).count(),
        'total_reviews': RecipeReview.query.count(),
        'flagged_content': len(flagged_reviews),
        'active_users': User.query.filter_by(is_active=True).count()
    }
    
    return render_template('admin/moderation.html', 
                         recent_recipes=recent_recipes,
                         flagged_reviews=flagged_reviews,
                         stats=stats)

@admin_moderation_bp.route('/admin/recipe/<int:recipe_id>/moderate', methods=['POST'])
@login_required
def moderate_recipe(recipe_id):
    """Moderate a recipe (approve, reject, feature)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    recipe = Recipe.query.get_or_404(recipe_id)
    action = request.json.get('action')
    reason = request.json.get('reason', '')
    
    if action == 'approve':
        recipe.is_approved = True
        recipe.moderation_notes = f"Approved by {current_user.username}: {reason}"
        message = 'Recipe approved'
        
    elif action == 'reject':
        recipe.is_approved = False
        recipe.is_private = True  # Make private if rejected
        recipe.moderation_notes = f"Rejected by {current_user.username}: {reason}"
        message = 'Recipe rejected and made private'
        
    elif action == 'feature':
        recipe.is_featured = True
        recipe.featured_at = datetime.utcnow()
        recipe.moderation_notes = f"Featured by {current_user.username}: {reason}"
        message = 'Recipe featured'
        
    elif action == 'unfeature':
        recipe.is_featured = False
        recipe.featured_at = None
        message = 'Recipe unfeatured'
        
    else:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    
    db.session.commit()
    
    # Log moderation action
    event = UserEvent(
        user_id=current_user.id,
        event_type='recipe_moderated',
        event_data=f'Recipe: {recipe.title}, Action: {action}, Admin: {current_user.username}'
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify({'success': True, 'message': message})

@admin_moderation_bp.route('/admin/challenges')
@login_required
def manage_challenges():
    """Manage cooking challenges"""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    challenges = Challenge.query.order_by(Challenge.created_at.desc()).all()
    return render_template('admin/challenges.html', challenges=challenges)

@admin_moderation_bp.route('/admin/challenges/create', methods=['POST'])
@login_required
def create_challenge():
    """Create a new cooking challenge"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    data = request.json
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    challenge_type = data.get('type', 'weekly')
    start_date = datetime.fromisoformat(data.get('start_date'))
    end_date = datetime.fromisoformat(data.get('end_date'))
    
    if not title:
        return jsonify({'success': False, 'error': 'Title is required'}), 400
    
    challenge = Challenge(
        title=title,
        description=description,
        challenge_type=challenge_type,
        start_date=start_date,
        end_date=end_date,
        created_at=datetime.utcnow()
    )
    
    db.session.add(challenge)
    db.session.commit()
    
    # Log event
    event = UserEvent(
        user_id=current_user.id,
        event_type='challenge_created',
        event_data=f'Challenge: {title}, Type: {challenge_type}'
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Challenge created successfully'})

@admin_moderation_bp.route('/admin/featured-recipes')
@login_required
def featured_recipes_admin():
    """Manage featured recipes"""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get currently featured recipes
    featured = Recipe.query.filter_by(is_featured=True).order_by(Recipe.featured_at.desc()).all()
    
    # Get candidate recipes for featuring (high rated, not yet featured)
    candidates = Recipe.query.join(RecipeReview).group_by(Recipe.id).having(
        db.func.avg(RecipeReview.rating) >= 4.0
    ).filter(Recipe.is_featured == False).order_by(
        db.func.count(RecipeReview.id).desc()
    ).limit(20).all()
    
    return render_template('admin/featured_recipes.html', 
                         featured=featured, 
                         candidates=candidates)

@admin_moderation_bp.route('/admin/content-reports')
@login_required
def content_reports():
    """View and manage content reports"""
    if not current_user.is_admin:
        flash('Admin access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # This would require a ContentReport model for user reports
    # For now, show recent content for manual review
    recent_reviews = RecipeReview.query.order_by(RecipeReview.created_at.desc()).limit(50).all()
    recent_photos = RecipePhoto.query.order_by(RecipePhoto.created_at.desc()).limit(20).all()
    
    return render_template('admin/content_reports.html',
                         recent_reviews=recent_reviews,
                         recent_photos=recent_photos)

@admin_moderation_bp.route('/admin/review/<int:review_id>/moderate', methods=['POST'])
@login_required
def moderate_review(review_id):
    """Moderate a review"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    review = RecipeReview.query.get_or_404(review_id)
    action = request.json.get('action')
    
    if action == 'approve':
        review.is_approved = True
        message = 'Review approved'
    elif action == 'delete':
        db.session.delete(review)
        message = 'Review deleted'
    else:
        return jsonify({'success': False, 'error': 'Invalid action'}), 400
    
    db.session.commit()
    
    # Log moderation action
    event = UserEvent(
        user_id=current_user.id,
        event_type='review_moderated',
        event_data=f'Review ID: {review_id}, Action: {action}, Admin: {current_user.username}'
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify({'success': True, 'message': message})

@admin_moderation_bp.route('/admin/bulk-actions', methods=['POST'])
@login_required
def bulk_actions():
    """Perform bulk moderation actions"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    data = request.json
    action = data.get('action')
    item_type = data.get('type')  # 'recipe', 'review', 'photo'
    item_ids = data.get('ids', [])
    
    if not item_ids:
        return jsonify({'success': False, 'error': 'No items selected'}), 400
    
    count = 0
    
    try:
        if item_type == 'recipe':
            recipes = Recipe.query.filter(Recipe.id.in_(item_ids)).all()
            for recipe in recipes:
                if action == 'approve':
                    recipe.is_approved = True
                elif action == 'feature':
                    recipe.is_featured = True
                    recipe.featured_at = datetime.utcnow()
                elif action == 'delete':
                    db.session.delete(recipe)
                count += 1
                
        elif item_type == 'review':
            reviews = RecipeReview.query.filter(RecipeReview.id.in_(item_ids)).all()
            for review in reviews:
                if action == 'approve':
                    review.is_approved = True
                elif action == 'delete':
                    db.session.delete(review)
                count += 1
        
        db.session.commit()
        
        # Log bulk action
        event = UserEvent(
            user_id=current_user.id,
            event_type='bulk_moderation',
            event_data=f'Action: {action}, Type: {item_type}, Count: {count}'
        )
        db.session.add(event)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'{action.title()} applied to {count} items'})
        
    except Exception as e:
        db.session.rollback()
        log_fault('bulk_moderation_error', str(e), current_user)
        return jsonify({'success': False, 'error': 'Bulk action failed'}), 500

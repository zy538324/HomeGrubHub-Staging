from flask import Blueprint, render_template, flash, redirect, url_for, request, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from recipe_app.db import db
from recipe_app.models.models import User, Recipe, Tag, RecipeRating
from recipe_app.forms.admin_forms import CreateUserForm, EditUserForm, ResetPasswordForm, AdminSettingsForm, DeleteConfirmForm
from functools import wraps
from datetime import datetime

def admin_redirect():
    """Redirect admin functions to user interface with informative message"""
    flash('Admin functionality has been moved to a separate system. Please use the main user interface for now.', 'info')
    return redirect(url_for('routes.dashboard'))

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with site statistics"""
    # Get statistics
    total_users = User.query.count()
    total_recipes = Recipe.query.count()
    total_tags = Tag.query.count()
    admin_users = User.query.filter_by(is_admin=True).count()
    
    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_recipes = Recipe.query.order_by(Recipe.created_at.desc()).limit(5).all()
    
    # Most popular recipes (simplified approach to avoid join issues)
    try:
        popular_recipes = Recipe.query.join(Recipe.favorited_by).group_by(Recipe.id).order_by(func.count().desc()).limit(5).all()
    except Exception:
        # Fallback to recent recipes if the join query fails
        popular_recipes = Recipe.query.order_by(Recipe.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         title='Admin Dashboard',
                         total_users=total_users,
                         total_recipes=total_recipes,
                         total_tags=total_tags,
                         admin_users=admin_users,
                         recent_users=recent_users,
                         recent_recipes=recent_recipes,
                         popular_recipes=popular_recipes)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users"""
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/users.html', title='Manage Users', users=users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create a new user"""
    form = CreateUserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            is_admin=form.is_admin.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'User {user.username} created successfully!', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/create_user.html', title='Create User', form=form)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit a user"""
    user = User.query.get_or_404(user_id)
    form = EditUserForm()
    
    if form.validate_on_submit():
        # Check if username/email changed and if they're unique
        if form.username.data != user.username:
            existing_user = User.query.filter_by(username=form.username.data).first()
            if existing_user:
                flash('Username already exists.', 'error')
                return render_template('admin/edit_user.html', title='Edit User', form=form, user=user)
        
        if form.email.data != user.email:
            existing_user = User.query.filter_by(email=form.email.data).first()
            if existing_user:
                flash('Email already registered.', 'error')
                return render_template('admin/edit_user.html', title='Edit User', form=form, user=user)
        
        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        db.session.commit()
        flash(f'User {user.username} updated successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    elif request.method == 'GET':
        form.username.data = user.username
        form.email.data = user.email
        form.is_admin.data = user.is_admin
    
    return render_template('admin/edit_user.html', title='Edit User', form=form, user=user)

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['GET', 'POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    """Reset a user's password"""
    user = User.query.get_or_404(user_id)
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        user.set_password(form.new_password.data)
        db.session.commit()
        flash(f'Password reset for user {user.username}!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/reset_password.html', title='Reset Password', form=form, user=user)

@admin_bp.route('/users/<int:user_id>/delete', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'error')
        return redirect(url_for('admin.users'))
    
    form = DeleteConfirmForm()
    if form.validate_on_submit():
        # Delete user's recipes
        Recipe.query.filter_by(user_id=user.id).delete()
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} and all their recipes have been deleted.', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/delete_user.html', title='Delete User', form=form, user=user)

@admin_bp.route('/recipes')
@login_required
@admin_required
def recipes():
    """List all recipes"""
    page = request.args.get('page', 1, type=int)
    recipes = Recipe.query.order_by(Recipe.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/recipes.html', title='Manage Recipes', recipes=recipes)

@admin_bp.route('/recipes/<int:recipe_id>/delete', methods=['GET', 'POST'])
@login_required
@admin_required
def delete_recipe(recipe_id):
    """Delete a recipe"""
    recipe = Recipe.query.get_or_404(recipe_id)
    form = DeleteConfirmForm()
    
    if form.validate_on_submit():
        # Delete associated ratings
        RecipeRating.query.filter_by(recipe_id=recipe.id).delete()
        # Delete the recipe
        db.session.delete(recipe)
        db.session.commit()
        flash(f'Recipe "{recipe.title}" has been deleted.', 'success')
        return redirect(url_for('admin.recipes'))
    
    return render_template('admin/delete_recipe.html', title='Delete Recipe', form=form, recipe=recipe)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Admin settings - redirected to main interface"""
    return admin_redirect()

@admin_bp.route('/system-info')
@login_required
def system_info():
    """System information - redirected to main interface"""
    return admin_redirect()

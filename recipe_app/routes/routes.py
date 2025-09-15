import os
import uuid
import requests
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from flask import (
    render_template, flash, redirect, url_for, request, Blueprint, jsonify, session, current_app, abort
)
from flask_login import (
    login_user, logout_user, current_user, login_required
)


from recipe_app.forms.forms import (
    LoginForm, RegistrationForm, RecipeForm, SearchForm, ImportRecipeForm,
    EditImportedRecipeForm, UserProfileForm
)
from recipe_app.models.models import User, Recipe, Tag, RecipeRating, RecipeConversion
from recipe_app.models import NutritionProfile
from recipe_app.main.analytics import UserEvent, FaultLog
from recipe_app.utils.recipe_importer import RecipeImporter
from recipe_app.db import db

# Advanced features
from recipe_app.forms.advanced_forms import (
    AdvancedFilterForm, NutritionAnalysisForm, MealPlannerForm, QuickRecipeSuggestionsForm
)
from ..advanced_filtering import AdvancedRecipeFilter, PantryBasedSuggestions
from recipe_app.utils.nutrition_service import NutritionAnalysisService, IngredientSubstitutionService

main_bp = Blueprint('main', __name__)

# Set up logging for request monitoring
logging.basicConfig(filename='access_monitor.log', level=logging.INFO, 
                   format='%(asctime)s - %(message)s')
access_logger = logging.getLogger('access_monitor')

def log_suspicious_request():
    """Log potentially suspicious requests with detailed information"""
    user_agent = request.headers.get('User-Agent', 'Unknown')
    ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
    referer = request.headers.get('Referer', 'None')
    
    # Log the request details
    access_logger.info(f"Request: {request.method} {request.url} | IP: {ip_address} | User-Agent: {user_agent} | Referer: {referer}")
    
    # Check for bot patterns
    bot_indicators = ['bot', 'crawler', 'spider', 'scraper', 'wget', 'curl']
    if any(indicator in user_agent.lower() for indicator in bot_indicators):
        access_logger.warning(f"BOT DETECTED: {user_agent} from {ip_address} accessing {request.url}")

@main_bp.before_request
def monitor_requests():
    """Monitor all requests for suspicious activity"""
    log_suspicious_request()

def _download_recipe_image(image_url: str, recipe_title: str) -> str:
    """Download recipe image and save it locally"""
    try:
        if not image_url:
            return None
        
        # Make the request with headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(image_url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        
        # Check if the content is actually an image
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            print(f"Not an image: {content_type}")
            return None
        
        # Get file extension from content type or URL
        if 'jpeg' in content_type or 'jpg' in content_type:
            ext = 'jpg'
        elif 'png' in content_type:
            ext = 'png'
        elif 'gif' in content_type:
            ext = 'gif'
        elif 'webp' in content_type:
            ext = 'webp'
        else:
            # Try to get extension from URL
            parsed_url = urlparse(image_url)
            path_ext = os.path.splitext(parsed_url.path)[1].lower()
            if path_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                ext = path_ext[1:]
            else:
                ext = 'jpg'  # Default
        
        # Create filename using recipe title and unique ID
        safe_title = secure_filename(recipe_title[:30])  # Limit length
        unique_id = str(uuid.uuid4())[:8]
        filename = f"imported_{safe_title}_{unique_id}.{ext}"
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join('recipe_app', 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the image
        filepath = os.path.join(upload_dir, filename)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Successfully downloaded image: {filename}")
        return filename
        
    except Exception as e:
        print(f"Failed to download image {image_url}: {e}")
        return None

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            from recipe_app.utils.utils import retry_db_operation
            
            @retry_db_operation(max_retries=3, delay=1)
            def get_user():
                return User.query.filter_by(username=form.username.data).first()
            
            user = get_user()
            
            if user is None or not user.check_password(form.password.data):
                flash('Invalid username or password', 'error')
                return redirect(url_for('main.login'))
            
            login_user(user, remember=form.remember_me.data)
            
            # Log login event with retry
            @retry_db_operation(max_retries=3, delay=1)
            def log_event():
                event = UserEvent(user_id=user.id, event_type='login')
                from recipe_app.db import db
                db.session.add(event)
                db.session.commit()
            
            try:
                log_event()
            except Exception as e:
                # Log the error but don't fail the login
                current_app.logger.error(f"Failed to log login event: {e}")
            
            flash(f'Welcome back, {user.username}!', 'success')
            
        except Exception as e:
            current_app.logger.error(f"Login failed due to database error: {e}")
            flash('Database connection error. Please try again.', 'error')
            return redirect(url_for('main.login'))
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
    return render_template('login.html', title='Sign In', form=form)

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        user.current_plan = 'Free'
        user.is_active = True
        from recipe_app.db import db
        db.session.add(user)
        db.session.commit()
        # Log registration event
        event = UserEvent(user_id=user.id, event_type='register')
        db.session.add(event)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@main_bp.route('/')
def index():
    """Public landing page - shows app overview without requiring login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('public_home.html')

@main_bp.route('/c/pay/<session_id>')
def handle_stripe_redirect(session_id):
    """Handle Stripe checkout completion redirect at root level"""
    if session_id.startswith('cs_'):
        # This is a checkout session ID, redirect to billing success page
        return redirect(url_for('billing.success', session_id=session_id))
    else:
        # Unknown session type, redirect to pricing
        return redirect(url_for('billing.pricing'))

@main_bp.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    """Main dashboard for logged-in users"""
    form = SearchForm()
    from recipe_app.db import db
    if form.validate_on_submit():
        query = form.q.data
        # Apply privacy filtering to search results
        if current_user.can_view_private_recipes():
            recipes = Recipe.query.filter(Recipe.title.contains(query)).all()
        else:
            recipes = Recipe.query.filter(
                Recipe.title.contains(query),
                db.or_(
                    Recipe.is_private == False,
                    Recipe.user_id == current_user.id
                )
            ).all()
        return render_template('search.html', recipes=recipes, query=query)
    
    # Get recent recipes for dashboard with privacy filtering
    if current_user.can_view_private_recipes():
        recent_recipes_query = Recipe.query
    else:
        recent_recipes_query = Recipe.query.filter(
            db.or_(
                Recipe.is_private == False,
                Recipe.user_id == current_user.id
            )
        )
    
    recent_recipes = recent_recipes_query.order_by(Recipe.created_at.desc()).limit(6).all()
    return render_template('index.html', form=form, recent_recipes=recent_recipes)

@main_bp.route('/recipes')
@login_required
def all_recipes():
    from recipe_app.db import db
    """Display all recipes in a card tile format"""
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Number of recipes per page
    
    # Only show public recipes or those owned by the current user
    recipes_query = Recipe.query.filter(
        db.or_(
            Recipe.is_private == False,  # Public recipes
            Recipe.user_id == current_user.id  # Their own recipes
        )
    )

    recipes = recipes_query.order_by(Recipe.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template('all_recipes.html', recipes=recipes)

@main_bp.route('/recipe_categories')
def recipe_categories():
    """Display recipe categories page - accessible to all users"""
    return render_template('recipe_categories.html')

@main_bp.route('/ingredient_search')
@login_required
def ingredient_search():
    """Search recipes by ingredients"""
    return render_template('ingredient_search.html')

@main_bp.route('/search_by_ingredients', methods=['POST'])
@login_required
def search_by_ingredients():
    """Find recipes that contain specified ingredients"""
    ingredients_input = request.form.get('ingredients', '').strip()
    
    if not ingredients_input:
        flash('Please enter at least one ingredient.', 'warning')
        return redirect(url_for('main.ingredient_search'))
    
    # Split ingredients by comma and clean them
    ingredient_list = [ing.strip().lower() for ing in ingredients_input.split(',') if ing.strip()]
    
    if not ingredient_list:
        flash('Please enter valid ingredients.', 'warning')
        return redirect(url_for('main.ingredient_search'))
    
    # Search for recipes containing these ingredients
    matching_recipes = []
    all_recipes = Recipe.query.all()
    
    for recipe in all_recipes:
        recipe_ingredients = recipe.ingredients.lower()
        matches = 0
        matched_ingredients = []
        
        for ingredient in ingredient_list:
            if ingredient in recipe_ingredients:
                matches += 1
                matched_ingredients.append(ingredient)
        
        if matches > 0:
            match_percentage = (matches / len(ingredient_list)) * 100
            matching_recipes.append({
                'recipe': recipe,
                'matches': matches,
                'total_ingredients': len(ingredient_list),
                'match_percentage': match_percentage,
                'matched_ingredients': matched_ingredients
            })
    
    # Sort by match percentage (best matches first)
    matching_recipes.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    return render_template('ingredient_search_results.html', 
                         results=matching_recipes, 
                         search_ingredients=ingredient_list)

@main_bp.route('/search')
@login_required
def search():
    q = request.args.get('q')
    if not q:
        return redirect(url_for('main.index'))
    
    # Enhanced search functionality
    recipes = Recipe.query.filter(
        Recipe.title.contains(q) | 
        Recipe.ingredients.contains(q) | 
        Recipe.description.contains(q) |
        Recipe.country.contains(q) |
        Recipe.cuisine_type.contains(q)
    ).order_by(Recipe.created_at.desc()).all()
    
    return render_template('search.html', title=f'Search Results for "{q}"', recipes=recipes, query=q)

# =============================================================================
# ADVANCED FILTERING ROUTES
# =============================================================================

@main_bp.route('/advanced_search', methods=['GET', 'POST'])
@login_required
def advanced_search():
    """Advanced recipe search with multiple filters"""
    form = AdvancedFilterForm()
    
    # Check if user can access advanced filtering
    if not current_user.can_access_feature('advanced_filtering'):
        flash('Advanced filtering is available for Home plan and above. Upgrade to unlock powerful search features!', 'info')
        return redirect(url_for('billing.pricing'))
    
    recipes = []
    total_count = 0
    filter_counts = {}
    
    if form.validate_on_submit() or request.method == 'GET':
        # Get filter data from form
        filter_data = {}
        
        if form.search_query.data:
            filter_data['search_query'] = form.search_query.data
        if form.max_prep_time.data:
            filter_data['max_prep_time'] = form.max_prep_time.data
        if form.max_cook_time.data:
            filter_data['max_cook_time'] = form.max_cook_time.data
        if form.max_total_time.data:
            filter_data['max_total_time'] = form.max_total_time.data
        if form.difficulty.data:
            filter_data['difficulty'] = form.difficulty.data
        if form.skill_level.data:
            filter_data['skill_level'] = form.skill_level.data
        if form.min_servings.data:
            filter_data['min_servings'] = form.min_servings.data
        if form.max_servings.data:
            filter_data['max_servings'] = form.max_servings.data
        if form.max_calories.data:
            filter_data['max_calories'] = form.max_calories.data
        if form.min_protein.data:
            filter_data['min_protein'] = form.min_protein.data
        if form.max_carbs.data:
            filter_data['max_carbs'] = form.max_carbs.data
        if form.max_fat.data:
            filter_data['max_fat'] = form.max_fat.data
        if form.min_fiber.data:
            filter_data['min_fiber'] = form.min_fiber.data
        if form.max_sodium.data:
            filter_data['max_sodium'] = form.max_sodium.data
        if form.nutritional_flags.data:
            filter_data['nutritional_flags'] = form.nutritional_flags.data
        if form.dietary_restrictions.data:
            filter_data['dietary_restrictions'] = form.dietary_restrictions.data
        if form.required_equipment.data:
            filter_data['required_equipment'] = form.required_equipment.data
        if form.max_cost_per_serving.data:
            filter_data['max_cost_per_serving'] = form.max_cost_per_serving.data
        if form.cuisine_type.data:
            filter_data['cuisine_type'] = form.cuisine_type.data
        if form.seasonal_preference.data:
            filter_data['seasonal_preference'] = form.seasonal_preference.data
        if form.meal_type.data:
            filter_data['meal_type'] = form.meal_type.data
        if form.has_image.data:
            filter_data['has_image'] = form.has_image.data
        if form.has_nutrition_info.data:
            filter_data['has_nutrition_info'] = form.has_nutrition_info.data
        if form.has_batch_cooking.data:
            filter_data['has_batch_cooking'] = form.has_batch_cooking.data
        if form.freezer_friendly.data:
            filter_data['freezer_friendly'] = form.freezer_friendly.data
        if form.quick_prep.data:
            filter_data['quick_prep'] = form.quick_prep.data
        if form.one_pot.data:
            filter_data['one_pot'] = form.one_pot.data
        if form.sort_by.data:
            filter_data['sort_by'] = form.sort_by.data
        
        # Apply filters using the advanced filter service
        filter_service = AdvancedRecipeFilter(current_user)
        query = filter_service.build_query(filter_data)
        
        # Get pagination settings
        page = request.args.get('page', 1, type=int)
        per_page = int(form.per_page.data) if form.per_page.data else 24
        
        # Execute query with pagination
        recipes_pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        recipes = recipes_pagination.items
        total_count = recipes_pagination.total
        
        # Get filter counts for display
        filter_counts = filter_service.get_filter_counts(filter_data)
    
    return render_template('advanced_search.html', 
                         title='Advanced Recipe Search',
                         form=form, 
                         recipes=recipes,
                         total_count=total_count,
                         filter_counts=filter_counts,
                         pagination=recipes_pagination if 'recipes_pagination' in locals() else None)

@main_bp.route('/quick_suggestions', methods=['GET', 'POST'])
@login_required  
def quick_suggestions():
    """What can I cook with what I have?"""
    form = QuickRecipeSuggestionsForm()
    suggestions = []
    
    if form.validate_on_submit():
        # Parse available ingredients
        ingredients_input = form.available_ingredients.data
        available_ingredients = [ing.strip() for ing in ingredients_input.split(',') if ing.strip()]
        
        if available_ingredients:
            # Additional filters
            filters = {}
            if form.meal_type.data:
                filters['meal_type'] = form.meal_type.data
            if form.max_time.data:
                filters['max_time'] = form.max_time.data
            if form.difficulty.data:
                filters['difficulty'] = form.difficulty.data
            
            # Get suggestions
            suggestion_service = PantryBasedSuggestions(current_user)
            max_missing = int(form.max_missing_ingredients.data)
            suggestions = suggestion_service.get_suggestions(
                available_ingredients, 
                max_missing=max_missing,
                filters=filters
            )
        else:
            flash('Please enter at least one ingredient.', 'warning')
    
    return render_template('quick_suggestions.html',
                         title='Recipe Suggestions',
                         form=form,
                         suggestions=suggestions)

@main_bp.route('/nutrition_analysis/<int:recipe_id>')
@login_required
def nutrition_analysis(recipe_id):
    """View detailed nutrition analysis for a recipe"""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Check if user can view this recipe
    if not recipe.can_be_viewed_by(current_user):
        flash('This recipe is not available.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if user can access nutrition analysis
    if not current_user.can_access_feature('nutrition_analysis'):
        flash('Detailed nutrition analysis is available for Home plan and above.', 'info')
        return redirect(url_for('billing.pricing'))
    
    return render_template('nutrition_analysis.html',
                         title=f'Nutrition Analysis - {recipe.title}',
                         recipe=recipe)

@main_bp.route('/analyze_nutrition/<int:recipe_id>', methods=['POST'])
@login_required
def analyze_nutrition(recipe_id):
    """Trigger nutrition analysis for a recipe"""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Check permissions
    if recipe.user_id != current_user.id and not current_user.is_admin:
        flash('You can only analyze nutrition for your own recipes.', 'error')
        return redirect(url_for('main.recipe', recipe_id=recipe_id))
    
    if not current_user.can_access_feature('nutrition_analysis'):
        flash('Nutrition analysis is available for Home plan and above.', 'info')
        return redirect(url_for('billing.pricing'))
    
    # Get API source preference
    api_source = request.form.get('api_source', 'edamam')
    
    # Analyze nutrition
    nutrition_service = NutritionAnalysisService()
    nutrition_data = nutrition_service.analyze_recipe_nutrition(recipe, api_source)
    
    if nutrition_data:
        success = nutrition_service.update_recipe_nutrition(recipe, nutrition_data)
        if success:
            flash(f'Nutrition analysis completed using {nutrition_data.data_source}.', 'success')
        else:
            flash('Failed to save nutrition data.', 'error')
    else:
        flash('Could not analyze nutrition for this recipe. Please try again later.', 'error')
    
    return redirect(url_for('main.nutrition_analysis', recipe_id=recipe_id))

@main_bp.route('/ingredient_substitutions')
@login_required
def ingredient_substitutions():
    """View ingredient substitution suggestions"""
    ingredient = request.args.get('ingredient')
    dietary_restrictions = request.args.getlist('dietary')
    cooking_method = request.args.get('method')
    
    substitutions = []
    
    if ingredient:
        substitution_service = IngredientSubstitutionService()
        substitutions = substitution_service.get_substitutions(
            ingredient, 
            dietary_restrictions=dietary_restrictions,
            cooking_method=cooking_method
        )
    
    return render_template('ingredient_substitutions.html',
                         title='Ingredient Substitutions',
                         ingredient=ingredient,
                         substitutions=substitutions,
                         dietary_restrictions=dietary_restrictions)

# =============================================================================
# END ADVANCED FILTERING ROUTES  
# =============================================================================

# =============================================================================
# MISSING ROUTES IMPLEMENTATION
# =============================================================================

@main_bp.route('/tags')
@login_required 
def tags():
    """Show all available tags and categories"""
    # Get statistics for the dashboard
    total_recipes = Recipe.query.count()
    total_users = User.query.count()
    
    # Get unique cuisines and countries from recipes
    unique_cuisines = db.session.query(Recipe.cuisine_type).distinct().filter(Recipe.cuisine_type.isnot(None)).count()
    unique_countries = db.session.query(Recipe.country).distinct().filter(Recipe.country.isnot(None)).count()
    
    # For now, use existing Tag system until RecipeCategory is implemented
    all_tags = Tag.query.all()
    
    # Create stats object similar to dashboard
    stats = {
        'total_recipes': total_recipes,
        'total_categories': len(all_tags),  # Using tags as categories for now
        'total_countries': unique_countries,
        'total_cuisines': unique_cuisines
    }
    
    # Group tags by type (mock categories structure)
    # Until we implement RecipeCategory, we'll organize existing tags
    categories_by_type = {
        'meal_type': [],
        'dietary': [],
        'allergen': [],
        'cuisine': [],
        'cooking_method': [],
        'health_goal': []
    }
    
    # Organize existing tags into mock categories
    for tag in all_tags:
        tag_name_lower = tag.name.lower()
        # Mock category assignment based on tag names
        if any(meal in tag_name_lower for meal in ['breakfast', 'lunch', 'dinner', 'snack', 'dessert', 'appetizer']):
            category_obj = type('Category', (), {
                'id': tag.id,
                'name': tag.name,
                'description': f'Recipes tagged with {tag.name}',
                'color_code': '#007bff',
                'icon': 'fas fa-utensils',
                'recipe_count': len(tag.recipes)
            })()
            categories_by_type['meal_type'].append(category_obj)
        elif any(diet in tag_name_lower for diet in ['vegan', 'vegetarian', 'gluten-free', 'keto', 'paleo', 'low-carb']):
            category_obj = type('Category', (), {
                'id': tag.id,
                'name': tag.name,
                'description': f'Recipes tagged with {tag.name}',
                'color_code': '#28a745',
                'icon': 'fas fa-leaf',
                'recipe_count': len(tag.recipes)
            })()
            categories_by_type['dietary'].append(category_obj)
        else:
            # Default to general category
            category_obj = type('Category', (), {
                'id': tag.id,
                'name': tag.name,
                'description': f'Recipes tagged with {tag.name}',
                'color_code': '#6c757d',
                'icon': 'fas fa-tag',
                'recipe_count': len(tag.recipes)
            })()
            categories_by_type['cooking_method'].append(category_obj)
    
    return render_template('tags.html',
                         title='Recipe Categories',
                         stats=stats,
                         categories_by_type=categories_by_type)

@main_bp.route('/category/<int:category_id>')
@login_required
def category_recipes(category_id):
    """Show recipes for a specific category (using tag system for now)"""
    # For now, use the tag system since RecipeCategory isn't implemented yet
    tag = Tag.query.get_or_404(category_id)
    
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    recipes = Recipe.query.filter(Recipe.tags.contains(tag)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Create a mock category object
    category = type('Category', (), {
        'id': tag.id,
        'name': tag.name,
        'description': f'Recipes tagged with {tag.name}',
        'color_code': '#007bff',
        'icon': 'fas fa-tag'
    })()
    
    return render_template('category_recipes.html',
                         title=f'{tag.name} Recipes',
                         category=category,
                         recipes=recipes)

@main_bp.route('/tag/<tag_name>')
@login_required
def tag(tag_name):
    """Show recipes for a specific tag"""
    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
    recipes = Recipe.query.filter(Recipe.tags.contains(tag)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('tag.html',
                         title=f'Recipes tagged with "{tag_name}"',
                         tag=tag,
                         recipes=recipes)

@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    user_recipes = Recipe.query.filter_by(user_id=current_user.id).order_by(Recipe.created_at.desc()).all()
    favorite_recipes = current_user.favorites
    
    stats = {
        'total_recipes': len(user_recipes),
        'favorite_count': len(favorite_recipes),
        'member_since': current_user.created_at.strftime('%B %Y') if current_user.created_at else 'Unknown',
        'current_plan': current_user.current_plan
    }
    
    return render_template('profile.html', 
                         user=current_user, 
                         user_recipes=user_recipes, 
                         favorite_recipes=favorite_recipes,
                         stats=stats)


@main_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile including postcode for location-specific pricing"""
    from recipe_app.utils.image_storage import ImageStorageManager
    form = UserProfileForm(current_user.email)
    
    if form.validate_on_submit():
        try:
            # Handle profile image upload using new storage system
            if form.profile_image.data:
                # Delete old profile image if exists
                if current_user.profile_image:
                    ImageStorageManager.delete_image(current_user.profile_image, 'profiles')
                
                # Save new image using the storage manager
                filename, message = ImageStorageManager.save_image(form.profile_image.data, 'profiles')
                if filename:
                    current_user.profile_image = filename
                else:
                    flash(f'Error uploading image: {message}', 'error')
                    return render_template('auth/edit_profile.html', title='Edit Profile', form=form)
            
            # Update user profile fields
            current_user.email = form.email.data
            current_user.display_name = form.display_name.data.strip() if form.display_name.data else None
            current_user.profile_bio = form.profile_bio.data.strip() if form.profile_bio.data else None
            
            # Handle social links as JSON
            social_links = {}
            if form.instagram_url.data:
                social_links['instagram'] = form.instagram_url.data.strip()
            if form.youtube_url.data:
                social_links['youtube'] = form.youtube_url.data.strip()
            if form.website_url.data:
                social_links['website'] = form.website_url.data.strip()
            
            current_user.social_links = social_links if social_links else None
            
            # Handle postcode
            if form.postcode.data:
                # Convert postcode to uppercase and ensure proper format
                postcode = form.postcode.data.upper().strip()
                # Add space if missing (e.g., "SW1A1AA" -> "SW1A 1AA")
                if len(postcode) > 3 and postcode[-4] != ' ':
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                current_user.postcode = postcode
            else:
                current_user.postcode = None
            
            db.session.commit()
            flash('Your profile has been updated!', 'success')
            if current_user.postcode:
                flash('Location-specific pricing is now enabled for your shopping lists!', 'info')
            return redirect(url_for('main.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile. Please try again.', 'error')
            print(f"Error updating profile: {e}")
    
    elif request.method == 'GET':
        # Populate form with current user data
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.display_name.data = current_user.display_name
        form.profile_bio.data = current_user.profile_bio
        form.postcode.data = current_user.postcode
        
        # Populate social links
        if current_user.social_links:
            form.instagram_url.data = current_user.social_links.get('instagram', '')
            form.youtube_url.data = current_user.social_links.get('youtube', '')
            form.website_url.data = current_user.social_links.get('website', '')
    
    return render_template('edit_profile.html', form=form)

@main_bp.route('/favourites')
@login_required
def favourites():
    """Show user's favourite recipes"""
    favourite_recipes = current_user.favorites
    return render_template('favourites.html', 
                         recipes=favourite_recipes,
                         title='My Favourite Recipes')

@main_bp.route('/chat')
@login_required
def chat():
    """Live chat support page"""
    return render_template('support/live_chat.html')

@main_bp.route('/create_meal_plan', methods=['POST'])
@login_required
def create_meal_plan():
    from recipe_app.db import db
    """Create a new meal plan"""
    if not current_user.can_access_feature('meal_planning'):
        flash('Meal planning requires Home plan', 'warning')
        return redirect(url_for('billing.pricing'))
    
    # Get form data
    name = request.form.get('name')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    target_calories = request.form.get('target_daily_calories')
    dietary_preferences = request.form.getlist('dietary_preferences')
    
    if not name or not start_date or not end_date:
        flash('Please fill in all required fields.', 'error')
        return redirect(url_for('meal_planning.meal_planner'))
    
    try:
        from datetime import datetime
        from recipe_app.models.advanced_models import MealPlan
        
        # Parse dates
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Create meal plan
        meal_plan = MealPlan(
            user_id=current_user.id,
            name=name,
            description=f"Meal plan from {start_date_obj} to {end_date_obj}",
            start_date=start_date_obj,
            end_date=end_date_obj,
            is_active=True,
            is_template=False
        )
        
        db.session.add(meal_plan)
        db.session.commit()
        
        flash(f'Meal plan "{name}" created successfully!', 'success')
        return redirect(url_for('meal_planning.meal_planner'))
        
    except ImportError:
        flash('Meal planning models are not available. Please contact support.', 'error')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        flash(f'Error creating meal plan: {str(e)}', 'error')
        return redirect(url_for('meal_planning.meal_planner'))

@main_bp.route('/add_recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    from recipe_app.db import db
    if not current_user.can_access_feature('upload_recipes'):
        flash('Uploading custom recipes is available for paid plans. Upgrade to unlock this feature!', 'info')
        return redirect(url_for('billing.pricing'))
    form = RecipeForm()
    if form.validate_on_submit():
        try:
            # Create new recipe
            recipe = Recipe(
                title=form.title.data,
                description=form.description.data,
                ingredients=form.ingredients.data,
                method=form.method.data,
                prep_time=form.prep_time.data,
                cook_time=form.cook_time.data,
                servings=form.servings.data,
                difficulty=form.difficulty.data,
                country=form.country.data,
                cuisine_type=form.cuisine_type.data,
                is_private=not form.is_public.data,  # Convert is_public to is_private
                user_id=current_user.id
                # created_at will be set automatically by the model default
            )
            db.session.add(recipe)
            db.session.flush()  # Get the recipe ID
            
            # Create nutrition profile if nutrition data provided
            if any([form.calories.data, form.protein_g.data, form.carbs_g.data, 
                   form.fat_g.data, form.fiber_g.data, form.sugar_g.data, form.sodium_mg.data]):
                nutrition_profile = NutritionProfile(
                    recipe_id=recipe.id,
                    calories=form.calories.data,
                    protein_g=form.protein_g.data,
                    carbs_g=form.carbs_g.data,
                    fat_g=form.fat_g.data,
                    fiber_g=form.fiber_g.data,
                    sugar_g=form.sugar_g.data,
                    sodium_mg=form.sodium_mg.data
                )
                db.session.add(nutrition_profile)
            
            # Process tags
            if form.tags.data:
                tags = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
                for tag_name in tags:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                        db.session.flush()
                    recipe.tags.append(tag)
            db.session.commit()
            # Log recipe add event
            event = UserEvent(user_id=current_user.id, event_type='add_recipe', event_data=str(recipe.id))
            db.session.add(event)
            db.session.commit()
            flash('Recipe added successfully!', 'success')
            return redirect(url_for('main.recipe', recipe_id=recipe.id))
        except Exception as e:
            db.session.rollback()
            flash('Error adding recipe. Please try again.', 'error')
            print(f"Error adding recipe: {e}")
    
    return render_template('add_recipe.html', form=form)

@main_bp.route('/recipe/<int:recipe_id>')
def recipe(recipe_id):
    """View a single recipe"""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Check if recipe is public or user owns it
    if recipe.is_private and (not current_user.is_authenticated or recipe.user_id != current_user.id):
        flash('This recipe is private', 'error')
        return redirect(url_for('main.index'))
    
    # Get recipe tags
    recipe_tags = recipe.tags
    
    # Get recipe ratings
    ratings = RecipeRating.query.filter_by(recipe_id=recipe_id).all()
    average_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
    rating_count = len(ratings)
    
    # Check if user has favorited this recipe
    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = recipe in current_user.favorites
    
    return render_template('recipe.html', 
                         recipe=recipe, 
                         tags=recipe_tags,
                         ratings=ratings,
                         average_rating=average_rating,
                         avg_rating=average_rating,
                         rating_count=rating_count,
                         is_favorite=is_favorite)

@main_bp.route('/recipe/<int:recipe_id>/rate', methods=['POST'])
@login_required
def rate_recipe(recipe_id):
    """Submit a rating for a recipe"""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Get data from request
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    rating_value = data.get('rating')
    comment = data.get('comment', '').strip()
    
    # Validate rating
    if not rating_value or not isinstance(rating_value, int) or rating_value < 1 or rating_value > 5:
        return jsonify({'success': False, 'error': 'Rating must be between 1 and 5'}), 400
    
    try:
        # Check if user already rated this recipe
        existing_rating = RecipeRating.query.filter_by(
            user_id=current_user.id,
            recipe_id=recipe_id
        ).first()
        
        if existing_rating:
            # Update existing rating
            existing_rating.rating = rating_value
            existing_rating.comment = comment
            existing_rating.created_at = datetime.utcnow()
            message = 'Rating updated successfully!'
        else:
            # Create new rating
            new_rating = RecipeRating(
                user_id=current_user.id,
                recipe_id=recipe_id,
                rating=rating_value,
                comment=comment
            )
            db.session.add(new_rating)
            message = 'Rating submitted successfully!'
        
        db.session.commit()
        
        # Calculate new average rating
        ratings = RecipeRating.query.filter_by(recipe_id=recipe_id).all()
        average_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
        rating_count = len(ratings)
        
        return jsonify({
            'success': True,
            'message': message,
            'average_rating': round(average_rating, 1),
            'rating_count': rating_count,
            'user_rating': rating_value
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to submit rating'}), 500

@main_bp.route('/recipe/<int:recipe_id>/user-rating')
@login_required
def get_user_rating(recipe_id):
    """Get current user's rating for a recipe"""
    user_rating = RecipeRating.query.filter_by(
        user_id=current_user.id,
        recipe_id=recipe_id
    ).first()
    
    if user_rating:
        return jsonify({
            'user_rating': {
                'rating': user_rating.rating,
                'comment': user_rating.comment
            }
        })
    else:
        return jsonify({'user_rating': None})

# Keep old route for backward compatibility
@main_bp.route('/toggle_favorite/<int:recipe_id>', methods=['POST'])
@login_required
def toggle_favorite(recipe_id):
    """Legacy route - redirect to new British spelling route"""
    return toggle_favourite(recipe_id)

@main_bp.route('/toggle_favourite/<int:recipe_id>', methods=['POST'])
@login_required
def toggle_favourite(recipe_id):
    """Toggle favourite status for a recipe"""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    if current_user.is_favorite(recipe):
        current_user.remove_favorite(recipe)
        is_favourite = False
        message = 'Recipe removed from favourites'
    else:
        current_user.add_favorite(recipe)
        is_favourite = True
        message = 'Recipe added to favourites'
    
    try:
        db.session.commit()
        
        # Get total favourite count for this recipe
        total_favourites = len(recipe.favorited_by)
        
        if request.headers.get('Content-Type') == 'application/json' or request.is_json:
            return jsonify({
                'success': True,
                'is_favourite': is_favourite, 
                'message': message,
                'total_favourites': total_favourites
            })
        else:
            flash(message, 'success')
            return redirect(url_for('main.recipe', recipe_id=recipe_id))
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to update favourite status'}), 500

@main_bp.route('/import_recipe', methods=['GET', 'POST'])
@login_required
def import_recipe():
    if not current_user.can_access_feature('url_import'):
        flash('Recipe import from URL is available for Home plan. Upgrade to unlock this feature!', 'info')
        return redirect(url_for('billing.pricing'))
    form = ImportRecipeForm()
    if form.validate_on_submit():
        try:
            importer = RecipeImporter()
            
            if form.import_type.data == 'url':
                # Import single recipe
                result = importer.import_from_url(form.url.data)
                if result and result.get('success'):
                    # Store in session for review
                    session['imported_recipe'] = result.get('recipe', {})
                    print(f"DEBUG: Stored recipe in session: {session['imported_recipe']}")
                    flash('Recipe imported successfully! Please review and save.', 'success')
                    return redirect(url_for('main.review_imported_recipe'))
                else:
                    error_msg = result.get('error', 'Could not import recipe from URL. Please check the URL and try again.')
                    flash(error_msg, 'error')
            
            elif form.import_type.data == 'rss':
                # RSS import feature - coming soon
                flash('RSS feed import is coming soon! For now, please use individual recipe URLs.', 'info')
                return render_template('import_recipe.html', form=form)
                    
        except Exception as e:
            flash('Error importing recipe. Please try again.', 'error')
            print(f"Import error: {e}")
    
    return render_template('import_recipe.html', form=form)

@main_bp.route('/bulk_import_dataset', methods=['GET', 'POST'])
@login_required
def bulk_import_dataset():
    """Bulk import recipes from datasets (Kaggle, CSV files, etc.)"""
    if not current_user.can_access_feature('url_import'):
        flash('Bulk dataset import is available for Home plan. Upgrade to unlock this feature!', 'info')
        return redirect(url_for('billing.pricing'))
    
    if request.method == 'POST':
        try:
            import_type = request.form.get('import_type')
            
            if import_type == 'kaggle':
                # Kaggle dataset import
                dataset_path = request.form.get('dataset_path')
                file_path = request.form.get('file_path', '')
                max_recipes = int(request.form.get('max_recipes', 100))
                
                if not dataset_path:
                    flash('Please provide a Kaggle dataset path', 'error')
                    return render_template('bulk_import_dataset.html')
                
                # Import from Kaggle dataset
                importer = RecipeImporter()
                result = importer.import_from_kaggle_dataset(dataset_path, file_path, max_recipes)
                
                if result and result.get('success'):
                    recipes = result.get('recipes', [])
                    session['bulk_imports'] = recipes
                    flash(f'Successfully loaded {len(recipes)} recipes from Kaggle dataset!', 'success')
                    return redirect(url_for('main.review_bulk_imports'))
                else:
                    error_msg = result.get('error', 'Could not import from Kaggle dataset.')
                    flash(error_msg, 'error')
            
            elif import_type == 'csv_upload':
                # CSV file upload
                if 'csv_file' not in request.files:
                    flash('Please select a CSV file', 'error')
                    return render_template('bulk_import_dataset.html')
                
                file = request.files['csv_file']
                if file.filename == '':
                    flash('Please select a CSV file', 'error')
                    return render_template('bulk_import_dataset.html')
                
                if file and file.filename.endswith('.csv'):
                    max_recipes = int(request.form.get('max_recipes', 100))
                    
                    # For very large files, limit to reasonable batch sizes
                    if max_recipes > 1000:
                        max_recipes = 1000
                        flash(f'Large file detected. Limited to {max_recipes} recipes for performance. You can import multiple batches.', 'info')
                    
                    # Import from uploaded CSV
                    importer = RecipeImporter()
                    result = importer.import_from_csv_file(file, max_recipes)
                    
                    if result and result.get('success'):
                        recipes = result.get('recipes', [])
                        total_available = result.get('total_rows', len(recipes))
                        session['bulk_imports'] = recipes
                        
                        if total_available > len(recipes):
                            flash(f'Successfully loaded {len(recipes)} recipes from CSV file! ({total_available} total recipes available in file)', 'success')
                        else:
                            flash(f'Successfully loaded {len(recipes)} recipes from CSV file!', 'success')
                        return redirect(url_for('main.review_bulk_imports'))
                    else:
                        error_msg = result.get('error', 'Could not import from CSV file.')
                        flash(error_msg, 'error')
                else:
                    flash('Please upload a valid CSV file', 'error')
                    
        except Exception as e:
            flash('Error importing dataset. Please try again.', 'error')
            print(f"Bulk import error: {e}")
    
    return render_template('bulk_import_dataset.html')

@main_bp.route('/review_bulk_imports')
@login_required
def review_bulk_imports():
    """Review bulk imported recipes before saving"""
    recipes = session.get('bulk_imports', [])
    if not recipes:
        flash('No bulk imports to review', 'error')
        return redirect(url_for('main.bulk_import_dataset'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Paginate recipes for review
    start = (page - 1) * per_page
    end = start + per_page
    paginated_recipes = recipes[start:end]
    
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': len(recipes),
        'has_prev': page > 1,
        'has_next': end < len(recipes),
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if end < len(recipes) else None
    }
    
    return render_template('review_bulk_imports.html', 
                         recipes=paginated_recipes, 
                         pagination=pagination_info,
                         total_recipes=len(recipes))

@main_bp.route('/save_bulk_imports', methods=['POST'])
@login_required
def save_bulk_imports():
    from recipe_app.db import db
    """Save selected bulk imported recipes"""
    recipes = session.get('bulk_imports', [])
    if not recipes:
        flash('No bulk imports to save', 'error')
        return redirect(url_for('main.bulk_import_dataset'))
    
    selected_indices = request.form.getlist('selected_recipes')
    
    if not selected_indices:
        flash('Please select at least one recipe to save', 'warning')
        return redirect(url_for('main.review_bulk_imports'))
    
    saved_count = 0
    errors = []
    
    try:
        for index_str in selected_indices:
            try:
                index = int(index_str)
                if 0 <= index < len(recipes):
                    recipe_data = recipes[index]
                    
                    # Create new recipe
                    recipe = Recipe(
                        title=recipe_data.get('title', 'Untitled Recipe')[:140],
                        description=recipe_data.get('description', '')[:500],
                        ingredients=recipe_data.get('ingredients', ''),
                        method=recipe_data.get('method', ''),
                        prep_time=recipe_data.get('prep_time'),
                        cook_time=recipe_data.get('cook_time'),
                        servings=recipe_data.get('servings', 4),
                        difficulty=recipe_data.get('difficulty', 'Medium'),
                        country=recipe_data.get('country', ''),
                        cuisine_type=recipe_data.get('cuisine_type', ''),
                        is_private=True,  # Import as private by default
                        user_id=current_user.id
                    )
                    
                    db.session.add(recipe)
                    db.session.flush()
                    
                    # Process tags if available
                    if recipe_data.get('tags'):
                        tags = [tag.strip() for tag in str(recipe_data['tags']).split(',') if tag.strip()]
                        for tag_name in tags[:10]:  # Limit to 10 tags
                            tag = Tag.query.filter_by(name=tag_name).first()
                            if not tag:
                                tag = Tag(name=tag_name)
                                db.session.add(tag)
                                db.session.flush()
                            recipe.tags.append(tag)
                    
                    saved_count += 1
                    
            except Exception as e:
                errors.append(f"Error saving recipe {index + 1}: {str(e)}")
                print(f"Error saving bulk recipe {index}: {e}")
        
        db.session.commit()
        session.pop('bulk_imports', None)
        
        if saved_count > 0:
            flash(f'Successfully saved {saved_count} recipes!', 'success')
            if errors:
                flash(f'Some recipes had errors: {"; ".join(errors[:3])}', 'warning')
        else:
            flash('No recipes were saved. Please check for errors.', 'error')
            
    except Exception as e:
        db.session.rollback()
        flash('Error saving recipes. Please try again.', 'error')
        print(f"Bulk save error: {e}")
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/review_imported_recipe', methods=['GET', 'POST'])
@login_required
def review_imported_recipe():
    from recipe_app.db import db
    if not current_user.can_access_feature('url_import'):
        flash('Recipe import from URL is available for Home plan. Upgrade to unlock this feature!', 'info')
        return redirect(url_for('billing.pricing'))
    """Review and edit imported recipe before saving"""
    recipe_data = session.get('imported_recipe')
    print(f"DEBUG: Recipe data from session: {recipe_data}")
    if not recipe_data:
        flash('No imported recipe to review', 'error')
        return redirect(url_for('main.import_recipe'))
    
    form = EditImportedRecipeForm()
    
    if request.method == 'GET':
        # Populate form with imported data
        form.title.data = recipe_data.get('title', '')
        form.description.data = recipe_data.get('description', '')
        form.ingredients.data = recipe_data.get('ingredients', '')
        form.method.data = recipe_data.get('method', '')
        form.prep_time.data = recipe_data.get('prep_time')
        form.cook_time.data = recipe_data.get('cook_time')
        form.servings.data = recipe_data.get('servings')
        form.difficulty.data = recipe_data.get('difficulty', 'Medium')
        form.country.data = recipe_data.get('country', '')
        form.cuisine_type.data = recipe_data.get('cuisine_type', '')
        form.tags.data = recipe_data.get('tags', '')
        form.source_url.data = recipe_data.get('source_url', '')
        
        # Populate nutrition fields if available
        nutrition_data = recipe_data.get('nutrition', {})
        form.calories.data = nutrition_data.get('calories')
        form.protein_g.data = nutrition_data.get('protein_g')
        form.carbs_g.data = nutrition_data.get('carbs_g')
        form.fat_g.data = nutrition_data.get('fat_g')
        form.fiber_g.data = nutrition_data.get('fiber_g')
        form.sugar_g.data = nutrition_data.get('sugar_g')
        form.sodium_mg.data = nutrition_data.get('sodium_mg')
    
    if form.validate_on_submit():
        if form.save_recipe.data:
            try:
                # Download and save recipe image if available
                image_filename = None
                recipe_data = session.get('imported_recipe', {})
                if recipe_data.get('image_url'):
                    image_filename = _download_recipe_image(recipe_data['image_url'], form.title.data)
                
                # Create new recipe
                recipe = Recipe(
                    title=form.title.data,
                    description=form.description.data,
                    ingredients=form.ingredients.data,
                    method=form.method.data,
                    prep_time=form.prep_time.data,
                    cook_time=form.cook_time.data,
                    servings=form.servings.data,
                    difficulty=form.difficulty.data,
                    country=form.country.data,
                    cuisine_type=form.cuisine_type.data,
                    image_file=image_filename,
                    is_private=not form.is_public.data,  # Note: is_private is opposite of is_public
                    user_id=current_user.id
                )
                
                db.session.add(recipe)
                db.session.flush()
                
                # Create nutrition profile if nutrition data provided
                if any([form.calories.data, form.protein_g.data, form.carbs_g.data, 
                       form.fat_g.data, form.fiber_g.data, form.sugar_g.data, form.sodium_mg.data]):
                    nutrition_profile = NutritionProfile(
                        recipe_id=recipe.id,
                        calories=form.calories.data,
                        protein_g=form.protein_g.data,
                        carbs_g=form.carbs_g.data,
                        fat_g=form.fat_g.data,
                        fiber_g=form.fiber_g.data,
                        sugar_g=form.sugar_g.data,
                        sodium_mg=form.sodium_mg.data
                    )
                    db.session.add(nutrition_profile)
                
                # Process tags
                if form.tags.data:
                    tags = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
                    for tag_name in tags:
                        tag = Tag.query.filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            db.session.add(tag)
                            db.session.flush()
                        
                        recipe.tags.append(tag)
                
                db.session.commit()
                session.pop('imported_recipe', None)
                flash('Recipe saved successfully!', 'success')
                return redirect(url_for('main.recipe', recipe_id=recipe.id))
                
            except Exception as e:
                db.session.rollback()
                flash('Error saving recipe. Please try again.', 'error')
                print(f"Error saving imported recipe: {e}")
        
        elif form.import_another.data:
            session.pop('imported_recipe', None)
            return redirect(url_for('main.import_recipe'))
    
    return render_template('edit_imported_recipe.html', form=form, recipe_data=recipe_data)

@main_bp.route('/recipe_conversions/<int:recipe_id>')
@login_required
def recipe_conversions(recipe_id):
    """Show unit conversions and related info for a recipe."""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Generate metric conversions for ingredients
    metric_ingredients = ""
    if recipe.ingredients:
        from recipe_app.utils.utils import convert_recipe_to_metric
        metric_ingredients = convert_recipe_to_metric(recipe.ingredients)
    
    return render_template('recipe_conversions.html', recipe=recipe, metric_ingredients=metric_ingredients)

@main_bp.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    from recipe_app.db import db
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this recipe.', 'error')
        return redirect(url_for('main.recipe', recipe_id=recipe_id))
    if not current_user.can_access_feature('upload_recipes'):
        flash('Editing recipes is available for paid plans. Upgrade to unlock this feature!', 'info')
        return redirect(url_for('billing.pricing'))
    form = RecipeForm(obj=recipe)
    if form.validate_on_submit():
        recipe.title = form.title.data
        recipe.description = form.description.data
        recipe.ingredients = form.ingredients.data
        recipe.method = form.method.data
        recipe.prep_time = form.prep_time.data
        recipe.cook_time = form.cook_time.data
        recipe.servings = form.servings.data
        recipe.difficulty = form.difficulty.data
        recipe.country = form.country.data
        recipe.cuisine_type = form.cuisine_type.data
        recipe.is_private = not form.is_public.data
        # Update tags
        recipe.tags.clear()
        if form.tags.data:
            tags = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
            for tag_name in tags:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()
                recipe.tags.append(tag)
        db.session.commit()
        flash('Recipe updated successfully!', 'success')
        return redirect(url_for('main.recipe', recipe_id=recipe.id))
    # Pre-populate tags as comma-separated string
    form.tags.data = ', '.join([tag.name for tag in recipe.tags])
    form.is_public.data = not recipe.is_private
    return render_template('add_recipe.html', form=form, edit_mode=True, recipe=recipe)


# =============================================================================
# END MISSING ROUTES
# =============================================================================

@main_bp.route('/privacy')
def privacy_policy():
    return render_template('legal/privacy_policy.html', title='Privacy Policy')

@main_bp.route('/terms')
def terms_of_service():
    return render_template('legal/terms_of_service.html', title='Terms of Service')

@main_bp.route('/cookies')
def cookie_policy():
    return render_template('legal/cookie_policy.html', title='Cookie Policy')

@main_bp.route('/about')
def about():
    return render_template('about.html', title='About HomeGrubHub')

@main_bp.route('/robots.txt')
def robots_txt():
    """Serve robots.txt file"""
    from flask import make_response
    response = make_response(open('recipe_app/static/robots.txt').read())
    response.headers["Content-Type"] = "text/plain"
    return response

@main_bp.route('/blog')
def blog():
    return render_template('blog/index.html', title='Blog & Tips')

@main_bp.route('/blog/<slug>')
def blog_post(slug):
    # Map blog post slugs to templates
    post_templates = {
        'meal-planning-guide': 'blog/meal-planning-guide.html',
        'budget-meal-planning': 'blog/budget-meal-planning.html',
        'healthy-family-meals': 'blog/healthy-family-meals.html'
    }
    
    template = post_templates.get(slug, 'blog/post-not-found.html')
    return render_template(template)

@main_bp.route('/refund-policy')
def refund_policy():
    return render_template('legal/refund-policy.html', title='Refund Policy')

# Admin routes temporarily disabled - moving to separate admin webapp
# @main_bp.route('/admin/analytics')
# @login_required
# def admin_analytics():
#     if not current_user.is_admin:
#         flash('Admin access required.', 'error')
#         return redirect(url_for('main.dashboard'))
#     # Admin functionality moved to separate admin application
#     flash('Admin features have been moved to a separate admin portal.', 'info')
#     return redirect(url_for('main.dashboard'))
    from sqlalchemy import func
    user_count = User.query.count()
    recipe_count = Recipe.query.count()
    login_count = UserEvent.query.filter_by(event_type='login').count()
    register_count = UserEvent.query.filter_by(event_type='register').count()
    add_recipe_count = UserEvent.query.filter_by(event_type='add_recipe').count()
    recent_events = UserEvent.query.order_by(UserEvent.timestamp.desc()).limit(50).all()

    # Fault log filtering
    fault_user = request.args.get('fault_user')
    fault_plan = request.args.get('fault_plan')
    fault_id = request.args.get('fault_id')
    fault_query = FaultLog.query
    if fault_user:
        fault_query = fault_query.join(User).filter(User.username.ilike(f"%{fault_user}%"))
    if fault_plan:
        fault_query = fault_query.filter(FaultLog.plan == fault_plan)
    if fault_id:
        fault_query = fault_query.filter(FaultLog.fault_id.ilike(f"%{fault_id}%"))
    recent_faults = fault_query.order_by(FaultLog.timestamp.desc()).limit(50).all()

    return render_template('admin/analytics.html',
        user_count=user_count,
        recipe_count=recipe_count,
        login_count=login_count,
        register_count=register_count,
        add_recipe_count=add_recipe_count,
        recent_events=recent_events,
        recent_faults=recent_faults,
        fault_user=fault_user or '',
        fault_plan=fault_plan or '',
        fault_id=fault_id or ''
    )

@main_bp.route('/offline')
def offline():
    """PWA Offline fallback page"""
    return render_template('offline.html')

@main_bp.route('/adjust-servings', methods=['POST'])
def adjust_servings():
    """AJAX endpoint for adjusting serving sizes"""
    try:
        # Add debugging
        print(f"DEBUG: Request content type: {request.content_type}")
        print(f"DEBUG: Request data: {request.data}")
        
        data = request.get_json()
        print(f"DEBUG: Parsed JSON data: {data}")
        
        if not data:
            return jsonify({'success': False, 'message': 'No JSON data received'})
        
        ingredients = data.get('ingredients', '').strip()
        original_servings = int(data.get('original_servings', 4))
        target_servings = int(data.get('target_servings', 4))
        recipe_id = data.get('recipe_id')
        
        print(f"DEBUG: Ingredients length: {len(ingredients)}")
        print(f"DEBUG: Original servings: {original_servings}, Target servings: {target_servings}")
        print(f"DEBUG: Recipe ID: {recipe_id}")
        
        if not ingredients:
            return jsonify({'success': False, 'message': 'No ingredients provided'})
            
        if original_servings <= 0 or target_servings <= 0:
            return jsonify({'success': False, 'message': 'Invalid serving sizes'})
        
        # Apply the serving adjustment
        from recipe_app.utils.utils import adjust_recipe_servings
        print("DEBUG: About to call adjust_recipe_servings")
        adjusted_ingredients = adjust_recipe_servings(ingredients, original_servings, target_servings)
        print(f"DEBUG: Adjustment successful, result length: {len(adjusted_ingredients)}")
        
        # Save conversion to database if user is logged in and recipe_id is provided
        conversion_id = None
        if current_user.is_authenticated and recipe_id:
            try:
                recipe = Recipe.query.get(recipe_id)
                if recipe:
                    conversion = RecipeConversion(
                        original_recipe_id=recipe_id,
                        user_id=current_user.id,
                        conversion_type='serving_adjust',
                        original_servings=original_servings,
                        target_servings=target_servings,
                        is_metric_converted=False,
                        converted_ingredients=adjusted_ingredients,
                        converted_title=f"{recipe.title} ({target_servings} servings)",
                        conversion_notes=f"Adjusted from {original_servings} to {target_servings} servings"
                    )
                    db.session.add(conversion)
                    db.session.commit()
                    conversion_id = conversion.id
                    print(f"DEBUG: Saved conversion with ID: {conversion_id}")
            except Exception as e:
                print(f"DEBUG: Error saving conversion: {str(e)}")
                # Don't fail the request if saving fails
                pass
        
        return jsonify({
            'success': True, 
            'adjusted_ingredients': adjusted_ingredients,
            'multiplier': target_servings / original_servings,
            'original_servings': original_servings,
            'target_servings': target_servings,
            'conversion_id': conversion_id
        })
    
    except Exception as e:
        print(f"DEBUG: Error in adjust_servings: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

@main_bp.route('/test-adjust', methods=['POST'])
def test_adjust():
    """Test endpoint for adjustment functionality"""
    try:
        print(f"DEBUG: Test endpoint called")
        print(f"DEBUG: Request content type: {request.content_type}")
        print(f"DEBUG: Request data: {request.data}")
        
        data = request.get_json()
        print(f"DEBUG: Parsed JSON: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Test endpoint working',
            'data': data
        })
    except Exception as e:
        print(f"DEBUG: Error in test_adjust: {str(e)}")
        return jsonify({'success': False, 'message': f'Test error: {str(e)}'})

@main_bp.route('/convert-to-metric', methods=['POST'])
def convert_to_metric_endpoint():
    """AJAX endpoint for converting ingredients to metric"""
    try:
        data = request.get_json()
        ingredients = data.get('ingredients', '').strip()
        recipe_id = data.get('recipe_id')
        
        if not ingredients:
            return jsonify({'success': False, 'message': 'No ingredients provided'})
        
        from recipe_app.utils.utils import convert_recipe_to_metric
        metric_ingredients = convert_recipe_to_metric(ingredients)
        
        # Save conversion to database if user is logged in and recipe_id is provided
        conversion_id = None
        if current_user.is_authenticated and recipe_id:
            try:
                recipe = Recipe.query.get(recipe_id)
                if recipe:
                    conversion = RecipeConversion(
                        original_recipe_id=recipe_id,
                        user_id=current_user.id,
                        conversion_type='metric',
                        original_servings=recipe.servings,
                        target_servings=recipe.servings,
                        is_metric_converted=True,
                        converted_ingredients=metric_ingredients,
                        converted_title=f"{recipe.title} (metric)",
                        conversion_notes="Converted to metric measurements"
                    )
                    db.session.add(conversion)
                    db.session.commit()
                    conversion_id = conversion.id
                    print(f"DEBUG: Saved metric conversion with ID: {conversion_id}")
            except Exception as e:
                print(f"DEBUG: Error saving metric conversion: {str(e)}")
                # Don't fail the request if saving fails
                pass
        
        return jsonify({
            'success': True,
            'metric_ingredients': metric_ingredients,
            'conversion_id': conversion_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

@main_bp.route('/debug_recipe/<int:recipe_id>')
def debug_recipe(recipe_id):
    """Debug route to test recipe method rendering"""
    recipe = Recipe.query.get_or_404(recipe_id)
    return render_template('debug_recipe.html', recipe=recipe)

@main_bp.route('/my-conversions')
@login_required
def my_conversions():
    """Display user's saved recipe conversions"""
    conversions = RecipeConversion.query.filter_by(user_id=current_user.id).order_by(RecipeConversion.created_at.desc()).all()
    return render_template('my_conversions.html', conversions=conversions)

@main_bp.route('/conversion/<int:conversion_id>')
@login_required
def view_conversion(conversion_id):
    """View a specific recipe conversion"""
    conversion = RecipeConversion.query.get_or_404(conversion_id)
    
    # Check if user owns this conversion
    if conversion.user_id != current_user.id:
        flash('You can only view your own recipe conversions.', 'error')
        return redirect(url_for('main.my_conversions'))
    
    # Increment access count
    conversion.access_count += 1
    db.session.commit()
    
    return render_template('view_conversion.html', conversion=conversion)

@main_bp.route('/save-conversion/<int:conversion_id>', methods=['POST'])
@login_required
def save_conversion(conversion_id):
    """Mark a conversion as saved/unsaved"""
    conversion = RecipeConversion.query.get_or_404(conversion_id)
    
    # Check if user owns this conversion
    if conversion.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    conversion.is_saved = not conversion.is_saved
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'is_saved': conversion.is_saved,
        'message': 'Conversion saved' if conversion.is_saved else 'Conversion unsaved'
    })

@main_bp.route('/delete-conversion/<int:conversion_id>', methods=['POST'])
@login_required
def delete_conversion(conversion_id):
    """Delete a recipe conversion"""
    conversion = RecipeConversion.query.get_or_404(conversion_id)
    
    # Check if user owns this conversion
    if conversion.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    db.session.delete(conversion)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Conversion deleted'})


# Image Serving Routes
@main_bp.route('/images/filesystem/<category>/<filename>')
def serve_filesystem_image(category, filename):
    """Serve images from filesystem storage (D: drive)"""
    from flask import send_file, abort
    import os
    from recipe_app.utils.image_storage import ImageStorageManager
    
    # Security check - only allow specific categories
    allowed_categories = ['profiles', 'recipes']
    if category not in allowed_categories:
        abort(404)
    
    # Build file path
    storage_path = ImageStorageManager.get_storage_path()
    file_path = os.path.join(storage_path, category, filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        abort(404)
    
    # Send file with caching headers
    response = send_file(file_path, 
                        as_attachment=False,
                        conditional=True)
    response.cache_control.max_age = 86400  # Cache for 24 hours
    return response


@main_bp.route('/images/database/<image_id>')
def serve_image(image_id):
    """Serve images from database storage"""
    from flask import Response
    from recipe_app.models.models import ImageStorage
    import base64
    
    # Get image from database
    db_image = ImageStorage.query.get_or_404(image_id)
    
    # Decode base64 data
    try:
        image_data = base64.b64decode(db_image.data)
    except Exception:
        abort(404)
    
    # Return image with proper headers
    return Response(
        image_data,
        mimetype=db_image.mime_type,
        headers={
            'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
            'Content-Length': len(image_data)
        }
    )


@main_bp.route('/api/images/upload', methods=['POST'])
@login_required
def upload_image():
    """API endpoint for uploading images"""
    from recipe_app.utils.image_storage import ImageStorageManager
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file provided'})
    
    file = request.files['image']
    category = request.form.get('category', 'profiles')
    
    # Upload image
    filename, message = ImageStorageManager.save_image(file, category)
    
    if filename:
        image_url = ImageStorageManager.get_image_url(filename, category)
        return jsonify({
            'success': True,
            'filename': filename,
            'url': image_url,
            'message': message
        })
    else:
        return jsonify({'success': False, 'message': message})


@main_bp.route('/api/images/delete', methods=['POST'])
@login_required
def delete_image():
    """API endpoint for deleting images"""
    from recipe_app.utils.image_storage import ImageStorageManager
    
    filename = request.json.get('filename')
    category = request.json.get('category', 'profiles')
    
    if not filename:
        return jsonify({'success': False, 'message': 'No filename provided'})
    
    # Delete image
    success = ImageStorageManager.delete_image(filename, category)
    
    return jsonify({
        'success': success,
        'message': 'Image deleted successfully' if success else 'Failed to delete image'
    })


@main_bp.route('/logout')
def logout():
    """Simple logout that redirects to HomeGrubHub home page"""
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect('https://homegrubhub.co.uk/')

@main_bp.route('/api/auth/status')
def auth_status():
    """Return authentication status and basic user info as JSON."""
    if current_user.is_authenticated:
        return jsonify({
            'is_authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email,
                'plan': getattr(current_user, 'current_plan', 'Free') or 'Free'
            }
        })
    return jsonify({'is_authenticated': False}), 200

# -------------------------------
# JSON API endpoints for Mobile/Web synchronicity
# -------------------------------

def _recipe_to_dict(recipe):
    """Serialize a Recipe for JSON APIs."""
    from flask import url_for
    image_url = None
    try:
        if getattr(recipe, 'image_file', None):
            image_url = url_for('static', filename=f'uploads/{recipe.image_file}', _external=True)
    except Exception:
        image_url = None

    # Average rating if available
    avg_rating = None
    try:
        if hasattr(recipe, 'average_rating') and callable(recipe.average_rating):
            avg_rating = recipe.average_rating()
    except Exception:
        avg_rating = None

    return {
        'id': recipe.id,
        'title': recipe.title,
        'description': (recipe.description or '')[:200],
        'image_url': image_url,
        'cuisine_type': getattr(recipe, 'cuisine_type', None),
        'country': getattr(recipe, 'country', None),
        'difficulty': getattr(recipe, 'difficulty', None),
        'servings': getattr(recipe, 'servings', None),
        'prep_time': getattr(recipe, 'prep_time', None),
        'cook_time': getattr(recipe, 'cook_time', None),
        'is_private': getattr(recipe, 'is_private', False),
        'user': {
            'id': getattr(recipe, 'user_id', None),
            'username': getattr(getattr(recipe, 'user', None), 'username', None),
        },
        'created_at': recipe.created_at.isoformat() if getattr(recipe, 'created_at', None) else None,
        'avg_rating': avg_rating,
    }

@main_bp.route('/api/auth/status')
def api_auth_status():
    """Return simple auth status and basic user info."""
    if current_user.is_authenticated:
        user_data = {
            'id': current_user.id,
            'username': getattr(current_user, 'username', None),
            'email': getattr(current_user, 'email', None),
            'plan': getattr(current_user, 'current_plan', None),
            'is_admin': getattr(current_user, 'is_admin', False),
        }
        return jsonify({'is_authenticated': True, 'user': user_data})
    return jsonify({'is_authenticated': False, 'user': None})

@main_bp.route('/api/recipes')
def api_list_recipes():
    """List recipes visible to the current user (public + own). Supports pagination."""
    from recipe_app.db import db as _db
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=12, type=int)

    if current_user.is_authenticated and hasattr(current_user, 'can_view_private_recipes') and current_user.can_view_private_recipes():
        query = Recipe.query
    else:
        query = Recipe.query.filter(
            _db.or_(
                Recipe.is_private == False,  # public
                Recipe.user_id == (current_user.id if current_user.is_authenticated else -1)
            )
        )

    query = query.order_by(Recipe.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    data = [_recipe_to_dict(r) for r in pagination.items]
    return jsonify({
        'recipes': data,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages
    })


@main_bp.route('/api/search')
def api_search_suggestions():
    """Provide recipe title suggestions for autocomplete."""
    q = (request.args.get('s') or '').strip()
    if not q:
        return jsonify([])

    if current_user.is_authenticated and hasattr(current_user, 'can_view_private_recipes') and current_user.can_view_private_recipes():
        query = Recipe.query
    else:
        query = Recipe.query.filter(
            db.or_(
                Recipe.is_private == False,
                Recipe.user_id == (current_user.id if current_user.is_authenticated else -1)
            )
        )

    results = query.filter(Recipe.title.ilike(f'%{q}%')).order_by(Recipe.title).limit(5).all()
    return jsonify([r.title for r in results])

@main_bp.route('/api/recipes/search')
def api_search_recipes():
    """Search recipes by title, applying same privacy rules as list."""
    from recipe_app.db import db as _db
    q = (request.args.get('q') or '').strip()
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=12, type=int)

    if not q:
        # Return empty result set to avoid dumping all data when no query
        return jsonify({'recipes': [], 'page': page, 'per_page': per_page, 'total': 0, 'pages': 0})

    if current_user.is_authenticated and hasattr(current_user, 'can_view_private_recipes') and current_user.can_view_private_recipes():
        query = Recipe.query.filter(Recipe.title.ilike(f'%{q}%'))
    else:
        query = Recipe.query.filter(
            _db.and_(
                Recipe.title.ilike(f'%{q}%'),
                _db.or_(
                    Recipe.is_private == False,
                    Recipe.user_id == (current_user.id if current_user.is_authenticated else -1)
                )
            )
        )

    query = query.order_by(Recipe.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    data = [_recipe_to_dict(r) for r in pagination.items]
    return jsonify({
        'recipes': data,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages
    })

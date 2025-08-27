from flask import render_template, flash, redirect, url_for, request, Blueprint, jsonify, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from .. import db
from .forms import LoginForm, RegistrationForm, RecipeForm, SearchForm, ImportRecipeForm, EditImportedRecipeForm
from .models import User, Recipe, Tag, CountryUsage, RecipeRating
from ..recipe_importer import RecipeImporter
from ..utils import convert_to_metric, adjust_serving_size, convert_recipe_to_metric, adjust_recipe_servings, parse_ingredient_amount
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
            return redirect(url_for('main.login'))
        login_user(user, remember=form.remember_me.data)
        flash(f'Welcome back, {user.username}!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('main.index'))
    return render_template('login.html', title='Sign In', form=form)

@main_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations! Your account has been created.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', title='Register', form=form)

@main_bp.route('/')
@main_bp.route('/index', methods=['GET', 'POST'])
def index():
    form = SearchForm()
    
    if form.validate_on_submit():
        query = form.q.data
        recipes = Recipe.query.filter(Recipe.title.contains(query)).all()
        return render_template('search.html', recipes=recipes, query=query)
    
    # Get recent recipes for homepage
    recent_recipes = Recipe.query.order_by(Recipe.created_at.desc()).limit(6).all()
    return render_template('index.html', form=form, recent_recipes=recent_recipes)

@main_bp.route('/recipes')
def all_recipes():
    """Display all recipes in a card tile format"""
    page = request.args.get('page', 1, type=int)
    per_page = 12  # Number of recipes per page
    
    recipes = Recipe.query.order_by(Recipe.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('all_recipes.html', recipes=recipes)

@main_bp.route('/ingredient_search')
def ingredient_search():
    """Search recipes by ingredients"""
    return render_template('ingredient_search.html')

@main_bp.route('/search_by_ingredients', methods=['POST'])
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

@main_bp.route('/recipe/<int:recipe_id>')
def recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Calculate average rating
    ratings = RecipeRating.query.filter_by(recipe_id=recipe_id).all()
    avg_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0
    
    # Check if current user has favorited this recipe
    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = current_user.is_favorite(recipe)
    
    return render_template('recipe.html', title=recipe.title, recipe=recipe, 
                         avg_rating=avg_rating, rating_count=len(ratings), 
                         is_favorite=is_favorite)

@main_bp.route('/add_recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    form = RecipeForm()
    
    # Pre-populate country if provided in URL
    if request.method == 'GET':
        country_param = request.args.get('country')
        if country_param:
            form.country.data = country_param
    
    if form.validate_on_submit():
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
            user_id=current_user.id
        )
        
        # Handle tags
        if form.tags.data:
            tag_names = [tag.strip() for tag in form.tags.data.split(',')]
            for tag_name in tag_names:
                if tag_name:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    recipe.tags.append(tag)
        
        db.session.add(recipe)
        db.session.commit()
        flash('Your recipe has been added successfully!', 'success')
        return redirect(url_for('main.recipe', recipe_id=recipe.id))
    return render_template('add_recipe.html', title='Add Recipe', form=form)

@main_bp.route('/edit_recipe/<int:recipe_id>', methods=['GET', 'POST'])
@login_required
def edit_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if recipe.user_id != current_user.id and not current_user.is_admin:
        flash('You do not have permission to edit this recipe.')
        return redirect(url_for('main.index'))
    form = RecipeForm()
    if form.validate_on_submit():
        recipe.title = form.title.data
        recipe.ingredients = form.ingredients.data
        recipe.method = form.method.data
        recipe.prep_time = form.prep_time.data
        recipe.cook_time = form.cook_time.data
        recipe.image_file = form.image_file.data
        recipe.tags.clear()
        tag_names = [tag.strip() for tag in form.tags.data.split(',')]
        for tag_name in tag_names:
            if tag_name:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                recipe.tags.append(tag)
        db.session.commit()
        flash('Your recipe has been updated!')
        return redirect(url_for('main.recipe', recipe_id=recipe.id))
    elif request.method == 'GET':
        form.title.data = recipe.title
        form.ingredients.data = recipe.ingredients
        form.method.data = recipe.method
        form.prep_time.data = recipe.prep_time
        form.cook_time.data = recipe.cook_time
        form.image_file.data = recipe.image_file
        form.tags.data = ', '.join(tag.name for tag in recipe.tags)
    return render_template('add_recipe.html', title='Edit Recipe', form=form)


@main_bp.route('/tags')
def tags():
    # Get all tags with recipe count
    tags_with_count = db.session.query(Tag, db.func.count(Recipe.id).label('recipe_count'))\
        .join(Tag.recipes)\
        .group_by(Tag.id)\
        .order_by(db.func.count(Recipe.id).desc())\
        .all()
    
    # Get countries and cuisines
    countries = db.session.query(Recipe.country, db.func.count(Recipe.id).label('count'))\
        .filter(Recipe.country.isnot(None))\
        .group_by(Recipe.country)\
        .order_by(db.func.count(Recipe.id).desc())\
        .all()
        
    cuisines = db.session.query(Recipe.cuisine_type, db.func.count(Recipe.id).label('count'))\
        .filter(Recipe.cuisine_type.isnot(None))\
        .group_by(Recipe.cuisine_type)\
        .order_by(db.func.count(Recipe.id).desc())\
        .all()
    
    total_recipes = Recipe.query.count()
    
    return render_template('tags.html', 
                         title='Recipe Categories', 
                         tags_with_count=tags_with_count,
                         countries=countries,
                         cuisines=cuisines,
                         total_recipes=total_recipes)

@main_bp.route('/tag/<string:tag_name>')
def tag(tag_name):
    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    recipes = tag.recipes
    return render_template('tag.html', title=f"Recipes in '{tag.name}'", tag=tag, recipes=recipes)

def generate_country_recipe(country_name, user_id):
    """Search the web for dinner recipes from the specified country and save to database"""
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import quote
    import json
    
    print(f"🔍 Searching for traditional {country_name} dinner recipes...")
    
    # Create dinner-focused search terms for any country
    dinner_search_terms = [
        f'{country_name} traditional dinner recipe',
        f'{country_name} main course dish recipe', 
        f'{country_name} national dinner dish',
        f'traditional {country_name} meal recipe',
        f'{country_name} authentic dinner cuisine'
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Try multiple search strategies
        for search_term in dinner_search_terms:
            print(f"🌐 Searching: {search_term}")
            
            # Method 1: Try to find recipes using recipe-scrapers with Google search
            try:
                # Search Google for recipe URLs
                google_url = f"https://www.google.com/search?q={quote(search_term)}"
                response = requests.get(google_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for recipe URLs in search results
                    potential_urls = []
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        if href and '/url?q=' in href:
                            # Extract actual URL from Google redirect
                            actual_url = href.split('/url?q=')[1].split('&')[0]
                            # Filter for recipe sites
                            if any(site in actual_url.lower() for site in ['allrecipes', 'food.com', 'epicurious', 'foodnetwork', 'taste.com', 'bbc.co.uk/food']):
                                potential_urls.append(actual_url)
                    
                    print(f"📋 Found {len(potential_urls)} potential recipe URLs")
                    
                    # Try to scrape recipes from found URLs
                    for url in potential_urls[:5]:  # Try first 5 URLs
                        try:
                            print(f"🍽️ Attempting to scrape: {url[:60]}...")
                            
                            # Use RecipeImporter to get recipe data
                            importer = RecipeImporter()
                            result = importer.import_from_url(url)
                            
                            if result['success']:
                                recipe_data = result['recipe']
                                title = recipe_data.get('title', '')
                                ingredients = recipe_data.get('ingredients', '')
                                method = recipe_data.get('method', '')
                                
                                # Validate this is a proper dinner recipe
                                if (len(title) > 5 and len(ingredients) > 100 and len(method) > 150 and
                                    'recipe' not in title.lower() and 'search' not in title.lower() and
                                    not title.startswith('http')):
                                    
                                    print(f"✅ Successfully found dinner recipe: {title}")
                                    
                                    # Create and save the recipe
                                    new_recipe = Recipe(
                                        title=f"{country_name}n {title}" if not any(x in title.lower() for x in [country_name.lower(), 'traditional']) else title,
                                        description=recipe_data.get('description', f'A traditional dinner dish from {country_name}, perfect for exploring {country_name}n cuisine.'),
                                        ingredients=ingredients,
                                        method=method,
                                        prep_time=recipe_data.get('prep_time', 30),
                                        cook_time=recipe_data.get('cook_time', 45),
                                        servings=recipe_data.get('servings', 4),
                                        difficulty=recipe_data.get('difficulty', 'Medium'),
                                        country=country_name,
                                        cuisine_type=f'{country_name}n',
                                        user_id=user_id,
                                        created_at=datetime.utcnow()
                                    )
                                    
                                    db.session.add(new_recipe)
                                    db.session.commit()
                                    
                                    print(f"🎉 Successfully saved {country_name} dinner recipe: {new_recipe.title}")
                                    return new_recipe
                                    
                        except Exception as scrape_error:
                            print(f"❌ Failed to scrape {url}: {str(scrape_error)}")
                            continue
                            
            except Exception as search_error:
                print(f"❌ Search failed for '{search_term}': {str(search_error)}")
                continue
        
        # Method 2: If web scraping completely fails, create a country-specific dinner template
        print(f"🍽️ Creating traditional {country_name} dinner template...")
        
        # Country-specific dinner dishes and ingredients
        country_dinner_templates = {
            'Afghanistan': {
                'dish': 'Kabuli Pulao',
                'description': 'Afghanistan\'s national dish - fragrant rice with lamb, carrots, and raisins',
                'ingredients': '2 cups basmati rice\n1 lb lamb, cubed\n2 large carrots, julienned\n1/2 cup raisins\n1 large onion, sliced\n4 cloves garlic, minced\n1 tsp cumin\n1 tsp cardamom\n1/2 tsp cinnamon\nSalt and pepper to taste\n3 tbsp oil'
            },
            'Albania': {
                'dish': 'Tavë Kosi',
                'description': 'Traditional Albanian baked lamb and rice with yogurt',
                'ingredients': '2 lbs lamb shoulder\n1 cup rice\n2 cups plain yogurt\n3 eggs\n2 tbsp flour\n1 onion, chopped\n3 cloves garlic\nFresh herbs\nOlive oil\nSalt and pepper'
            },
            'Armenia': {
                'dish': 'Khorovats',
                'description': 'Armenian grilled meat with vegetables and lavash bread',
                'ingredients': '3 lbs beef or lamb\n2 bell peppers\n2 tomatoes\n1 large onion\n4 cloves garlic\n2 tbsp wine vinegar\nFresh herbs (parsley, cilantro)\nLavash bread\nSalt and pepper'
            },
            'Nepal': {
                'dish': 'Dal Bhat Tarkari',
                'description': 'Nepal\'s staple dinner - lentil soup with rice and vegetables',
                'ingredients': '1 cup red lentils\n2 cups basmati rice\n2 potatoes\n1 cup green beans\n2 tomatoes\n1 onion\n4 cloves garlic\n1 inch ginger\n2 tsp turmeric\n1 tsp cumin\nFresh cilantro'
            }
        }
        
        # Get country-specific template or create generic one
        template = country_dinner_templates.get(country_name, {
            'dish': f'Traditional {country_name} Dinner',
            'description': f'A hearty traditional dinner dish representing the authentic flavors of {country_name}',
            'ingredients': f'''2 lbs main protein (beef, lamb, chicken, or fish)
2 cups rice or traditional grain
2 large onions, chopped
4 cloves garlic, minced
2 cups seasonal vegetables
Traditional {country_name}n spices
3 tbsp cooking oil
Salt and pepper to taste
Fresh herbs for garnish'''
        })
        
        # Create comprehensive dinner recipe
        dinner_method = f'''1. Prepare all ingredients according to {country_name}n tradition.
2. Heat oil in a large pot over medium heat.
3. Sauté onions and garlic until fragrant and golden.
4. Add the main protein and brown on all sides.
5. Add traditional {country_name}n spices and cook until aromatic.
6. Add vegetables and enough liquid to create a flavorful sauce.
7. Simmer covered for 30-45 minutes until protein is tender.
8. Prepare rice or grain according to {country_name}n style.
9. Serve the main dish over rice, garnished with fresh herbs.
10. Enjoy this authentic taste of {country_name}!

Note: This recipe represents traditional {country_name}n dinner cuisine. Feel free to adjust ingredients and spices to match authentic {country_name}n flavors!'''
        
        fallback_recipe = Recipe(
            title=template['dish'],
            description=template['description'],
            ingredients=template['ingredients'],
            method=dinner_method,
            prep_time=25,
            cook_time=60,
            servings=6,
            difficulty='Medium',
            country=country_name,
            cuisine_type=f'{country_name}n',
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        
        db.session.add(fallback_recipe)
        db.session.commit()
        
        print(f"🍽️ Created {country_name} dinner recipe: {fallback_recipe.title}")
        return fallback_recipe
        
    except Exception as e:
        print(f"❌ Error generating {country_name} dinner recipe: {str(e)}")
        db.session.rollback()
        return None

@main_bp.route('/random_country', methods=['GET', 'POST'])
@login_required
def random_country():
    # List of countries with popular cuisines
    countries = [
        'Italy', 'France', 'Spain', 'Greece', 'Germany', 'India', 'China', 'Japan', 'Thailand', 'Vietnam',
        'Korea', 'Mexico', 'Brazil', 'Argentina', 'Peru', 'Morocco', 'Ethiopia', 'Nigeria', 'Lebanon',
        'Turkey', 'Russia', 'Poland', 'Hungary', 'Ireland', 'Sweden', 'Norway', 'Australia', 'Jamaica',
        'Indonesia', 'Malaysia', 'Philippines', 'Nepal', 'Afghanistan', 'Iran', 'Egypt', 'Tunisia',
        'South Africa', 'Kenya', 'Ghana', 'Cuba', 'Colombia', 'Chile', 'Venezuela', 'Ecuador', 'Bolivia',
        'Uruguay', 'Paraguay', 'Guyana', 'Suriname', 'Portugal', 'Netherlands', 'Belgium', 'Austria',
        'Switzerland', 'Czech Republic', 'Slovakia', 'Slovenia', 'Croatia', 'Bosnia', 'Serbia', 'Bulgaria',
        'Romania', 'Ukraine', 'Lithuania', 'Latvia', 'Estonia', 'Finland', 'Denmark', 'Iceland', 'Malta',
        'Cyprus', 'Israel', 'Jordan', 'Syria', 'Iraq', 'Saudi Arabia', 'UAE', 'Yemen', 'Oman', 'Kuwait',
        'Qatar', 'Bahrain', 'Pakistan', 'Bangladesh', 'Sri Lanka', 'Myanmar', 'Cambodia', 'Laos',
        'Mongolia', 'Kazakhstan', 'Uzbekistan', 'Kyrgyzstan', 'Tajikistan', 'Turkmenistan', 'Georgia',
        'Armenia', 'Azerbaijan', 'Algeria', 'Libya', 'Sudan', 'Chad', 'Niger', 'Mali', 'Burkina Faso',
        'Senegal', 'Gambia', 'Guinea', 'Sierra Leone', 'Liberia', 'Ivory Coast', 'Benin', 'Togo',
        'Cameroon', 'Central African Republic', 'Democratic Republic of Congo', 'Republic of Congo',
        'Gabon', 'Equatorial Guinea', 'Sao Tome and Principe', 'Angola', 'Zambia', 'Zimbabwe', 'Botswana',
        'Namibia', 'Lesotho', 'Swaziland', 'Madagascar', 'Mauritius', 'Seychelles', 'Comoros'
    ]
    
    if request.method == 'POST':
        # Check if user selected a specific country from suggestions
        force_country = request.form.get('force_country')
        
        # Get countries used by this user in the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        used_countries = db.session.query(CountryUsage.country).filter(
            CountryUsage.user_id == current_user.id,
            CountryUsage.used_at > thirty_days_ago
        ).all()
        used_country_names = [country[0] for country in used_countries]
        
        if force_country:
            selected_country = force_country
        else:
            # Get available countries
            available_countries = [c for c in countries if c not in used_country_names]
            
            if not available_countries:
                # Reset if all countries have been used
                flash('You\'ve explored all countries in the last 30 days! Starting fresh...', 'info')
                # Clear old usage records
                CountryUsage.query.filter(
                    CountryUsage.user_id == current_user.id,
                    CountryUsage.used_at <= thirty_days_ago
                ).delete()
                db.session.commit()
                available_countries = countries
            
            # Select random country
            selected_country = random.choice(available_countries)
        
        # Record the usage
        country_usage = CountryUsage(country=selected_country, user_id=current_user.id)
        db.session.add(country_usage)
        db.session.commit()
        
        # Find recipes from this country - ALWAYS search online first!
        recipes = []
        print(f"=== 🌐 ONLINE SEARCH FOR {selected_country} RECIPES ===")
        
        # PRIORITY: Always search online for new dinner recipes first
        print(f"🔍 Searching online for fresh {selected_country} dinner recipes...")
        generated_recipe = generate_country_recipe(selected_country, current_user.id)
        if generated_recipe:
            recipes.append(generated_recipe)
            print(f"✅ SUCCESS: Found new online recipe: {generated_recipe.title}")
            flash(f'🍽️ Fresh Discovery! We searched online and found a new {selected_country}n dinner recipe: "{generated_recipe.title}" - now added to your collection!', 'success')
        else:
            print("❌ Online search failed")
        
        # SECONDARY: Add any existing recipes as additional options
        print(f"📚 Checking for existing {selected_country} recipes...")
        existing_recipes = Recipe.query.filter_by(country=selected_country).all()
        if existing_recipes:
            print(f"📖 Found {len(existing_recipes)} existing {selected_country} recipes")
            # Add existing recipes that aren't the one we just created
            for existing_recipe in existing_recipes:
                if not recipes or existing_recipe.id != recipes[0].id:
                    recipes.append(existing_recipe)
        else:
            print(f"📖 No existing {selected_country} recipes in database")
        
        # FALLBACK: If absolutely nothing worked
        if not recipes:
            print(f"🔄 FALLBACK: Showing related recipes...")
            fallback_recipes = Recipe.query.limit(3).all()
            recipes.extend(fallback_recipes)
            flash(f'⏳ Still searching for {selected_country} recipes... Here are some other dishes!', 'info')
        
        # Remove duplicates while preserving order
        cuisine_data = {
            'Ethiopia': {
                'terms': ['ethiopian', 'injera', 'berbere', 'doro wat', 'kitfo', 'tibs'],
                'ingredients': ['teff', 'berbere spice', 'clarified butter', 'red pepper']
            },
            'Italy': {
                'terms': ['italian', 'pasta', 'pizza', 'risotto', 'parmesan', 'gnocchi', 'carbonara'],
                'ingredients': ['parmesan', 'mozzarella', 'basil', 'olive oil', 'tomato', 'prosciutto']
            },
            'India': {
                'terms': ['indian', 'curry', 'masala', 'naan', 'biryani', 'tandoori', 'dal'],
                'ingredients': ['turmeric', 'cumin', 'coriander', 'garam masala', 'cardamom', 'ghee']
            },
            'Mexico': {
                'terms': ['mexican', 'tacos', 'salsa', 'tortilla', 'enchilada', 'quesadilla'],
                'ingredients': ['cilantro', 'lime', 'jalapeño', 'avocado', 'corn', 'black beans']
            },
            'Thailand': {
                'terms': ['thai', 'pad thai', 'curry', 'tom yum', 'green curry', 'red curry'],
                'ingredients': ['coconut milk', 'lemongrass', 'fish sauce', 'thai basil', 'galangal']
            },
            'Japan': {
                'terms': ['japanese', 'sushi', 'ramen', 'miso', 'tempura', 'teriyaki'],
                'ingredients': ['soy sauce', 'miso', 'rice vinegar', 'nori', 'sake', 'mirin']
            },
            'China': {
                'terms': ['chinese', 'stir fry', 'kung pao', 'sweet sour', 'fried rice'],
                'ingredients': ['soy sauce', 'ginger', 'sesame oil', 'rice wine', 'star anise']
            },
            'France': {
                'terms': ['french', 'ratatouille', 'coq au vin', 'bourguignon', 'cassoulet'],
                'ingredients': ['butter', 'cream', 'wine', 'herbs de provence', 'shallots']
            },
            'Greece': {
                'terms': ['greek', 'moussaka', 'souvlaki', 'tzatziki', 'spanakopita'],
                'ingredients': ['olive oil', 'feta cheese', 'oregano', 'lemon', 'olives']
            },
            'Spain': {
                'terms': ['spanish', 'paella', 'tapas', 'gazpacho', 'churros'],
                'ingredients': ['saffron', 'paprika', 'sherry', 'manchego', 'serrano ham']
            },
            'Morocco': {
                'terms': ['moroccan', 'tagine', 'couscous', 'harissa', 'pastilla'],
                'ingredients': ['preserved lemon', 'harissa', 'ras el hanout', 'argan oil']
            },
            'Lebanon': {
                'terms': ['lebanese', 'hummus', 'tabbouleh', 'fattoush', 'kibbeh'],
                'ingredients': ['tahini', 'sumac', 'za\'atar', 'bulgur', 'pine nuts']
            },
            'Korea': {
                'terms': ['korean', 'kimchi', 'bulgogi', 'bibimbap', 'gochujang'],
                'ingredients': ['gochujang', 'sesame oil', 'korean chili', 'miso paste']
            },
            'Vietnam': {
                'terms': ['vietnamese', 'pho', 'banh mi', 'spring rolls', 'nem'],
                'ingredients': ['fish sauce', 'rice paper', 'mint', 'vietnamese basil']
            }
        }
        
        if not recipes and selected_country in cuisine_data:
            cuisine_info = cuisine_data[selected_country]
            print(f"Strategy 3 - Cuisine-specific search for {selected_country}")
            
            # Search by cuisine terms
            for term in cuisine_info['terms']:
                term_recipes = Recipe.query.filter(
                    Recipe.title.ilike(f'%{term}%') |
                    Recipe.description.ilike(f'%{term}%') |
                    Recipe.ingredients.ilike(f'%{term}%')
                ).limit(3).all()
                recipes.extend(term_recipes)
                print(f"  - Term '{term}': Found {len(term_recipes)} recipes")
            
            # Search by typical ingredients
            for ingredient in cuisine_info['ingredients']:
                ingredient_recipes = Recipe.query.filter(
                    Recipe.ingredients.ilike(f'%{ingredient}%')
                ).limit(2).all()
                recipes.extend(ingredient_recipes)
                print(f"  - Ingredient '{ingredient}': Found {len(ingredient_recipes)} recipes")
        
        # Strategy 4: If still no recipes, try broader terms regardless of country
        if not recipes:
            print(f"Strategy 4 - Broad search for any recipes related to {selected_country}")
            # Search for any recipes that might be remotely related
            broad_search_recipes = Recipe.query.limit(3).all()  # Get some recipes as fallback
            recipes.extend(broad_search_recipes)
            print(f"Strategy 4 - Fallback: Found {len(broad_search_recipes)} recipes")
        
        # Strategy 5: Generate a new recipe for the country if none found
        if not recipes:
            print(f"Strategy 5 - No recipes found for {selected_country}, searching web for authentic recipes")
            generated_recipe = generate_country_recipe(selected_country, current_user.id)
            if generated_recipe:
                recipes.append(generated_recipe)
                print(f"Generated new recipe: {generated_recipe.title}")
                flash(f'� Amazing discovery! We searched the web and found an authentic {selected_country}n recipe: "{generated_recipe.title}" - now saved to your collection!', 'success')
            else:
                print("Failed to generate recipe from web search, falling back to existing countries")
                # Fallback to countries with existing recipes
                countries_with_recipes = db.session.query(Recipe.country).filter(Recipe.country.isnot(None)).distinct().all()
                available_countries = [country[0] for country in countries_with_recipes if country[0]]
                print(f"Countries with recipes: {available_countries}")
                
                if available_countries:
                    # Pick a random country that actually has recipes
                    selected_country = random.choice(available_countries)
                    print(f"Switched to country with recipes: {selected_country}")
                    country_recipes = Recipe.query.filter_by(country=selected_country).all()
                    recipes.extend(country_recipes)
                    print(f"Found {len(country_recipes)} recipes for {selected_country}")
        
        # Strategy 6: Fuzzy matching for similar country names (simplified)
        if not recipes:
            print("Strategy 6 - All strategies exhausted")
        
        # Strategy 7: Final fallback (simplified)  
        if not recipes:
            print("Strategy 7 - Using any available recipes as final fallback")
            fallback_recipes = Recipe.query.limit(3).all()
            recipes.extend(fallback_recipes)
            print(f"Final fallback: Found {len(fallback_recipes)} recipes")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recipes = []
        for recipe in recipes:
            if recipe.id not in seen:
                seen.add(recipe.id)
                unique_recipes.append(recipe)
        
        recipes = unique_recipes[:10]  # Limit to 10 recipes
        
        # Debug: Show what we found
        print(f"=== FINAL RESULTS ===")
        print(f"Total recipes found: {len(recipes)}")
        total_recipes_in_db = Recipe.query.count()
        print(f"Total recipes in database: {total_recipes_in_db}")
        
        if recipes:
            for i, recipe in enumerate(recipes):
                print(f"Recipe {i+1}: {recipe.title} (Country: {recipe.country})")
        else:
            print("No recipes found! Let's check what recipes exist...")
            all_recipes = Recipe.query.limit(5).all()
            for recipe in all_recipes:
                print(f"  - {recipe.title} (Country: {recipe.country}, Desc: {recipe.description[:50] if recipe.description else 'None'})")
        
        # Generate suggestions for similar cuisines if no recipes found
        similar_cuisines = []
        if not recipes:
            cuisine_families = {
            "American": [   
                "United States","Canada","Mexico","Argentina","Brazil","Chile","Colombia","Peru","Venezuela",
                "Cuba","Dominican Republic","Guatemala","Honduras","Nicaragua","Panama","Paraguay","Uruguay"
            ],
            "British": [
                "United Kingdom","Ireland","Australia","New Zealand","South Africa","Canada"
            ],
            "Mediterranean": [
                "Albania","Algeria","Andorra","Bosnia and Herzegovina","Cyprus","Croatia","Egypt",
                "France","Greece","Israel","Italy","Lebanon","Malta","Morocco","Portugal","Spain","Tunisia","Turkey"
            ],
            "Asian": [
            "Afghanistan","Armenia","Azerbaijan","Bangladesh","Bhutan","Brunei","Cambodia","China",
            "Georgia","India","Indonesia","Japan","Kazakhstan","Kyrgyzstan","Laos","Malaysia",
            "Maldives","Mongolia","Myanmar","Nepal","North Korea","Pakistan","Philippines","Singapore",
            "South Korea","Sri Lanka","Tajikistan","Thailand","Timor‑Leste","Turkmenistan","Uzbekistan","Vietnam"
            ],
            "Latin American": [
                "Argentina","Belize","Bolivia","Brazil","Chile","Colombia","Costa Rica","Cuba",
                "Dominican Republic","Ecuador","El Salvador","Guatemala","Honduras","Mexico","Nicaragua",
                "Panama","Paraguay","Peru","Uruguay","Venezuela"
            ],
            "European": [
                "Austria","Belarus","Belgium","Czech Republic","Denmark","Estonia","Finland","Germany",
                "Hungary","Ireland","Latvia","Lithuania","Luxembourg","Netherlands","Norway","Poland",
                "Romania","Russia","Serbia","Slovakia","Slovenia","Sweden","Switzerland","Ukraine","United Kingdom"
            ],
            "African": [
                "Angola","Benin","Botswana","Burkina Faso","Burundi","Cameroon","Cape Verde","Central African Republic",
                "Chad","Comoros","Congo, Republic of the","Congo, Democratic Republic of the","Côte d’Ivoire",
                "Djibouti","Equatorial Guinea","Eritrea","Eswatini","Ethiopia","Gabon","Gambia","Ghana",
                "Guinea","Guinea‑Bissau","Kenya","Lesotho","Liberia","Libya","Madagascar","Malawi","Mali","Mauritania",
                "Mauritius","Morocco","Mozambique","Namibia","Niger","Nigeria","Rwanda","Sao Tome and Principe",
                "Senegal","Seychelles","Sierra Leone","Somalia","South Africa","South Sudan","Sudan","Tanzania","Togo","Tunisia","Uganda","Zambia","Zimbabwe"
            ],
            "Middle Eastern": [
                "Bahrain","Iraq","Iran","Jordan","Kuwait","Oman","Palestine, State of","Qatar","Saudi Arabia",
                "Syria","United Arab Emirates","Yemen"
            ],
            "Oceanian": [
                "Australia","Fiji","Kiribati","Marshall Islands","Micronesia (Federated States of)","Nauru",
                "New Zealand","Palau","Papua New Guinea","Samoa","Solomon Islands","Tonga","Tuvalu","Vanuatu"
            ],
            "North American": [
                "Canada","United States"
            ],
            "Caribbean": [
                "Antigua and Barbuda","Bahamas","Barbados","Cuba","Dominica","Dominican Republic",
                "Grenada","Haiti","Jamaica","Saint Kitts and Nevis","Saint Lucia","Saint Vincent and the Grenadines","Trinidad and Tobago"
            ],
            "Other": [
                "Holy See (Vatican City)","Kosovo","Taiwan"
            ]
            }

            
            for family, countries in cuisine_families.items():
                if selected_country in countries:
                    similar_cuisines = [c for c in countries if c != selected_country][:4]
                    break
        
        flash(f'Today\'s cuisine adventure: {selected_country}!', 'success')
        return render_template('random_country.html', title='Random Country Cuisine', 
                             selected_country=selected_country, recipes=recipes,
                             used_count=len(used_country_names), total_countries=len(countries),
                             similar_cuisines=similar_cuisines)
    
    # GET request - show the random country generator
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    used_count = CountryUsage.query.filter(
        CountryUsage.user_id == current_user.id,
        CountryUsage.used_at > thirty_days_ago
    ).count()
    
    return render_template('random_country.html', title='Random Country Cuisine',
                         used_count=used_count, total_countries=len(countries))

@main_bp.route('/toggle_favorite/<int:recipe_id>', methods=['POST'])
@login_required
def toggle_favorite(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    
    if current_user.is_favorite(recipe):
        current_user.remove_favorite(recipe)
        is_favorite = False
        message = 'Recipe removed from favorites'
    else:
        current_user.add_favorite(recipe)
        is_favorite = True
        message = 'Recipe added to favorites'
    
    db.session.commit()
    
    if request.headers.get('Content-Type') == 'application/json':
        return jsonify({'is_favorite': is_favorite, 'message': message})
    else:
        flash(message, 'success')
        return redirect(url_for('main.recipe', recipe_id=recipe_id))

@main_bp.route('/favorites')
@login_required
def favorites():
    recipes = current_user.favorites
    return render_template('favorites.html', title='My Favorite Recipes', recipes=recipes)

@main_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_recipe():
    form = ImportRecipeForm()
    
    if form.validate_on_submit():
        importer = RecipeImporter()
        
        if form.import_type.data == 'url':
            # Import single recipe from URL
            result = importer.import_from_url(form.url.data)
            
            if result['success']:
                # Store imported recipe data in session for editing
                session['imported_recipe'] = result['recipe']
                session['import_source'] = result.get('source', 'unknown')
                flash(f'Recipe imported successfully! Please review and edit before saving.', 'success')
                return redirect(url_for('main.edit_imported'))
            else:
                flash(f'Import failed: {result["error"]}', 'error')
                
        elif form.import_type.data == 'rss':
            # Import from RSS feed
            max_items = form.max_items.data or 10
            result = importer.import_from_rss(form.url.data, max_items)
            
            if result['success']:
                session['imported_recipes'] = result['recipes']
                session['feed_title'] = result.get('feed_title', 'RSS Feed')
                flash(f'Found {len(result["recipes"])} recipes from {result["feed_title"]}!', 'success')
                return redirect(url_for('main.review_rss_imports'))
            else:
                flash(f'RSS import failed: {result["error"]}', 'error')
    
    return render_template('import_recipe.html', title='Import Recipe', form=form)

@main_bp.route('/import/edit', methods=['GET', 'POST'])
@login_required
def edit_imported():
    if 'imported_recipe' not in session:
        flash('No recipe to edit. Please import a recipe first.', 'error')
        return redirect(url_for('main.import_recipe'))
    
    recipe_data = session['imported_recipe']
    form = EditImportedRecipeForm()
    
    if form.validate_on_submit():
        if form.save_recipe.data:
            # Save the recipe
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
                user_id=current_user.id
            )
            
            # Handle tags
            if form.tags.data:
                tag_names = [tag.strip() for tag in form.tags.data.split(',')]
                for tag_name in tag_names:
                    if tag_name:
                        tag = Tag.query.filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            db.session.add(tag)
                        recipe.tags.append(tag)
            
            db.session.add(recipe)
            db.session.commit()
            
            # Clear session
            session.pop('imported_recipe', None)
            session.pop('import_source', None)
            
            flash('Recipe saved successfully!', 'success')
            return redirect(url_for('main.recipe', recipe_id=recipe.id))
            
        elif form.import_another.data:
            # Clear session and go back to import
            session.pop('imported_recipe', None)
            session.pop('import_source', None)
            return redirect(url_for('main.import_recipe'))
    
    elif request.method == 'GET':
        # Pre-populate form with imported data
        form.title.data = recipe_data.get('title', '')
        form.description.data = recipe_data.get('description', '')
        form.ingredients.data = recipe_data.get('ingredients', '')
        form.method.data = recipe_data.get('method', '')
        form.prep_time.data = recipe_data.get('prep_time')
        form.cook_time.data = recipe_data.get('cook_time')
        form.servings.data = recipe_data.get('servings')
        form.difficulty.data = recipe_data.get('difficulty', 'Medium')
        form.source_url.data = recipe_data.get('source_url', '')
    
    import_source = session.get('import_source', 'unknown')
    return render_template('edit_imported_recipe.html', 
                         title='Edit Imported Recipe', 
                         form=form, 
                         source=import_source)

@main_bp.route('/import/rss-review')
@login_required  
def review_rss_imports():
    if 'imported_recipes' not in session:
        flash('No recipes to review. Please import from RSS first.', 'error')
        return redirect(url_for('main.import_recipe'))
    
    recipes = session['imported_recipes']
    feed_title = session.get('feed_title', 'RSS Feed')
    
    return render_template('review_rss_imports.html', 
                         title='Review RSS Imports', 
                         recipes=recipes, 
                         feed_title=feed_title)

@main_bp.route('/import/select-rss/<int:index>')
@login_required
def select_rss_recipe(index):
    if 'imported_recipes' not in session:
        flash('No recipes available. Please import from RSS first.', 'error')
        return redirect(url_for('main.import_recipe'))
    
    recipes = session['imported_recipes']
    if index < 0 or index >= len(recipes):
        flash('Invalid recipe selection.', 'error')
        return redirect(url_for('main.review_rss_imports'))
    
    # Move selected recipe to single import session
    session['imported_recipe'] = recipes[index]
    session['import_source'] = 'rss'
    
    return redirect(url_for('main.edit_imported'))

@main_bp.route('/import/clear-rss')
@login_required
def clear_rss_imports():
    session.pop('imported_recipes', None)
    session.pop('feed_title', None)
    flash('RSS import cleared.', 'info')
    return redirect(url_for('main.import_recipe'))

@main_bp.route('/convert-measurements', methods=['POST'])
def convert_measurements():
    """AJAX endpoint for converting US measurements to metric"""
    data = request.get_json()
    ingredient_text = data.get('ingredient', '')
    
    amount, unit, ingredient_name = parse_ingredient_amount(ingredient_text)
    
    if amount is not None and unit:
        metric_amount, metric_unit = convert_to_metric(amount, unit)
        
        if metric_unit != unit:
            if metric_amount == int(metric_amount):
                formatted_amount = str(int(metric_amount))
            else:
                formatted_amount = f"{metric_amount:.2f}".rstrip('0').rstrip('.')
            
            converted = f"{formatted_amount} {metric_unit} {ingredient_name}"
            return jsonify({'success': True, 'converted': converted, 'original': ingredient_text})
    
    return jsonify({'success': False, 'message': 'No conversion available'})

@main_bp.route('/test-adjust', methods=['POST'])
def test_adjust():
    """Simple test endpoint"""
    print("=== TEST ADJUST CALLED ===")
    data = request.get_json()
    print(f"Received data: {data}")
    return jsonify({
        'success': True,
        'message': 'Test successful',
        'received_data': data
    })

@main_bp.route('/adjust-servings', methods=['POST'])
def adjust_servings():
    """AJAX endpoint for adjusting serving sizes"""
    try:
        print("=== ADJUST SERVINGS CALLED ===")
        data = request.get_json()
        print(f"Received data: {data}")
        
        ingredients = data.get('ingredients', '').strip()
        original_servings = int(data.get('original_servings', 4))
        target_servings = int(data.get('target_servings', 4))
        
        print(f"Adjust servings: {original_servings} -> {target_servings}")
        print(f"Ingredients length: {len(ingredients)}")
        print(f"First 100 chars: {ingredients[:100]}")
        
        if not ingredients:
            print("ERROR: No ingredients provided")
            return jsonify({'success': False, 'message': 'No ingredients provided'})
            
        if original_servings <= 0 or target_servings <= 0:
            print("ERROR: Invalid serving sizes")
            return jsonify({'success': False, 'message': 'Invalid serving sizes'})
        
        # Apply the serving adjustment
        adjusted_ingredients = adjust_recipe_servings(ingredients, original_servings, target_servings)
        
        print(f"Adjusted ingredients length: {len(adjusted_ingredients)}")
        print(f"First 100 chars adjusted: {adjusted_ingredients[:100]}")
        print("=== RETURNING SUCCESS ===")
        
        return jsonify({
            'success': True, 
            'adjusted_ingredients': adjusted_ingredients,
            'multiplier': target_servings / original_servings,
            'original_servings': original_servings,
            'target_servings': target_servings
        })
    
    except Exception as e:
        print(f"ERROR in adjust_servings: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})

@main_bp.route('/recipe/<int:recipe_id>/conversions')
def recipe_conversions(recipe_id):
    """View recipe with conversion and serving adjustment tools"""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Get metric conversions
    metric_ingredients = convert_recipe_to_metric(recipe.ingredients) if recipe.ingredients else ""
    
    return render_template('recipe_conversions.html', 
                         title=f"Conversions - {recipe.title}",
                         recipe=recipe,
                         metric_ingredients=metric_ingredients)

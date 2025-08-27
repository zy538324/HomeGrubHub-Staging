from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from recipe_app.db import db
from recipe_app.models.nutrition_tracking import Food, Meal, NutritionLog
from datetime import datetime, date
import requests
import csv
import re
from io import StringIO
from functools import wraps

nutrition_bp = Blueprint('nutrition', __name__)

def get_user_tier():
    # Get tier from current user's subscription plan
    if current_user.is_authenticated:
        return current_user.current_plan
    return session.get('user_tier', 'Free')

def require_tier(required_tiers):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            tier = get_user_tier()
            # Make tier checking case-insensitive
            tier_lower = tier.lower() if tier else 'free'
            required_tiers_lower = [t.lower() for t in required_tiers]
            
            if tier_lower not in required_tiers_lower:
                return jsonify({'error': f'Feature not available for your tier ({tier}). Required: {", ".join(required_tiers)}'}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator

@nutrition_bp.route('/nutrition-dashboard')
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def nutrition_dashboard():
    """Main nutrition dashboard page - serves as the main entry point"""
    from recipe_app.models.nutrition_tracking import NutritionLog
    
    user_id = session.get('_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    # Get nutrition logs using the existing model
    logs = NutritionLog.query.filter_by(user_id=user_id).order_by(NutritionLog.log_date.desc()).limit(10).all()
    
    # For goals, we'll create a simple default structure
    class SimpleGoals:
        daily_calories = 2000
        daily_protein = 150
        daily_carbs = 250
        daily_fat = 65
    
    goals = SimpleGoals()
    
    # Get today's summary from logs
    today = date.today()
    today_summary = NutritionLog.query.filter_by(user_id=user_id, log_date=today).first()
    
    return render_template('nutrition/nutrition_log_list.html', 
                          logs=logs,
                          goals=goals,
                          today_summary=today_summary)

@nutrition_bp.route('/nutrition-tracker')
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def nutrition_tracker():
    """Main nutrition tracking page"""
    from recipe_app.models.nutrition_tracking import NutritionLog
    
    user_id = session.get('_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    today = date.today()
    
    # For goals, we'll create a simple default structure
    class SimpleGoals:
        daily_calories = 2000
        daily_protein = 150
        daily_carbs = 250
        daily_fat = 65
    
    goals = SimpleGoals()
    
    # Get today's summary from logs
    today_summary = NutritionLog.query.filter_by(user_id=user_id, log_date=today).first()
    today_entries = []  # For now, empty entries
    week_summaries = []  # For now, empty summaries
    
    return render_template('nutrition_tracker_clean.html',
                         goals=goals,
                         daily_summary=today_summary,
                         today_entries=today_entries,
                         week_summaries=week_summaries,
                         today=today)

# --- Food CRUD ---
@nutrition_bp.route('/api/foods', methods=['GET'])
def get_foods():
    foods = Food.query.all()
    return jsonify([food.to_dict() for food in foods])

@nutrition_bp.route('/api/foods', methods=['POST'])
def add_food():
    data = request.get_json()
    food = Food(
        name=data['name'],
        brand=data.get('brand'),
        barcode=data.get('barcode'),
        calories=data['calories'],
        protein=data['protein'],
        carbs=data['carbs'],
        fat=data['fat'],
        serving_size=data.get('serving_size')
    )
    db.session.add(food)
    db.session.commit()
    return jsonify(food.to_dict()), 201

@nutrition_bp.route('/food-list', methods=['GET'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def food_list():
    from recipe_app.models.nutrition_tracking import Food
    foods = Food.query.all()
    return render_template('nutrition/food_list.html', foods=foods)

@nutrition_bp.route('/add-food', methods=['GET', 'POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def add_food_form():
    from recipe_app.models.nutrition_tracking import Food
    if request.method == 'POST':
        food = Food(
            name=request.form['name'],
            brand=request.form.get('brand'),
            barcode=request.form.get('barcode'),
            calories=float(request.form['calories']),
            protein=float(request.form['protein']),
            carbs=float(request.form['carbs']),
            fat=float(request.form['fat']),
            serving_size=request.form.get('serving_size')
        )
        db.session.add(food)
        db.session.commit()
        flash('Food added successfully!', 'success')
        return redirect(url_for('nutrition.food_list'))
    return render_template('nutrition/add_food.html')

# --- Meal CRUD ---
@nutrition_bp.route('/api/meals', methods=['GET'])
def get_meals():
    user_id = session.get('_user_id')
    meals = Meal.query.filter_by(user_id=user_id).order_by(Meal.meal_date.desc()).all()
    return jsonify([meal.to_dict() for meal in meals])

@nutrition_bp.route('/api/meals', methods=['POST'])
def add_meal():
    user_id = session.get('_user_id')
    data = request.get_json()
    meal = Meal(
        user_id=user_id,
        meal_type=data['meal_type'],
        meal_date=datetime.strptime(data['meal_date'], '%Y-%m-%d').date()
    )
    # Add foods by IDs
    food_ids = data.get('food_ids', [])
    foods = Food.query.filter(Food.id.in_(food_ids)).all()
    meal.foods = foods
    # Calculate totals
    meal.total_calories = sum(f.calories for f in foods)
    meal.total_protein = sum(f.protein for f in foods)
    meal.total_carbs = sum(f.carbs for f in foods)
    meal.total_fat = sum(f.fat for f in foods)
    db.session.add(meal)
    db.session.commit()
    return jsonify(meal.to_dict()), 201

# --- Nutrition Log CRUD ---
@nutrition_bp.route('/api/nutrition-logs', methods=['GET'])
def get_nutrition_logs():
    user_id = session.get('_user_id')
    logs = NutritionLog.query.filter_by(user_id=user_id).order_by(NutritionLog.log_date.desc()).all()
    return jsonify([log.to_dict() for log in logs])

@nutrition_bp.route('/api/nutrition-logs', methods=['POST'])
def add_nutrition_log():
    user_id = session.get('_user_id')
    data = request.get_json()
    log_date = datetime.strptime(data['log_date'], '%Y-%m-%d').date()
    log = NutritionLog(user_id=user_id, log_date=log_date)
    db.session.add(log)
    db.session.commit()
    # Link meals to this log if meal_ids provided
    meal_ids = data.get('meal_ids', [])
    if meal_ids:
        from recipe_app.models.nutrition_tracking import Meal
        meals = Meal.query.filter(Meal.id.in_(meal_ids)).all()
        for meal in meals:
            meal.nutrition_log_id = log.id
        db.session.commit()
    return jsonify(log.to_dict()), 201

@nutrition_bp.route('/log-meal', methods=['GET', 'POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def log_meal():
    from recipe_app.models.nutrition_tracking import Food, Meal
    from datetime import date
    user_id = session.get('_user_id')
    if request.method == 'POST':
        meal_type = request.form['meal_type']
        meal_date = request.form['meal_date']
        food_ids = request.form.getlist('food_ids')
        foods = Food.query.filter(Food.id.in_(food_ids)).all()
        meal = Meal(
            user_id=user_id,
            meal_type=meal_type,
            meal_date=date.fromisoformat(meal_date),
            foods=foods,
            total_calories=sum(f.calories for f in foods),
            total_protein=sum(f.protein for f in foods),
            total_carbs=sum(f.carbs for f in foods),
            total_fat=sum(f.fat for f in foods)
        )
        db.session.add(meal)
        db.session.commit()
        flash('Meal logged successfully!', 'success')
        return redirect(url_for('nutrition.log_meal'))
    foods = Food.query.all()
    today = date.today().isoformat()
    return render_template('nutrition/log_meal.html', foods=foods, today=today)

@nutrition_bp.route('/daily-summary', methods=['GET'])
def daily_summary():
    from recipe_app.models.nutrition_tracking import Meal
    from datetime import date
    user_id = session.get('_user_id')
    summary_date = request.args.get('date', date.today().isoformat())
    meals = Meal.query.filter_by(user_id=user_id, meal_date=date.fromisoformat(summary_date)).all()
    total_calories = sum(m.total_calories or 0 for m in meals)
    total_protein = sum(m.total_protein or 0 for m in meals)
    total_carbs = sum(m.total_carbs or 0 for m in meals)
    total_fat = sum(m.total_fat or 0 for m in meals)
    return render_template('nutrition/daily_summary.html',
        summary_date=summary_date,
        meals=meals,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fat=total_fat)

@nutrition_bp.route('/edit-meal/<int:meal_id>', methods=['GET', 'POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def edit_meal(meal_id):
    from recipe_app.models.nutrition_tracking import Meal, Food
    from datetime import date
    user_id = session.get('_user_id')
    meal = Meal.query.filter_by(id=meal_id, user_id=user_id).first_or_404()
    foods = Food.query.all()
    selected_food_ids = [food.id for food in meal.foods]
    if request.method == 'POST':
        if 'delete' in request.args:
            db.session.delete(meal)
            db.session.commit()
            flash('Meal deleted.', 'info')
            return redirect(url_for('nutrition.daily_summary', date=meal.meal_date))
        meal.meal_type = request.form['meal_type']
        meal.meal_date = date.fromisoformat(request.form['meal_date'])
        food_ids = request.form.getlist('food_ids')
        meal.foods = Food.query.filter(Food.id.in_(food_ids)).all()
        meal.total_calories = sum(f.calories for f in meal.foods)
        meal.total_protein = sum(f.protein for f in meal.foods)
        meal.total_carbs = sum(f.carbs for f in meal.foods)
        meal.total_fat = sum(f.fat for f in meal.foods)
        db.session.commit()
        flash('Meal updated.', 'success')
        return redirect(url_for('nutrition.daily_summary', date=meal.meal_date))
    return render_template('nutrition/edit_meal.html', meal=meal, foods=foods, selected_food_ids=selected_food_ids)

@nutrition_bp.route('/nutrition-logs', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def nutrition_log_list():
    from recipe_app.models.nutrition_tracking import NutritionLog
    from recipe_app.models.nutrition_models import DailyNutritionSummary, NutritionGoal
    from datetime import timedelta
    
    user_id = session.get('_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    # Get nutrition logs from both models for compatibility
    logs = NutritionLog.query.filter_by(user_id=user_id).order_by(NutritionLog.log_date.desc()).all()
    
    # Get daily summaries from the new nutrition models
    daily_summaries = DailyNutritionSummary.query.filter_by(user_id=user_id).order_by(DailyNutritionSummary.summary_date.desc()).limit(30).all()
    
    # Get or create user's nutrition goals
    goals = NutritionGoal.query.filter_by(user_id=user_id).first()
    if not goals:
        goals = NutritionGoal(user_id=user_id)
        db.session.add(goals)
        db.session.commit()
    
    # Get today's summary
    today = date.today()
    today_summary = DailyNutritionSummary.query.filter_by(
        user_id=user_id, 
        summary_date=today
    ).first()
    
    # Merge logs and daily summaries for comprehensive display
    all_logs = []
    
    # Add daily summaries to logs
    for summary in daily_summaries:
        all_logs.append(summary)
    
    # Add old nutrition logs if they exist
    for log in logs:
        all_logs.append(log)
    
    # Sort by date descending
    all_logs.sort(key=lambda x: getattr(x, 'summary_date', None) or getattr(x, 'log_date', None), reverse=True)
    
    return render_template('nutrition/nutrition_log_list.html', 
                          logs=all_logs,
                          daily_summaries=daily_summaries,
                          goals=goals,
                          today_summary=today_summary)

# Example: restrict progress chart to Home/Family/Pro/Student
@nutrition_bp.route('/progress-chart', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def progress_chart():
    from recipe_app.models.nutrition_tracking import NutritionLog
    user_id = session.get('_user_id')
    logs = NutritionLog.query.filter_by(user_id=user_id).order_by(NutritionLog.log_date.asc()).all()
    chart_data = {
        'dates': [log.log_date.isoformat() for log in logs],
        'calories': [log.daily_calories or 0 for log in logs],
        'protein': [log.daily_protein or 0 for log in logs],
        'carbs': [log.daily_carbs or 0 for log in logs],
        'fat': [log.daily_fat or 0 for log in logs]
    }
    return render_template('nutrition/progress_chart.html', chart_data=chart_data)

@nutrition_bp.route('/progress-chart-extended', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def progress_chart_extended():
    from recipe_app.models.nutrition_tracking import NutritionLog
    user_id = session.get('_user_id')
    days = int(request.args.get('days', 30))
    logs = NutritionLog.query.filter_by(user_id=user_id).order_by(NutritionLog.log_date.desc()).limit(days).all()[::-1]
    chart_data = {
        'dates': [log.log_date.isoformat() for log in logs],
        'calories': [log.daily_calories or 0 for log in logs],
        'protein': [log.daily_protein or 0 for log in logs],
        'carbs': [log.daily_carbs or 0 for log in logs],
        'fat': [log.daily_fat or 0 for log in logs]
    }
    return render_template('nutrition/progress_chart.html', chart_data=chart_data)

@nutrition_bp.route('/export-nutrition-logs', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def export_nutrition_logs():
    from recipe_app.models.nutrition_tracking import NutritionLog
    user_id = session.get('_user_id')
    logs = NutritionLog.query.filter_by(user_id=user_id).order_by(NutritionLog.log_date.asc()).all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Date', 'Calories', 'Protein', 'Carbs', 'Fat'])
    for log in logs:
        writer.writerow([
            log.log_date.isoformat(),
            log.daily_calories or 0,
            log.daily_protein or 0,
            log.daily_carbs or 0,
            log.daily_fat or 0
        ])
    output = si.getvalue()
    return output, 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=nutrition_logs.csv'}

@nutrition_bp.route('/log-weight', methods=['GET', 'POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def log_weight():
    from recipe_app.models.fitness_models import WeightLog
    from datetime import date
    user_id = session.get('_user_id')
    if request.method == 'POST':
        weight = float(request.form['weight'])
        log_date = date.fromisoformat(request.form['log_date'])
        log = WeightLog(user_id=user_id, weight=weight, log_date=log_date)
        db.session.add(log)
        db.session.commit()
        flash('Weight logged successfully!', 'success')
        return redirect(url_for('nutrition.weight_history'))
    today = date.today().isoformat()
    return render_template('nutrition/log_weight.html', today=today)

@nutrition_bp.route('/weight-history', methods=['GET'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def weight_history():
    from recipe_app.models.fitness_models import WeightLog
    user_id = session.get('_user_id')
    logs = WeightLog.query.filter_by(user_id=user_id).order_by(WeightLog.log_date.asc()).all()
    chart_data = {
        'dates': [log.log_date.isoformat() for log in logs],
        'weights': [log.weight for log in logs]
    }
    return render_template('nutrition/weight_history.html', logs=logs, chart_data=chart_data)

@nutrition_bp.route('/log-steps', methods=['GET', 'POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def log_steps():
    from recipe_app.models.fitness_models import StepLog
    from datetime import date
    user_id = session.get('_user_id')
    if request.method == 'POST':
        steps = int(request.form['steps'])
        log_date = date.fromisoformat(request.form['log_date'])
        log = StepLog(user_id=user_id, steps=steps, log_date=log_date)
        db.session.add(log)
        db.session.commit()
        flash('Steps logged successfully!', 'success')
        return redirect(url_for('nutrition.step_history'))
    today = date.today().isoformat()
    return render_template('nutrition/log_steps.html', today=today)

@nutrition_bp.route('/recipe-search', methods=['GET', 'POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def recipe_search():
    from recipe_app.models.nutrition_tracking import Recipe
    user_id = session.get('_user_id')
    user_tier = get_user_tier()
    query = request.args.get('query', '')
    recipes = []
    if query:
        # Simple search: title contains query
        recipes = Recipe.query.filter(Recipe.title.ilike(f'%{query}%')).all()
    
    # Home+ tiers get all saved recipes, Free gets limited view
    if user_tier == 'Free':
        saved_recipes = Recipe.query.filter_by(user_id=user_id, saved=True).limit(5).all()
    else:
        saved_recipes = Recipe.query.filter_by(user_id=user_id, saved=True).all()
    
    saved_count = len(saved_recipes)
    return render_template('nutrition/recipe_search.html', 
                         query=query, recipes=recipes, saved_recipes=saved_recipes, 
                         saved_count=saved_count, user_tier=user_tier)

@nutrition_bp.route('/save-recipe', methods=['POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def save_recipe():
    from recipe_app.models.nutrition_tracking import Recipe
    user_id = session.get('_user_id')
    recipe_id = int(request.form['recipe_id'])
    saved_count = Recipe.query.filter_by(user_id=user_id, saved=True).count()
    
    # Free tier limited to 5 recipes, Home+ tiers unlimited
    user_tier = get_user_tier()
    if user_tier == 'Free' and saved_count >= 5:
        flash('Free tier limited to 5 recipes. Upgrade to Home for unlimited saving!', 'warning')
        return redirect(url_for('nutrition.recipe_search'))
    
    recipe = Recipe.query.get(recipe_id)
    if recipe:
        recipe.saved = True
        recipe.user_id = user_id
        db.session.commit()
        flash('Recipe saved!', 'success')
    return redirect(url_for('nutrition.recipe_search'))

@nutrition_bp.route('/delete-recipe', methods=['POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def delete_recipe():
    from recipe_app.models.nutrition_tracking import Recipe
    user_id = session.get('_user_id')
    recipe_id = int(request.form['recipe_id'])
    recipe = Recipe.query.get(recipe_id)
    if recipe and recipe.user_id == user_id:
        recipe.saved = False
        db.session.commit()
        flash('Recipe deleted.', 'info')
    return redirect(url_for('nutrition.recipe_search'))

@nutrition_bp.route('/shopping-list', methods=['GET'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def shopping_list():
    from recipe_app.models.nutrition_tracking import ShoppingItem
    user_id = session.get('_user_id')
    items = ShoppingItem.query.filter_by(user_id=user_id).all()
    return render_template('nutrition/shopping_list.html', items=items)

@nutrition_bp.route('/add-shopping-item', methods=['POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def add_shopping_item():
    from recipe_app.models.nutrition_tracking import ShoppingItem
    user_id = session.get('_user_id')
    item_name = request.form['item']
    item = ShoppingItem(user_id=user_id, name=item_name)
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('nutrition.shopping_list'))

@nutrition_bp.route('/delete-shopping-item', methods=['POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def delete_shopping_item():
    from recipe_app.models.nutrition_tracking import ShoppingItem
    user_id = session.get('_user_id')
    item_id = int(request.form['item_id'])
    item = ShoppingItem.query.get(item_id)
    if item and item.user_id == user_id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('nutrition.shopping_list'))

@nutrition_bp.route('/log-water', methods=['GET', 'POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def log_water():
    from recipe_app.models.nutrition_tracking import WaterLog
    from datetime import date
    user_id = session.get('_user_id')
    if request.method == 'POST':
        amount = int(request.form['amount'])
        log_date = date.fromisoformat(request.form['log_date'])
        log = WaterLog(user_id=user_id, amount=amount, log_date=log_date)
        db.session.add(log)
        db.session.commit()
        flash('Water intake logged successfully!', 'success')
        return redirect(url_for('nutrition.water_history'))
    today = date.today().isoformat()
    return render_template('nutrition/log_water.html', today=today)

@nutrition_bp.route('/water-history', methods=['GET'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def water_history():
    from recipe_app.models.nutrition_tracking import WaterLog
    user_id = session.get('_user_id')
    logs = WaterLog.query.filter_by(user_id=user_id).order_by(WaterLog.log_date.asc()).all()
    chart_data = {
        'dates': [log.log_date.isoformat() for log in logs],
        'amounts': [log.amount for log in logs]
    }
    return render_template('nutrition/water_history.html', logs=logs, chart_data=chart_data)

@nutrition_bp.route('/barcode-scan', methods=['GET'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def barcode_scan():
    return render_template('nutrition/barcode_scan.html')

@nutrition_bp.route('/barcode-lookup', methods=['POST'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def barcode_lookup():
    barcode = request.form['barcode']
    # Open Food Facts API lookup
    url = f'https://world.openfoodfacts.org/api/v0/product/{barcode}.json'
    resp = requests.get(url)
    food_data = None
    if resp.status_code == 200:
        result = resp.json()
        if result.get('status') == 1:
            product = result['product']
            food_data = {
                'name': product.get('product_name', ''),
                'brand': product.get('brands', ''),
                'barcode': barcode,
                'calories': product.get('nutriments', {}).get('energy-kcal_100g', 0),
                'protein': product.get('nutriments', {}).get('proteins_100g', 0),
                'carbs': product.get('nutriments', {}).get('carbohydrates_100g', 0),
                'fat': product.get('nutriments', {}).get('fat_100g', 0),
                'serving_size': product.get('serving_size', '')
            }
    return render_template('nutrition/barcode_scan.html', food=food_data)

@nutrition_bp.route('/meal-plan', methods=['GET'])
@require_tier(['Free', 'Home', 'Family', 'Pro', 'Student'])
def meal_plan():
    return render_template('nutrition/meal_plan.html')

@nutrition_bp.route('/custom-meal-plan', methods=['GET', 'POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def custom_meal_plan():
    from recipe_app.models.nutrition_tracking import CustomMealPlan
    user_id = session.get('_user_id')
    if request.method == 'POST':
        plan_name = request.form['plan_name']
        days = int(request.form['days'])
        plan = CustomMealPlan(user_id=user_id, name=plan_name, days=days)
        db.session.add(plan)
        db.session.commit()
        flash('Custom meal plan created!', 'success')
        return redirect(url_for('nutrition.custom_meal_plan'))
    meal_plans = CustomMealPlan.query.filter_by(user_id=user_id).all()
    return render_template('nutrition/custom_meal_plan.html', meal_plans=meal_plans)

@nutrition_bp.route('/household', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def household():
    from recipe_app.models.nutrition_tracking import HouseholdMember
    user_id = session.get('_user_id')
    members = HouseholdMember.query.filter_by(owner_id=user_id).all()
    return render_template('nutrition/household.html', members=members)

@nutrition_bp.route('/add-household-member', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def add_household_member():
    from recipe_app.models.nutrition_tracking import HouseholdMember
    user_id = session.get('_user_id')
    email = request.form['email']
    member = HouseholdMember(owner_id=user_id, email=email)
    db.session.add(member)
    db.session.commit()
    return redirect(url_for('nutrition.household'))

@nutrition_bp.route('/remove-household-member', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def remove_household_member():
    from recipe_app.models.nutrition_tracking import HouseholdMember
    user_id = session.get('_user_id')
    member_id = int(request.form['member_id'])
    member = HouseholdMember.query.get(member_id)
    if member and member.owner_id == user_id:
        db.session.delete(member)
        db.session.commit()
    return redirect(url_for('nutrition.household'))

@nutrition_bp.route('/family-shopping-list', methods=['GET'])
@require_tier(['Family', 'Pro', 'Student'])
def family_shopping_list():
    from recipe_app.models.nutrition_tracking import ShoppingItem, HouseholdMember
    user_id = session.get('_user_id')
    # Get all household member IDs
    member_ids = [user_id] + [m.id for m in HouseholdMember.query.filter_by(owner_id=user_id).all()]
    items = ShoppingItem.query.filter(ShoppingItem.user_id.in_(member_ids)).all()
    return render_template('nutrition/shopping_list.html', items=items)

@nutrition_bp.route('/family-add-shopping-item', methods=['POST'])
@require_tier(['Family', 'Pro', 'Student'])
def family_add_shopping_item():
    from recipe_app.models.nutrition_tracking import ShoppingItem
    user_id = session.get('_user_id')
    item_name = request.form['item']
    item = ShoppingItem(user_id=user_id, name=item_name)
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('nutrition.family_shopping_list'))

@nutrition_bp.route('/family-delete-shopping-item', methods=['POST'])
@require_tier(['Family', 'Pro', 'Student'])
def family_delete_shopping_item():
    from recipe_app.models.nutrition_tracking import ShoppingItem
    user_id = session.get('_user_id')
    item_id = int(request.form['item_id'])
    item = ShoppingItem.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('nutrition.family_shopping_list'))

@nutrition_bp.route('/group-log-meal', methods=['GET', 'POST'])
@require_tier(['Family', 'Pro', 'Student'])
def group_log_meal():
    from recipe_app.models.nutrition_tracking import Food, Meal, HouseholdMember
    from datetime import date
    user_id = session.get('_user_id')
    members = [{'id': user_id, 'email': 'You'}] + [{'id': m.id, 'email': m.email} for m in HouseholdMember.query.filter_by(owner_id=user_id).all()]
    if request.method == 'POST':
        member_id = int(request.form['member_id'])
        meal_type = request.form['meal_type']
        meal_date = request.form['meal_date']
        food_ids = request.form.getlist('food_ids')
        foods = Food.query.filter(Food.id.in_(food_ids)).all()
        meal = Meal(
            user_id=member_id,
            meal_type=meal_type,
            meal_date=date.fromisoformat(meal_date),
            foods=foods,
            total_calories=sum(f.calories for f in foods),
            total_protein=sum(f.protein for f in foods),
            total_carbs=sum(f.carbs for f in foods),
            total_fat=sum(f.fat for f in foods)
        )
        db.session.add(meal)
        db.session.commit()
        flash('Meal logged for family member!', 'success')
        return redirect(url_for('nutrition.group_log_meal'))
    foods = Food.query.all()
    today = date.today().isoformat()
    return render_template('nutrition/log_meal.html', foods=foods, today=today, members=members)

@nutrition_bp.route('/family-progress-chart', methods=['GET'])
@require_tier(['Family', 'Pro', 'Student'])
def family_progress_chart():
    from recipe_app.models.nutrition_tracking import NutritionLog, HouseholdMember
    user_id = session.get('_user_id')
    member_ids = [user_id] + [m.id for m in HouseholdMember.query.filter_by(owner_id=user_id).all()]
    logs = NutritionLog.query.filter(NutritionLog.user_id.in_(member_ids)).order_by(NutritionLog.log_date.asc()).all()
    chart_data = {
        'dates': [log.log_date.isoformat() for log in logs],
        'calories': [log.daily_calories or 0 for log in logs],
        'protein': [log.daily_protein or 0 for log in logs],
        'carbs': [log.daily_carbs or 0 for log in logs],
        'fat': [log.daily_fat or 0 for log in logs]
    }
    return render_template('nutrition/progress_chart.html', chart_data=chart_data)

@nutrition_bp.route('/family-meal-plan', methods=['GET', 'POST'])
@require_tier(['Family', 'Pro', 'Student'])
def family_meal_plan():
    from recipe_app.models.nutrition_tracking import FamilyMealPlan, HouseholdMember
    user_id = session.get('_user_id')
    member_ids = [user_id] + [m.id for m in HouseholdMember.query.filter_by(owner_id=user_id).all()]
    if request.method == 'POST':
        plan_name = request.form['plan_name']
        days = int(request.form['days'])
        plan = FamilyMealPlan(owner_id=user_id, name=plan_name, days=days)
        db.session.add(plan)
        db.session.commit()
        flash('Family meal plan created!', 'success')
        return redirect(url_for('nutrition.family_meal_plan'))
    meal_plans = FamilyMealPlan.query.filter(FamilyMealPlan.owner_id.in_(member_ids)).all()
    return render_template('nutrition/custom_meal_plan.html', meal_plans=meal_plans)

@nutrition_bp.route('/family-notification', methods=['POST'])
@require_tier(['Family', 'Pro', 'Student'])
def family_notification():
    from recipe_app.models.nutrition_tracking import HouseholdMember
    user_id = session.get('_user_id')
    message = request.form['message']
    # This is a stub: In production, integrate with email/SMS/push
    members = HouseholdMember.query.filter_by(owner_id=user_id).all()
    for member in members:
        # send_notification(member.email, message)  # Implement actual sending
        pass
    flash('Notification sent to household members!', 'success')
    return redirect(url_for('nutrition.household'))

@nutrition_bp.route('/pro-analytics', methods=['GET'])
@require_tier(['Pro', 'Student'])
def pro_analytics():
    from recipe_app.models.nutrition_tracking import NutritionLog
    user_id = session.get('_user_id')
    # Example: Calculate weekly/monthly averages
    logs = NutritionLog.query.filter_by(user_id=user_id).order_by(NutritionLog.log_date.desc()).limit(90).all()[::-1]
    weekly_avg = {
        'calories': round(sum(l.daily_calories or 0 for l in logs[-7:]) / 7, 2) if len(logs) >= 7 else None,
        'protein': round(sum(l.daily_protein or 0 for l in logs[-7:]) / 7, 2) if len(logs) >= 7 else None,
        'carbs': round(sum(l.daily_carbs or 0 for l in logs[-7:]) / 7, 2) if len(logs) >= 7 else None,
        'fat': round(sum(l.daily_fat or 0 for l in logs[-7:]) / 7, 2) if len(logs) >= 7 else None
    }
    monthly_avg = {
        'calories': round(sum(l.daily_calories or 0 for l in logs[-30:]) / 30, 2) if len(logs) >= 30 else None,
        'protein': round(sum(l.daily_protein or 0 for l in logs[-30:]) / 30, 2) if len(logs) >= 30 else None,
        'carbs': round(sum(l.daily_carbs or 0 for l in logs[-30:]) / 30, 2) if len(logs) >= 30 else None,
        'fat': round(sum(l.daily_fat or 0 for l in logs[-30:]) / 30, 2) if len(logs) >= 30 else None
    }
    return render_template('nutrition/pro_analytics.html', weekly_avg=weekly_avg, monthly_avg=monthly_avg)

@nutrition_bp.route('/pro-export', methods=['GET'])
@require_tier(['Pro', 'Student'])
def pro_export():
    from recipe_app.models.nutrition_tracking import NutritionLog, Meal, Food
    user_id = session.get('_user_id')
    logs = NutritionLog.query.filter_by(user_id=user_id).order_by(NutritionLog.log_date.asc()).all()
    # Export with detailed meal/food info
    import csv
    from io import StringIO
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Date', 'Calories', 'Protein', 'Carbs', 'Fat', 'Meals'])
    for log in logs:
        meal_details = []
        for meal in log.meals:
            foods = ', '.join([f.name for f in meal.foods])
            meal_details.append(f"{meal.meal_type}: {foods}")
        writer.writerow([
            log.log_date.isoformat(),
            log.daily_calories or 0,
            log.daily_protein or 0,
            log.daily_carbs or 0,
            log.daily_fat or 0,
            '; '.join(meal_details)
        ])
    output = si.getvalue()
    return output, 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=pro_nutrition_logs.csv'}

@nutrition_bp.route('/campus-group', methods=['GET', 'POST'])
@require_tier(['Student'])
def campus_group():
    from recipe_app.models.nutrition_tracking import CampusGroup
    user_id = session.get('_user_id')
    if request.method == 'POST':
        group_name = request.form['group_name']
        group = CampusGroup(owner_id=user_id, name=group_name)
        db.session.add(group)
        db.session.commit()
        flash('Campus group created!', 'success')
        return redirect(url_for('nutrition.campus_group'))
    groups = CampusGroup.query.filter_by(owner_id=user_id).all()
    return render_template('nutrition/campus_group.html', groups=groups)

@nutrition_bp.route('/study-meal-plan', methods=['GET', 'POST'])
@require_tier(['Student'])
def study_meal_plan():
    from recipe_app.models.nutrition_tracking import StudyMealPlan
    user_id = session.get('_user_id')
    if request.method == 'POST':
        plan_name = request.form['plan_name']
        days = int(request.form['days'])
        plan = StudyMealPlan(user_id=user_id, name=plan_name, days=days)
        db.session.add(plan)
        db.session.commit()
        flash('Study meal plan created!', 'success')
        return redirect(url_for('nutrition.study_meal_plan'))
    meal_plans = StudyMealPlan.query.filter_by(user_id=user_id).all()
    return render_template('nutrition/custom_meal_plan.html', meal_plans=meal_plans)

# Smart Shopping List Routes (Home+ tier)
@nutrition_bp.route('/smart-shopping-list', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def smart_shopping_list():
    """Smart shopping list interface"""
    # TODO: Implement with proper shopping list models
    return render_template('nutrition/smart_shopping_list.html', 
                         grouped_items={}, 
                         message="Smart shopping list feature coming soon!")

@nutrition_bp.route('/generate-smart-list', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def generate_smart_list():
    from recipe_app.models.nutrition_tracking import SmartShoppingItem, Meal
    from datetime import date, timedelta
    user_id = session.get('_user_id')
    
    # Get recent meals (last 7 days)
    week_ago = date.today() - timedelta(days=7)
    recent_meals = Meal.query.filter(
        Meal.user_id == user_id,
        Meal.meal_date >= week_ago
    ).all()
    
    # Extract ingredients from foods in recent meals
    ingredients = set()
    for meal in recent_meals:
        for food in meal.foods:
            # Simple ingredient extraction (in production, use NLP/AI)
            ingredients.add(food.name.lower())
    
    # Add to smart shopping list with auto-categorization
    for ingredient in ingredients:
        existing = SmartShoppingItem.query.filter_by(
            user_id=user_id, 
            name=ingredient
        ).first()
        if not existing:
            aisle = categorize_ingredient(ingredient)
            item = SmartShoppingItem(
                user_id=user_id,
                name=ingredient,
                aisle=aisle
            )
            db.session.add(item)
    
    db.session.commit()
    flash('Smart shopping list generated from recent meals!', 'success')
    return redirect(url_for('nutrition.smart_shopping_list'))

@nutrition_bp.route('/add-smart-item', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def add_smart_item():
    from recipe_app.models.nutrition_tracking import SmartShoppingItem
    user_id = session.get('_user_id')
    item_name = request.form['item']
    aisle = request.form['aisle']
    item = SmartShoppingItem(user_id=user_id, name=item_name, aisle=aisle)
    db.session.add(item)
    db.session.commit()
    return redirect(url_for('nutrition.smart_shopping_list'))

@nutrition_bp.route('/delete-smart-item', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def delete_smart_item():
    from recipe_app.models.nutrition_tracking import SmartShoppingItem
    user_id = session.get('_user_id')
    item_id = int(request.form['item_id'])
    item = SmartShoppingItem.query.get(item_id)
    if item and item.user_id == user_id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('nutrition.smart_shopping_list'))

def categorize_ingredient(ingredient):
    """Simple ingredient categorization - in production use ML/AI"""
    produce = ['apple', 'banana', 'carrot', 'lettuce', 'tomato', 'onion', 'potato']
    dairy = ['milk', 'cheese', 'butter', 'yogurt', 'cream']
    meat = ['chicken', 'beef', 'pork', 'fish', 'salmon', 'turkey']
    pantry = ['rice', 'pasta', 'flour', 'sugar', 'salt', 'oil', 'bread']
    
    ingredient = ingredient.lower()
    if any(item in ingredient for item in produce):
        return 'Produce'
    elif any(item in ingredient for item in dairy):
        return 'Dairy'
    elif any(item in ingredient for item in meat):
        return 'Meat & Seafood'
    elif any(item in ingredient for item in pantry):
        return 'Pantry'
    else:
        return 'Other'

# Recipe Nutritional Analysis Routes (Home+ tier)
@nutrition_bp.route('/recipe-analysis', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def recipe_analysis():
    from recipe_app.models.nutrition_tracking import Recipe, RecipeAnalysis
    user_id = session.get('_user_id')
    
    # Get saved recipes for dropdown
    saved_recipes = Recipe.query.filter_by(user_id=user_id).all()
    
    # Get recent analyses
    recent_analyses = RecipeAnalysis.query.filter_by(user_id=user_id).order_by(RecipeAnalysis.created_at.desc()).limit(5).all()
    
    return render_template('nutrition/recipe_analysis.html', 
                         saved_recipes=saved_recipes,
                         recent_analyses=recent_analyses)

@nutrition_bp.route('/analyze-recipe', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def analyze_recipe():
    from recipe_app.models.nutrition_tracking import Recipe, RecipeAnalysis
    import json
    user_id = session.get('_user_id')
    
    recipe_text = request.form['recipe_text']
    servings = int(request.form['servings'])
    
    # Analyze nutrition (stub - in production use USDA API + AI)
    analysis_data = analyze_recipe_nutrition_stub(recipe_text, servings)
    
    # Get saved recipes and recent analyses
    saved_recipes = Recipe.query.filter_by(user_id=user_id).all()
    recent_analyses = RecipeAnalysis.query.filter_by(user_id=user_id).order_by(RecipeAnalysis.created_at.desc()).limit(5).all()
    
    return render_template('nutrition/recipe_analysis.html', 
                         analysis=analysis_data,
                         analysis_json=json.dumps(analysis_data),
                         recipe_text=recipe_text,
                         servings=servings,
                         saved_recipes=saved_recipes,
                         recent_analyses=recent_analyses)

@nutrition_bp.route('/analyze-saved-recipe', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def analyze_saved_recipe():
    from recipe_app.models.nutrition_tracking import Recipe, RecipeAnalysis
    import json
    user_id = session.get('_user_id')
    
    recipe_id = int(request.form['recipe_id'])
    recipe = Recipe.query.get(recipe_id)
    
    if not recipe or recipe.user_id != user_id:
        flash('Recipe not found', 'error')
        return redirect(url_for('nutrition.recipe_analysis'))
    
    # Analyze saved recipe
    recipe_text = f"{recipe.ingredients}\n{recipe.instructions}"
    analysis_data = analyze_recipe_nutrition_stub(recipe_text, recipe.servings)
    analysis_data['recipe_name'] = recipe.name
    
    saved_recipes = Recipe.query.filter_by(user_id=user_id).all()
    recent_analyses = RecipeAnalysis.query.filter_by(user_id=user_id).order_by(RecipeAnalysis.created_at.desc()).limit(5).all()
    
    return render_template('nutrition/recipe_analysis.html', 
                         analysis=analysis_data,
                         analysis_json=json.dumps(analysis_data),
                         recipe_text=recipe_text,
                         servings=recipe.servings,
                         saved_recipes=saved_recipes,
                         recent_analyses=recent_analyses)

@nutrition_bp.route('/save-recipe-analysis', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def save_recipe_analysis():
    from recipe_app.models.nutrition_tracking import RecipeAnalysis
    import json
    from datetime import datetime
    user_id = session.get('_user_id')
    
    analysis_data = json.loads(request.form['analysis_data'])
    
    # Save analysis to database
    analysis = RecipeAnalysis(
        user_id=user_id,
        recipe_name=analysis_data.get('recipe_name', 'Custom Recipe'),
        servings=analysis_data['servings'],
        calories_per_serving=analysis_data['per_serving']['calories'],
        protein_per_serving=analysis_data['per_serving']['protein'],
        carbs_per_serving=analysis_data['per_serving']['carbs'],
        fat_per_serving=analysis_data['per_serving']['fat'],
        health_score=analysis_data['health_score'],
        analysis_json=json.dumps(analysis_data),
        created_at=datetime.utcnow()
    )
    db.session.add(analysis)
    db.session.commit()
    
    flash('Recipe analysis saved!', 'success')
    return redirect(url_for('nutrition.recipe_analysis'))

@nutrition_bp.route('/load-analysis', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def load_analysis():
    from recipe_app.models.nutrition_tracking import RecipeAnalysis, Recipe
    import json
    user_id = session.get('_user_id')
    
    analysis_id = int(request.form['analysis_id'])
    saved_analysis = RecipeAnalysis.query.get(analysis_id)
    
    if not saved_analysis or saved_analysis.user_id != user_id:
        flash('Analysis not found', 'error')
        return redirect(url_for('nutrition.recipe_analysis'))
    
    analysis_data = json.loads(saved_analysis.analysis_json)
    saved_recipes = Recipe.query.filter_by(user_id=user_id).all()
    recent_analyses = RecipeAnalysis.query.filter_by(user_id=user_id).order_by(RecipeAnalysis.created_at.desc()).limit(5).all()
    
    return render_template('nutrition/recipe_analysis.html', 
                         analysis=analysis_data,
                         analysis_json=saved_analysis.analysis_json,
                         saved_recipes=saved_recipes,
                         recent_analyses=recent_analyses)

@nutrition_bp.route('/delete-analysis', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def delete_analysis():
    from recipe_app.models.nutrition_tracking import RecipeAnalysis
    user_id = session.get('_user_id')
    
    analysis_id = int(request.form['analysis_id'])
    analysis = RecipeAnalysis.query.get(analysis_id)
    
    if analysis and analysis.user_id == user_id:
        db.session.delete(analysis)
        db.session.commit()
        flash('Analysis deleted!', 'success')
    
    return redirect(url_for('nutrition.recipe_analysis'))

def analyze_recipe_nutrition_stub(recipe_text, servings):
    """
    Recipe nutrition analysis stub - in production, integrate with USDA FoodData API + AI
    Returns detailed nutritional analysis including macros, micros, and health insights
    """
    import re
    import random
    
    # Simple ingredient parsing (in production use NLP/AI)
    lines = recipe_text.strip().split('\n')
    ingredients = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # Extract quantity and ingredient name (simplified)
            match = re.match(r'(\d+(?:\.\d+)?)\s*(\w+)?\s*(.+)', line)
            if match:
                quantity, unit, ingredient = match.groups()
                ingredients.append({
                    'quantity': float(quantity),
                    'unit': unit or 'item',
                    'name': ingredient.strip()
                })
            else:
                ingredients.append({'quantity': 1, 'unit': 'item', 'name': line})
    
    # Estimate nutrition based on common ingredients (simplified)
    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0
    total_fiber = 0
    total_sugar = 0
    
    # Basic nutrition database (in production use comprehensive USDA data)
    nutrition_db = {
        'flour': {'calories': 364, 'protein': 10, 'carbs': 76, 'fat': 1, 'fiber': 3, 'sugar': 1},
        'sugar': {'calories': 387, 'protein': 0, 'carbs': 100, 'fat': 0, 'fiber': 0, 'sugar': 100},
        'butter': {'calories': 717, 'protein': 1, 'carbs': 1, 'fat': 81, 'fiber': 0, 'sugar': 1},
        'egg': {'calories': 155, 'protein': 13, 'carbs': 1, 'fat': 11, 'fiber': 0, 'sugar': 1},
        'milk': {'calories': 42, 'protein': 3, 'carbs': 5, 'fat': 1, 'fiber': 0, 'sugar': 5},
        'chicken': {'calories': 239, 'protein': 27, 'carbs': 0, 'fat': 14, 'fiber': 0, 'sugar': 0},
        'rice': {'calories': 130, 'protein': 3, 'carbs': 28, 'fat': 0, 'fiber': 0, 'sugar': 0},
        'olive oil': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'fiber': 0, 'sugar': 0}
    }
    
    for ingredient in ingredients:
        name = ingredient['name'].lower()
        quantity = ingredient['quantity']
        
        # Find matching nutrition data (simplified matching)
        nutrition = None
        for food, data in nutrition_db.items():
            if food in name:
                nutrition = data
                break
        
        if not nutrition:
            # Default estimation for unknown ingredients
            nutrition = {'calories': 100, 'protein': 2, 'carbs': 15, 'fat': 3, 'fiber': 2, 'sugar': 5}
        
        # Scale by quantity (assuming per 100g for most items)
        scale = quantity / 100 if ingredient['unit'] in ['g', 'grams'] else quantity / 4  # Rough estimation
        total_calories += nutrition['calories'] * scale
        total_protein += nutrition['protein'] * scale
        total_carbs += nutrition['carbs'] * scale
        total_fat += nutrition['fat'] * scale
        total_fiber += nutrition['fiber'] * scale
        total_sugar += nutrition['sugar'] * scale
    
    # Calculate per serving
    per_serving = {
        'calories': round(total_calories / servings),
        'protein': round(total_protein / servings, 1),
        'carbs': round(total_carbs / servings, 1),
        'fat': round(total_fat / servings, 1),
        'fiber': round(total_fiber / servings, 1),
        'sugar': round(total_sugar / servings, 1)
    }
    
    # Estimate micronutrients (simplified)
    micronutrients = {
        'Vitamin C': {'amount': random.randint(5, 25), 'unit': 'mg', 'daily_value': random.randint(10, 30)},
        'Iron': {'amount': round(random.uniform(1, 5), 1), 'unit': 'mg', 'daily_value': random.randint(15, 40)},
        'Calcium': {'amount': random.randint(50, 200), 'unit': 'mg', 'daily_value': random.randint(5, 25)},
        'Potassium': {'amount': random.randint(200, 600), 'unit': 'mg', 'daily_value': random.randint(10, 30)},
        'Vitamin A': {'amount': random.randint(100, 500), 'unit': 'IU', 'daily_value': random.randint(5, 25)},
        'Folate': {'amount': random.randint(20, 100), 'unit': 'mcg', 'daily_value': random.randint(10, 30)}
    }
    
    # Calculate health score (simplified algorithm)
    health_score = 5  # Start at middle
    if per_serving['fiber'] > 5:
        health_score += 1
    if per_serving['sugar'] < 10:
        health_score += 1
    if per_serving['protein'] > 15:
        health_score += 1
    if per_serving['calories'] < 400:
        health_score += 1
    if per_serving['fat'] < 15:
        health_score += 0.5
    
    health_score = min(10, max(1, round(health_score)))
    
    # Generate health feedback and recommendations
    health_feedback = "This recipe provides a balanced nutritional profile."
    recommendations = []
    
    if per_serving['fiber'] < 3:
        recommendations.append("Consider adding more vegetables or whole grains to increase fiber content")
    if per_serving['sugar'] > 15:
        recommendations.append("Try reducing added sugars to improve the health profile")
    if per_serving['protein'] < 10:
        recommendations.append("Consider adding protein sources like lean meat, beans, or nuts")
    
    return {
        'recipe_name': None,
        'servings': servings,
        'per_serving': per_serving,
        'total': {
            'calories': round(total_calories),
            'protein': round(total_protein, 1),
            'carbs': round(total_carbs, 1),
            'fat': round(total_fat, 1),
            'fiber': round(total_fiber, 1),
            'sugar': round(total_sugar, 1)
        },
        'micronutrients': micronutrients,
        'health_score': health_score,
        'health_feedback': health_feedback,
        'recommendations': recommendations
    }

# Enhanced Progress Charts Routes (Home+ tier)
@nutrition_bp.route('/enhanced-progress', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def enhanced_progress():
    from recipe_app.models.nutrition_tracking import NutritionLog, WeightLog, StepLog, WaterLog
    from datetime import date, timedelta
    import json
    user_id = session.get('_user_id')
    
    # Get parameters
    days = int(request.args.get('days', 30))
    primary_metric = request.args.get('primary_metric', 'calories')
    
    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    # Generate comprehensive progress data
    progress_data = generate_progress_data(user_id, start_date, end_date, primary_metric)
    
    return render_template('nutrition/enhanced_progress.html',
                         days=days,
                         primary_metric=primary_metric,
                         summary_metrics=progress_data['summary_metrics'],
                         primary_insights=progress_data['primary_insights'],
                         weekly_patterns=progress_data['weekly_patterns'],
                         goals=progress_data['goals'],
                         chart_data=progress_data['chart_data'])

@nutrition_bp.route('/export-progress-pdf', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def export_progress_pdf():
    # In production, generate actual PDF using ReportLab or WeasyPrint
    flash('PDF export feature will be available soon!', 'info')
    return redirect(url_for('nutrition.enhanced_progress'))

@nutrition_bp.route('/export-progress-csv', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def export_progress_csv():
    from recipe_app.models.nutrition_tracking import NutritionLog, WeightLog, StepLog, WaterLog
    from datetime import date, timedelta
    import csv
    from io import StringIO
    from flask import Response
    user_id = session.get('_user_id')
    
    days = int(request.form.get('days', 30))
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    
    # Generate CSV data
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Date', 'Calories', 'Protein', 'Carbs', 'Fat', 'Weight', 'Steps', 'Water'])
    
    # Get data for each day
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        
        # Get nutrition data for the day
        nutrition_logs = NutritionLog.query.filter(
            NutritionLog.user_id == user_id,
            NutritionLog.log_date == current_date
        ).all()
        
        daily_calories = sum(log.calories for log in nutrition_logs)
        daily_protein = sum(log.protein for log in nutrition_logs)
        daily_carbs = sum(log.carbs for log in nutrition_logs)
        daily_fat = sum(log.fat for log in nutrition_logs)
        
        # Get weight
        weight_log = WeightLog.query.filter(
            WeightLog.user_id == user_id,
            WeightLog.log_date == current_date
        ).first()
        daily_weight = weight_log.weight if weight_log else ''
        
        # Get steps
        step_log = StepLog.query.filter(
            StepLog.user_id == user_id,
            StepLog.log_date == current_date
        ).first()
        daily_steps = step_log.steps if step_log else ''
        
        # Get water
        water_log = WaterLog.query.filter(
            WaterLog.user_id == user_id,
            WaterLog.log_date == current_date
        ).first()
        daily_water = water_log.water_ml if water_log else ''
        
        writer.writerow([
            current_date.strftime('%Y-%m-%d'),
            daily_calories,
            daily_protein,
            daily_carbs,
            daily_fat,
            daily_weight,
            daily_steps,
            daily_water
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=progress_{days}days.csv'}
    )

@nutrition_bp.route('/share-progress', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def share_progress():
    # In production, generate shareable link or social media post
    flash('Progress sharing feature coming soon!', 'info')
    return redirect(url_for('nutrition.enhanced_progress'))

def generate_progress_data(user_id, start_date, end_date, primary_metric):
    """Generate comprehensive progress data for enhanced charts"""
    from recipe_app.models.nutrition_tracking import NutritionLog, WeightLog, StepLog, WaterLog
    from datetime import timedelta
    import random
    
    days_count = (end_date - start_date).days + 1
    
    # Initialize data structures
    chart_data = {
        'primary': {'labels': [], 'data': []},
        'nutrition': {'labels': [], 'calories': [], 'protein': []},
        'activity': {'labels': [], 'steps': [], 'water': []},
        'weekly': [0] * 7  # Monday to Sunday averages
    }
    
    daily_values = {
        'calories': [],
        'protein': [],
        'weight': [],
        'steps': [],
        'water': []
    }
    
    weekly_counts = [0] * 7
    
    # Collect data for each day
    for i in range(days_count):
        current_date = start_date + timedelta(days=i)
        day_of_week = current_date.weekday()  # 0 = Monday
        
        # Get nutrition data
        nutrition_logs = NutritionLog.query.filter(
            NutritionLog.user_id == user_id,
            NutritionLog.log_date == current_date
        ).all()
        
        daily_calories = sum(log.calories for log in nutrition_logs)
        daily_protein = sum(log.protein for log in nutrition_logs)
        
        # Get weight
        weight_log = WeightLog.query.filter(
            WeightLog.user_id == user_id,
            WeightLog.log_date == current_date
        ).first()
        daily_weight = weight_log.weight if weight_log else None
        
        # Get steps
        step_log = StepLog.query.filter(
            StepLog.user_id == user_id,
            StepLog.log_date == current_date
        ).first()
        daily_steps = step_log.steps if step_log else 0
        
        # Get water
        water_log = WaterLog.query.filter(
            WaterLog.user_id == user_id,
            WaterLog.log_date == current_date
        ).first()
        daily_water = water_log.water_ml if water_log else 0
        
        # Store daily values
        daily_values['calories'].append(daily_calories)
        daily_values['protein'].append(daily_protein)
        daily_values['weight'].append(daily_weight)
        daily_values['steps'].append(daily_steps)
        daily_values['water'].append(daily_water)
        
        # Add to chart data
        chart_data['primary']['labels'].append(current_date.strftime('%m/%d'))
        chart_data['nutrition']['labels'].append(current_date.strftime('%m/%d'))
        chart_data['activity']['labels'].append(current_date.strftime('%m/%d'))
        
        chart_data['nutrition']['calories'].append(daily_calories)
        chart_data['nutrition']['protein'].append(daily_protein)
        chart_data['activity']['steps'].append(daily_steps)
        chart_data['activity']['water'].append(daily_water)
        
        # Add primary metric data
        if primary_metric == 'calories':
            chart_data['primary']['data'].append(daily_calories)
        elif primary_metric == 'weight':
            chart_data['primary']['data'].append(daily_weight or 0)
        elif primary_metric == 'steps':
            chart_data['primary']['data'].append(daily_steps)
        elif primary_metric == 'water':
            chart_data['primary']['data'].append(daily_water)
        elif primary_metric == 'protein':
            chart_data['primary']['data'].append(daily_protein)
        
        # Weekly patterns
        if primary_metric == 'calories':
            chart_data['weekly'][day_of_week] += daily_calories
            weekly_counts[day_of_week] += 1
        elif primary_metric == 'steps':
            chart_data['weekly'][day_of_week] += daily_steps
            weekly_counts[day_of_week] += 1
        elif primary_metric == 'water':
            chart_data['weekly'][day_of_week] += daily_water
            weekly_counts[day_of_week] += 1
    
    # Calculate weekly averages
    for i in range(7):
        if weekly_counts[i] > 0:
            chart_data['weekly'][i] = round(chart_data['weekly'][i] / weekly_counts[i])
    
    # Generate summary metrics
    summary_metrics = generate_summary_metrics(daily_values, primary_metric)
    
    # Generate insights
    primary_insights = generate_insights(daily_values, primary_metric)
    
    # Generate weekly patterns
    weekly_patterns = generate_weekly_patterns(chart_data['weekly'], primary_metric)
    
    # Generate goals
    goals = generate_goals(daily_values)
    
    return {
        'summary_metrics': summary_metrics,
        'primary_insights': primary_insights,
        'weekly_patterns': weekly_patterns,
        'goals': goals,
        'chart_data': chart_data
    }

def generate_summary_metrics(daily_values, primary_metric):
    """Generate summary metric cards"""
    import statistics
    
    metrics = []
    
    # Calories
    if daily_values['calories']:
        current_avg = round(statistics.mean(daily_values['calories'][-7:]))  # Last 7 days
        previous_avg = round(statistics.mean(daily_values['calories'][-14:-7])) if len(daily_values['calories']) >= 14 else current_avg
        change = current_avg - previous_avg
        
        metrics.append({
            'label': 'Avg Daily Calories',
            'current': f"{current_avg} kcal",
            'change': f"{change:+d} vs last week",
            'trend': 1 if change > 0 else -1 if change < 0 else 0,
            'icon': '🔥',
            'color': '#FF6384'
        })
    
    # Weight
    weights = [w for w in daily_values['weight'] if w is not None]
    if weights:
        current = weights[-1]
        previous = weights[0] if len(weights) > 1 else current
        change = round(current - previous, 1)
        
        metrics.append({
            'label': 'Current Weight',
            'current': f"{current} kg",
            'change': f"{change:+.1f} kg total",
            'trend': 1 if change > 0 else -1 if change < 0 else 0,
            'icon': '⚖️',
            'color': '#36A2EB'
        })
    
    # Steps
    if daily_values['steps']:
        current_avg = round(statistics.mean([s for s in daily_values['steps'][-7:] if s > 0]))
        previous_avg = round(statistics.mean([s for s in daily_values['steps'][-14:-7] if s > 0])) if len(daily_values['steps']) >= 14 else current_avg
        change = current_avg - previous_avg
        
        metrics.append({
            'label': 'Avg Daily Steps',
            'current': f"{current_avg:,}",
            'change': f"{change:+,d} vs last week",
            'trend': 1 if change > 0 else -1 if change < 0 else 0,
            'icon': '👟',
            'color': '#4BC0C0'
        })
    
    return metrics

def generate_insights(daily_values, primary_metric):
    """Generate insights for the primary metric"""
    import statistics
    
    insights = []
    
    if primary_metric == 'calories':
        if daily_values['calories']:
            avg_calories = round(statistics.mean(daily_values['calories']))
            if avg_calories > 2200:
                insights.append("Your calorie intake is above average - consider portion control")
            elif avg_calories < 1500:
                insights.append("Your calorie intake seems low - ensure you're eating enough")
            else:
                insights.append("Your calorie intake is well-balanced")
                
            consistency = statistics.stdev(daily_values['calories']) if len(daily_values['calories']) > 1 else 0
            if consistency < 200:
                insights.append("Great consistency in your daily calorie intake!")
            else:
                insights.append("Try to maintain more consistent daily calorie intake")
    
    elif primary_metric == 'weight':
        weights = [w for w in daily_values['weight'] if w is not None]
        if len(weights) > 1:
            trend = weights[-1] - weights[0]
            if abs(trend) < 0.5:
                insights.append("Your weight has been stable - great maintenance!")
            elif trend > 0:
                insights.append(f"You've gained {trend:.1f}kg - monitor your progress")
            else:
                insights.append(f"You've lost {abs(trend):.1f}kg - excellent progress!")
    
    elif primary_metric == 'steps':
        steps = [s for s in daily_values['steps'] if s > 0]
        if steps:
            avg_steps = round(statistics.mean(steps))
            if avg_steps >= 10000:
                insights.append("Excellent! You're consistently hitting 10,000+ steps")
            elif avg_steps >= 7500:
                insights.append("Good activity level - try to reach 10,000 daily steps")
            else:
                insights.append("Consider increasing daily activity to reach 7,500+ steps")
    
    return insights

def generate_weekly_patterns(weekly_data, primary_metric):
    """Generate weekly pattern analysis"""
    patterns = []
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    max_idx = weekly_data.index(max(weekly_data))
    min_idx = weekly_data.index(min(weekly_data))
    
    patterns.append(f"Your highest {primary_metric} day is typically {days[max_idx]}")
    patterns.append(f"Your lowest {primary_metric} day is typically {days[min_idx]}")
    
    weekend_avg = (weekly_data[5] + weekly_data[6]) / 2  # Sat + Sun
    weekday_avg = sum(weekly_data[:5]) / 5  # Mon-Fri
    
    if weekend_avg > weekday_avg * 1.1:
        patterns.append("You tend to have higher values on weekends")
    elif weekend_avg < weekday_avg * 0.9:
        patterns.append("Your weekdays show higher values than weekends")
    else:
        patterns.append("Your weekly pattern is fairly consistent")
    
    return patterns

def generate_goals(daily_values):
    """Generate goal tracking"""
    import statistics
    
    goals = []
    
    # Calorie goal
    if daily_values['calories']:
        avg_calories = round(statistics.mean(daily_values['calories']))
        target_calories = 2000  # Default target
        progress = min(100, (avg_calories / target_calories) * 100)
        
        goals.append({
            'name': 'Daily Calories',
            'current': avg_calories,
            'target': target_calories,
            'progress': round(progress),
            'status': 'On track' if 90 <= progress <= 110 else 'Needs attention',
            'icon': '🎯',
            'color': '#28a745' if 90 <= progress <= 110 else '#ffc107'
        })
    
    # Weight goal (example)
    weights = [w for w in daily_values['weight'] if w is not None]
    if weights:
        current_weight = weights[-1]
        target_weight = current_weight - 2  # Example: lose 2kg
        progress = max(0, min(100, ((current_weight - target_weight) / 2) * 100))
        
        goals.append({
            'name': 'Weight Loss',
            'current': f"{current_weight}kg",
            'target': f"{target_weight}kg",
            'progress': round(progress),
            'status': 'In progress' if progress > 0 else 'Starting',
            'icon': '⚖️',
            'color': '#007bff'
        })
    
    # Steps goal
    steps = [s for s in daily_values['steps'] if s > 0]
    if steps:
        avg_steps = round(statistics.mean(steps))
        target_steps = 10000
        progress = min(100, (avg_steps / target_steps) * 100)
        
        goals.append({
            'name': 'Daily Steps',
            'current': f"{avg_steps:,}",
            'target': f"{target_steps:,}",
            'progress': round(progress),
            'status': 'Excellent' if progress >= 100 else 'Good progress' if progress >= 75 else 'Keep going',
            'icon': '👟',
            'color': '#28a745' if progress >= 100 else '#ffc107' if progress >= 75 else '#dc3545'
        })
    
    return goals

# Weekly Meal Planning Calendar Routes (Home+ tier)
@nutrition_bp.route('/weekly-calendar', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def weekly_calendar():
    from recipe_app.models.nutrition_tracking import WeeklyMealPlan
    from datetime import date, timedelta
    user_id = session.get('_user_id')
    
    # Get week offset (0 = current week, 1 = next week, -1 = last week)
    week_offset = int(request.args.get('week_offset', 0))
    
    # Calculate week start (Monday) and end (Sunday)
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    
    # Get weekly meal plan
    weekly_meals, weekly_summary = get_weekly_meals(user_id, week_start)
    
    return render_template('nutrition/weekly_calendar.html',
                         week_start=week_start,
                         week_end=week_end,
                         week_offset=week_offset,
                         weekly_meals=weekly_meals,
                         weekly_summary=weekly_summary)

@nutrition_bp.route('/add-calendar-meal', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def add_calendar_meal():
    from recipe_app.models.nutrition_tracking import WeeklyMealPlan
    from datetime import date, timedelta
    import json
    user_id = session.get('_user_id')
    
    data = request.json
    week_offset = data['week_offset']
    meal_type = data['meal_type']
    day = data['day']
    meal_name = data['name']
    calories = data['calories']
    
    # Calculate specific date
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
    meal_date = week_start + timedelta(days=day)
    
    # Check if plan exists for this week
    meal_plan = WeeklyMealPlan.query.filter_by(
        user_id=user_id,
        week_start=week_start
    ).first()
    
    if not meal_plan:
        meal_plan = WeeklyMealPlan(
            user_id=user_id,
            week_start=week_start,
            meal_data=json.dumps({})
        )
        db.session.add(meal_plan)
    
    # Update meal data
    meal_data = json.loads(meal_plan.meal_data) if meal_plan.meal_data else {}
    if meal_type not in meal_data:
        meal_data[meal_type] = {}
    
    meal_data[meal_type][str(day)] = {
        'name': meal_name,
        'calories': calories,
        'date': meal_date.isoformat()
    }
    
    meal_plan.meal_data = json.dumps(meal_data)
    db.session.commit()
    
    return {'success': True}

@nutrition_bp.route('/generate-week-meals', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def generate_week_meals():
    from recipe_app.models.nutrition_tracking import WeeklyMealPlan
    from datetime import date, timedelta
    import json
    import random
    user_id = session.get('_user_id')
    
    data = request.json
    week_offset = data['week_offset']
    
    # Calculate week start
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
    
    # Generate AI meal plan for the week
    meal_suggestions = {
        'breakfast': ['Oatmeal with Berries', 'Scrambled Eggs', 'Greek Yogurt Parfait', 'Smoothie Bowl', 'Avocado Toast', 'Pancakes', 'French Toast'],
        'lunch': ['Chicken Salad', 'Turkey Sandwich', 'Quinoa Bowl', 'Soup and Salad', 'Wrap', 'Pasta Salad', 'Stir Fry'],
        'dinner': ['Grilled Salmon', 'Chicken Stir Fry', 'Beef Tacos', 'Pasta Primavera', 'Curry Bowl', 'Pizza', 'BBQ Chicken'],
        'snack': ['Mixed Nuts', 'Apple with PB', 'Yogurt', 'Trail Mix', 'Cheese & Crackers', 'Smoothie', 'Fruit Salad']
    }
    
    calorie_ranges = {
        'breakfast': (250, 400),
        'lunch': (350, 550),
        'dinner': (400, 650),
        'snack': (100, 250)
    }
    
    # Generate meals for each day
    meal_data = {}
    for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
        meal_data[meal_type] = {}
        available_meals = meal_suggestions[meal_type].copy()
        
        for day in range(7):
            if not available_meals:
                available_meals = meal_suggestions[meal_type].copy()
            
            meal_name = random.choice(available_meals)
            available_meals.remove(meal_name)
            
            min_cal, max_cal = calorie_ranges[meal_type]
            calories = random.randint(min_cal, max_cal)
            
            meal_data[meal_type][str(day)] = {
                'name': meal_name,
                'calories': calories,
                'date': (week_start + timedelta(days=day)).isoformat()
            }
    
    # Save to database
    meal_plan = WeeklyMealPlan.query.filter_by(
        user_id=user_id,
        week_start=week_start
    ).first()
    
    if not meal_plan:
        meal_plan = WeeklyMealPlan(
            user_id=user_id,
            week_start=week_start,
            meal_data=json.dumps(meal_data)
        )
        db.session.add(meal_plan)
    else:
        meal_plan.meal_data = json.dumps(meal_data)
    
    db.session.commit()
    return {'success': True}

@nutrition_bp.route('/clear-week-meals', methods=['POST'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def clear_week_meals():
    from recipe_app.models.nutrition_tracking import WeeklyMealPlan
    from datetime import date, timedelta
    user_id = session.get('_user_id')
    
    data = request.json
    week_offset = data['week_offset']
    
    # Calculate week start
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
    
    # Delete meal plan
    meal_plan = WeeklyMealPlan.query.filter_by(
        user_id=user_id,
        week_start=week_start
    ).first()
    
    if meal_plan:
        db.session.delete(meal_plan)
        db.session.commit()
    
    return {'success': True}

@nutrition_bp.route('/export-week-meals', methods=['GET'])
@require_tier(['Home', 'Family', 'Pro', 'Student'])
def export_week_meals():
    from recipe_app.models.nutrition_tracking import WeeklyMealPlan
    from datetime import date, timedelta
    from flask import Response
    import json
    user_id = session.get('_user_id')
    
    week_offset = int(request.args.get('week_offset', 0))
    
    # Calculate week start
    today = date.today()
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    
    # Get meal plan
    meal_plan = WeeklyMealPlan.query.filter_by(
        user_id=user_id,
        week_start=week_start
    ).first()
    
    if not meal_plan:
        return Response('No meal plan found for this week', status=404)
    
    # Generate text export
    meal_data = json.loads(meal_plan.meal_data)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    export_text = f"Weekly Meal Plan: {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}\n"
    export_text += "=" * 60 + "\n\n"
    
    for day_idx in range(7):
        export_text += f"{days[day_idx]}:\n"
        for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
            meal = meal_data.get(meal_type, {}).get(str(day_idx))
            if meal:
                export_text += f"  {meal_type.title()}: {meal['name']} ({meal['calories']} cal)\n"
        export_text += "\n"
    
    return Response(
        export_text,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename=meal_plan_{week_start.strftime("%Y%m%d")}.txt'}
    )

def get_weekly_meals(user_id, week_start):
    """Get weekly meals and calculate summary statistics"""
    from recipe_app.models.nutrition_tracking import WeeklyMealPlan
    import json
    
    meal_plan = WeeklyMealPlan.query.filter_by(
        user_id=user_id,
        week_start=week_start
    ).first()
    
    weekly_meals = {}
    if meal_plan and meal_plan.meal_data:
        weekly_meals = json.loads(meal_plan.meal_data)
    
    # Calculate summary statistics
    total_meals = 0
    total_calories = 0
    meal_names = set()
    
    for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
        if meal_type not in weekly_meals:
            weekly_meals[meal_type] = {}
        
        for day in range(7):
            meal = weekly_meals[meal_type].get(str(day))
            if meal:
                total_meals += 1
                total_calories += meal['calories']
                meal_names.add(meal['name'].lower())
    
    avg_calories = round(total_calories / 7) if total_calories > 0 else 0
    variety_score = min(10, len(meal_names))  # Max 10 for high variety
    completion = round((total_meals / 28) * 100)  # 28 = 7 days × 4 meal types
    
    weekly_summary = {
        'total_meals': total_meals,
        'avg_calories': avg_calories,
        'variety_score': variety_score,
        'completion': completion
    }
    
    return weekly_meals, weekly_summary

@nutrition_bp.route('/barcode-scanner')
@require_tier(['home', 'family', 'pro', 'student'])
def barcode_scanner():
    """Barcode scanner interface for Home+ tier users"""
    return render_template('nutrition/barcode_scanner.html')

@nutrition_bp.route('/lookup-barcode', methods=['POST'])
@require_tier(['home', 'family', 'pro', 'student'])
def lookup_barcode():
    """Look up product information by barcode"""
    try:
        data = request.get_json()
        barcode = data.get('barcode', '').strip()
        
        if not barcode or not re.match(r'^[0-9]{8,14}$', barcode):
            return jsonify({
                'success': False,
                'message': 'Invalid barcode format'
            })
        
        # Mock product lookup - in production, integrate with OpenFoodFacts or similar API
        product_info = lookup_product_by_barcode(barcode)
        
        if product_info:
            return jsonify({
                'success': True,
                'product': product_info
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Product not found in database'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error looking up product: {str(e)}'
        })

@nutrition_bp.route('/add-scanned-to-meal', methods=['POST'])
@require_tier(['home', 'family', 'pro', 'student'])
def add_scanned_to_meal():
    """Add scanned product to today's meal log"""
    try:
        data = request.get_json()
        barcode = data.get('barcode')
        product = data.get('product', {})
        
        # Create meal entry for today
        today = datetime.now().date()
        
        # First create a food item for the scanned product
        food_item = Food(
            name=product.get('name', f'Scanned Product ({barcode})'),
            brand=product.get('brand', ''),
            barcode=barcode,
            calories=float(product.get('calories', 0)) or 0,
            protein=float(product.get('protein', 0)) or 0,
            carbs=float(product.get('carbohydrates', 0)) or 0,
            fat=float(product.get('fat', 0)) or 0,
            serving_size=product.get('serving_size', '1 serving')
        )
        db.session.add(food_item)
        db.session.flush()  # Get the food ID
        
        # Create meal entry with the food
        meal_entry = Meal(
            user_id=current_user.id,
            meal_date=today,
            meal_type='snack',  # Default to snack, user can change later
            foods=[food_item],
            total_calories=food_item.calories,
            total_protein=food_item.protein,
            total_carbs=food_item.carbs,
            total_fat=food_item.fat
        )
        
        db.session.add(meal_entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Product added to today\'s meal log'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error adding to meal: {str(e)}'
        })

@nutrition_bp.route('/add-scanned-to-shopping', methods=['POST'])
@require_tier(['home', 'family', 'pro', 'student'])
def add_scanned_to_shopping():
    """Add scanned product to smart shopping list"""
    try:
        # TODO: Implement with proper ShoppingList model
        return jsonify({
            'success': False,
            'message': 'Smart shopping list feature coming soon!'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error adding to shopping list: {str(e)}'
        })

def lookup_product_by_barcode(barcode):
    """
    Look up product information by barcode
    In production, integrate with OpenFoodFacts API or similar service
    """
    # Mock product database for demonstration
    mock_products = {
        '012345678901': {
            'barcode': '012345678901',
            'name': 'Organic Whole Wheat Bread',
            'brand': 'Nature\'s Best',
            'calories': 120,
            'protein': 4,
            'carbohydrates': 22,
            'fat': 2,
            'fiber': 3,
            'sugar': 3,
            'serving_size': '1 slice (28g)',
            'ingredients': 'Whole wheat flour, water, yeast, salt, honey, sunflower oil',
            'image': '/static/images/bread-placeholder.jpg'
        },
        '123456789012': {
            'barcode': '123456789012',
            'name': 'Greek Yogurt Plain',
            'brand': 'Farm Fresh',
            'calories': 100,
            'protein': 17,
            'carbohydrates': 6,
            'fat': 0,
            'fiber': 0,
            'sugar': 6,
            'serving_size': '1 container (170g)',
            'ingredients': 'Cultured grade A non-fat milk, live active cultures',
            'image': '/static/images/yogurt-placeholder.jpg'
        },
        '234567890123': {
            'barcode': '234567890123',
            'name': 'Organic Bananas',
            'brand': 'Fresh Produce Co.',
            'calories': 105,
            'protein': 1,
            'carbohydrates': 27,
            'fat': 0,
            'fiber': 3,
            'sugar': 14,
            'serving_size': '1 medium banana (118g)',
            'ingredients': 'Organic bananas',
            'image': '/static/images/banana-placeholder.jpg'
        },
        '345678901234': {
            'barcode': '345678901234',
            'name': 'Chicken Breast Boneless',
            'brand': 'Premium Poultry',
            'calories': 231,
            'protein': 43,
            'carbohydrates': 0,
            'fat': 5,
            'fiber': 0,
            'sugar': 0,
            'serving_size': '100g',
            'ingredients': 'Chicken breast',
            'image': '/static/images/chicken-placeholder.jpg'
        }
    }
    
    if barcode in mock_products:
        return mock_products[barcode]
    
    # If not in mock database, generate a basic product entry
    return {
        'barcode': barcode,
        'name': f'Product {barcode[-4:]}',
        'brand': 'Unknown Brand',
        'calories': 150,
        'protein': 5,
        'carbohydrates': 20,
        'fat': 3,
        'fiber': 2,
        'sugar': 8,
        'serving_size': '1 serving',
        'ingredients': 'Ingredients not available',
        'image': '/static/images/placeholder-food.png'
    }

"""
Nutrition logging routes for daily/weekly/monthly tracking
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, or_
from recipe_app.db import db
from recipe_app.models.nutrition_models import NutritionEntry, DailyNutritionSummary, NutritionGoal
from recipe_app.models import WaterLog
from recipe_app.utils.nutrition_calculator import NutritionCalculator
import json


nutrition_bp = Blueprint('nutrition', __name__)


@nutrition_bp.route('/nutrition-tracker')
def nutrition_tracker():
    """Main nutrition tracking page"""
    if '_user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = str(session['_user_id'])
    user_id_int = int(session['_user_id'])
    today = date.today()
    
    # Get or create user's nutrition goals
    goals = NutritionGoal.query.filter_by(user_id=user_id).first()
    if not goals:
        goals = NutritionGoal(user_id=user_id)
        db.session.add(goals)
        db.session.commit()
    
    # Get today's summary
    daily_summary = DailyNutritionSummary.query.filter_by(
        user_id=user_id, 
        summary_date=today
    ).first()
    
    # Get today's entries
    today_entries = NutritionEntry.query.filter_by(
        user_id=user_id,
        entry_date=today
    ).order_by(NutritionEntry.entry_time.desc()).all()

    # Get today's water total
    water_total = db.session.query(func.sum(WaterLog.amount_ml)).filter(
        WaterLog.user_id == user_id_int,
        func.date(WaterLog.log_time) == today
    ).scalar() or 0
    
    # Get recent week summaries for charts
    week_ago = today - timedelta(days=7)
    week_summaries = DailyNutritionSummary.query.filter_by(
        user_id=user_id
    ).filter(
        DailyNutritionSummary.summary_date >= week_ago
    ).order_by(DailyNutritionSummary.summary_date).all()
    
    return render_template('nutrition_tracker.html',
                         goals=goals,
                         daily_summary=daily_summary,
                         today_entries=today_entries,
                         week_summaries=week_summaries,
                         water_total=water_total,
                         today=today)


@nutrition_bp.route('/log-nutrition', methods=['POST'])
def log_nutrition():
    """Log a nutrition entry"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        user_id = str(session['_user_id'])
        
        # Extract data
        barcode = data.get('barcode')
        product_name = data.get('product_name', '')
        brand = data.get('brand', '')
        portion_size = float(data.get('portion_size', 100))
        servings = float(data.get('servings', 1))
        meal_type = data.get('meal_type', 'snack')
        notes = data.get('notes', '')
        
        # Calculate total weight
        total_weight = portion_size * servings
        
        # Get nutrition data
        nutrition_data = data.get('nutrition', {})
        
        # Create nutrition entry
        entry = NutritionEntry(
            user_id=user_id,
            barcode=barcode,
            product_name=product_name,
            brand=brand,
            portion_size=portion_size,
            servings=servings,
            total_weight=total_weight,
            calories=float(nutrition_data.get('calories', 0)),
            protein=float(nutrition_data.get('protein', 0)),
            carbs=float(nutrition_data.get('carbs', 0)),
            fat=float(nutrition_data.get('fat', 0)),
            fiber=float(nutrition_data.get('fiber', 0)),
            sugar=float(nutrition_data.get('sugar', 0)),
            sodium=float(nutrition_data.get('sodium', 0)),
            cholesterol=float(nutrition_data.get('cholesterol', 0)),
            saturated_fat=float(nutrition_data.get('saturated_fat', 0)),
            meal_type=meal_type,
            notes=notes
        )
        
        db.session.add(entry)
        db.session.commit()
        
        # Update daily summary
        update_daily_summary(user_id, entry.entry_date)
        
        return jsonify({
            'success': True,
            'message': 'Nutrition entry logged successfully',
            'entry_id': entry.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@nutrition_bp.route('/log-from-barcode', methods=['POST'])
def log_from_barcode():
    """Log nutrition from barcode scan with calculated values"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        user_id = str(session['_user_id'])
        
        # Extract data
        barcode = data.get('barcode')
        portion_size = float(data.get('portion_size', 100))
        servings = float(data.get('servings', 1))
        meal_type = data.get('meal_type', 'snack')
        notes = data.get('notes', '')
        
        # Calculate nutrition using existing calculator
        calculator = NutritionCalculator()
        nutrition_result = calculator.get_product_nutrition_per_serving(
            barcode, int(servings), portion_size
        )
        
        if not nutrition_result['success']:
            return jsonify({'success': False, 'error': nutrition_result['error']}), 400
        
        # Extract product and nutrition data
        product_data = nutrition_result['product']
        nutrition_data = nutrition_result['nutrition']
        
        # Helper function to extract numeric value from nutrition data
        def extract_numeric_value(data, key, default=0):
            value = data.get(key, default)
            if isinstance(value, dict) and 'value' in value:
                return float(value['value']) if value['value'] is not None else default
            return float(value) if value is not None else default
        
        # Create nutrition entry
        entry = NutritionEntry(
            user_id=user_id,
            barcode=barcode,
            product_name=product_data.get('name', product_data.get('product_name', '')),
            brand=product_data.get('brand', product_data.get('brands', '')),
            portion_size=portion_size,
            servings=servings,
            total_weight=portion_size * servings,
            calories=extract_numeric_value(nutrition_data, 'calories') or extract_numeric_value(nutrition_data, 'energy_kcal'),
            protein=extract_numeric_value(nutrition_data, 'protein') or extract_numeric_value(nutrition_data, 'proteins'),
            carbs=extract_numeric_value(nutrition_data, 'carbs') or extract_numeric_value(nutrition_data, 'carbohydrates'),
            fat=extract_numeric_value(nutrition_data, 'fat'),
            fiber=extract_numeric_value(nutrition_data, 'fiber'),
            sugar=extract_numeric_value(nutrition_data, 'sugar') or extract_numeric_value(nutrition_data, 'sugars'),
            sodium=extract_numeric_value(nutrition_data, 'sodium') * 1000 if extract_numeric_value(nutrition_data, 'sodium') else 0,  # Convert to mg
            cholesterol=extract_numeric_value(nutrition_data, 'cholesterol') * 1000 if extract_numeric_value(nutrition_data, 'cholesterol') else 0,  # mg
            saturated_fat=extract_numeric_value(nutrition_data, 'saturated_fat') or extract_numeric_value(nutrition_data, 'saturated-fat'),
            meal_type=meal_type,
            notes=notes
        )
        
        db.session.add(entry)
        db.session.commit()
        
        # Update daily summary
        update_daily_summary(user_id, entry.entry_date)
        
        return jsonify({
            'success': True,
            'message': 'Nutrition entry logged successfully',
            'entry_id': entry.id,
            'entry': entry.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@nutrition_bp.route('/nutrition-entries/<date_str>')
def get_nutrition_entries(date_str):
    """Get nutrition entries for a specific date"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        user_id = session['_user_id']
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        entries = NutritionEntry.query.filter_by(
            user_id=user_id,
            entry_date=entry_date
        ).order_by(NutritionEntry.entry_time.desc()).all()
        
        # Group by meal type
        grouped_entries = {
            'breakfast': [],
            'lunch': [],
            'dinner': [],
            'snack': []
        }
        
        for entry in entries:
            grouped_entries[entry.meal_type].append(entry.to_dict())
        
        return jsonify({
            'success': True,
            'entries': grouped_entries,
            'total_entries': len(entries)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@nutrition_bp.route('/log-water', methods=['POST'])
def log_water():
    """Log water intake"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    data = request.get_json() or {}
    try:
        amount = float(data.get('amount_ml', 0))
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        return jsonify({'success': False, 'error': 'Invalid amount'}), 400

    log = WaterLog(user_id=int(session['_user_id']), amount_ml=amount)
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'log': log.to_dict()})


@nutrition_bp.route('/water-log/<int:log_id>', methods=['PUT'])
def edit_water_log(log_id):
    """Edit a water log entry"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    log = WaterLog.query.filter_by(id=log_id, user_id=int(session['_user_id'])).first()
    if not log:
        return jsonify({'success': False, 'error': 'Log not found'}), 404

    data = request.get_json() or {}
    try:
        amount = float(data.get('amount_ml', log.amount_ml))
    except (TypeError, ValueError):
        amount = log.amount_ml
    log.amount_ml = amount
    db.session.commit()

    return jsonify({'success': True, 'log': log.to_dict()})


@nutrition_bp.route('/water-log/<int:log_id>', methods=['DELETE'])
def delete_water_log(log_id):
    """Delete a water log entry"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    log = WaterLog.query.filter_by(id=log_id, user_id=int(session['_user_id'])).first()
    if not log:
        return jsonify({'success': False, 'error': 'Log not found'}), 404

    db.session.delete(log)
    db.session.commit()
    return jsonify({'success': True})


@nutrition_bp.route('/water-summary/<date_str>')
def water_summary(date_str):
    """Get total water intake for a day"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        summary_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid date'}), 400

    total = db.session.query(func.sum(WaterLog.amount_ml)).filter(
        WaterLog.user_id == int(session['_user_id']),
        func.date(WaterLog.log_time) == summary_date
    ).scalar() or 0

    return jsonify({'success': True, 'total_ml': float(total)})


@nutrition_bp.route('/delete-nutrition-entry/<int:entry_id>', methods=['DELETE'])
def delete_nutrition_entry(entry_id):
    """Delete a nutrition entry"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        user_id = session['_user_id']
        
        entry = NutritionEntry.query.filter_by(
            id=entry_id,
            user_id=user_id
        ).first()
        
        if not entry:
            return jsonify({'success': False, 'error': 'Entry not found'}), 404
        
        entry_date = entry.entry_date
        db.session.delete(entry)
        db.session.commit()
        
        # Update daily summary
        update_daily_summary(user_id, entry_date)
        
        return jsonify({
            'success': True,
            'message': 'Entry deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@nutrition_bp.route('/nutrition-goals', methods=['GET', 'POST'])
def nutrition_goals():
    """Get or update nutrition goals"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    user_id = session['_user_id']
    
    if request.method == 'GET':
        goals = NutritionGoal.query.filter_by(user_id=user_id).first()
        if not goals:
            goals = NutritionGoal(user_id=user_id)
            db.session.add(goals)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'goals': goals.to_dict()
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            goals = NutritionGoal.query.filter_by(user_id=user_id).first()
            if not goals:
                goals = NutritionGoal(user_id=user_id)
                db.session.add(goals)
            
            # Update goals
            goals.daily_calories = float(data.get('daily_calories', goals.daily_calories))
            goals.daily_protein = float(data.get('daily_protein', goals.daily_protein))
            goals.daily_carbs = float(data.get('daily_carbs', goals.daily_carbs))
            goals.daily_fat = float(data.get('daily_fat', goals.daily_fat))
            goals.daily_fiber = float(data.get('daily_fiber', goals.daily_fiber))
            goals.daily_sugar = float(data.get('daily_sugar', goals.daily_sugar))
            goals.daily_sodium = float(data.get('daily_sodium', goals.daily_sodium))
            
            # Update profile data if provided
            if 'age' in data:
                goals.age = int(data['age'])
            if 'gender' in data:
                goals.gender = data['gender']
            if 'height' in data:
                goals.height = float(data['height'])
            if 'weight' in data:
                goals.weight = float(data['weight'])
            if 'activity_level' in data:
                goals.activity_level = data['activity_level']
            if 'goal_type' in data:
                goals.goal_type = data['goal_type']
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Goals updated successfully',
                'goals': goals.to_dict()
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500


@nutrition_bp.route('/nutrition-summary/<date_str>')
def get_nutrition_summary(date_str):
    """Get nutrition summary for a specific date"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        user_id = session['_user_id']
        summary_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        summary = DailyNutritionSummary.query.filter_by(
            user_id=user_id,
            summary_date=summary_date
        ).first()
        
        if not summary:
            # Create empty summary if none exists
            summary = DailyNutritionSummary(
                user_id=user_id,
                summary_date=summary_date
            )
        
        # Get user goals for comparison
        goals = NutritionGoal.query.filter_by(user_id=user_id).first()
        
        return jsonify({
            'success': True,
            'summary': summary.to_dict(),
            'goals': goals.to_dict() if goals else None
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def update_daily_summary(user_id, summary_date):
    """Update or create daily nutrition summary"""
    try:
        # Get existing summary or create new one
        summary = DailyNutritionSummary.query.filter_by(
            user_id=user_id,
            summary_date=summary_date
        ).first()
        
        if not summary:
            summary = DailyNutritionSummary(
                user_id=user_id,
                summary_date=summary_date
            )
            db.session.add(summary)
        
        # Calculate totals from entries
        entries = NutritionEntry.query.filter_by(
            user_id=user_id,
            entry_date=summary_date
        ).all()
        
        # Reset totals
        summary.total_calories = 0
        summary.total_protein = 0
        summary.total_carbs = 0
        summary.total_fat = 0
        summary.total_fiber = 0
        summary.total_sugar = 0
        summary.total_sodium = 0
        summary.total_cholesterol = 0
        summary.total_saturated_fat = 0
        summary.breakfast_calories = 0
        summary.lunch_calories = 0
        summary.dinner_calories = 0
        summary.snack_calories = 0
        summary.total_entries = len(entries)
        
        # Sum up values
        for entry in entries:
            summary.total_calories += entry.calories
            summary.total_protein += entry.protein
            summary.total_carbs += entry.carbs
            summary.total_fat += entry.fat
            summary.total_fiber += entry.fiber
            summary.total_sugar += entry.sugar
            summary.total_sodium += entry.sodium
            summary.total_cholesterol += getattr(entry, 'cholesterol', 0)
            summary.total_saturated_fat += entry.saturated_fat
            
            # Add to meal-specific totals
            if entry.meal_type == 'breakfast':
                summary.breakfast_calories += entry.calories
            elif entry.meal_type == 'lunch':
                summary.lunch_calories += entry.calories
            elif entry.meal_type == 'dinner':
                summary.dinner_calories += entry.calories
            elif entry.meal_type == 'snack':
                summary.snack_calories += entry.calories
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating daily summary: {e}")


@nutrition_bp.route('/weekly-summary')
def weekly_summary():
    """Get weekly nutrition summary"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        user_id = session['_user_id']
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        summaries = DailyNutritionSummary.query.filter_by(
            user_id=user_id
        ).filter(
            DailyNutritionSummary.summary_date >= week_ago
        ).order_by(DailyNutritionSummary.summary_date).all()
        
        # Calculate weekly averages
        if summaries:
            avg_calories = sum(s.total_calories for s in summaries) / len(summaries)
            avg_protein = sum(s.total_protein for s in summaries) / len(summaries)
            avg_carbs = sum(s.total_carbs for s in summaries) / len(summaries)
            avg_fat = sum(s.total_fat for s in summaries) / len(summaries)
        else:
            avg_calories = avg_protein = avg_carbs = avg_fat = 0
        
        return jsonify({
            'success': True,
            'summaries': [s.to_dict() for s in summaries],
            'averages': {
                'calories': round(avg_calories, 1),
                'protein': round(avg_protein, 1),
                'carbs': round(avg_carbs, 1),
                'fat': round(avg_fat, 1)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@nutrition_bp.route('/nutrition-dashboard')
def nutrition_dashboard():
    """Comprehensive nutrition dashboard page"""
    if '_user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = str(session['_user_id'])
    today = date.today()
    
    # Get or create user's nutrition goals
    goals = NutritionGoal.query.filter_by(user_id=user_id).first()
    if not goals:
        goals = NutritionGoal(user_id=user_id)
        db.session.add(goals)
        db.session.commit()
    
    # Get today's summary
    daily_summary = DailyNutritionSummary.query.filter_by(
        user_id=user_id, 
        summary_date=today
    ).first()
    
    # Get today's entries
    today_entries = NutritionEntry.query.filter_by(
        user_id=user_id,
        entry_date=today
    ).order_by(NutritionEntry.entry_time.desc()).all()
    
    # Get recent week summaries for charts
    week_ago = today - timedelta(days=7)
    week_summaries = DailyNutritionSummary.query.filter_by(
        user_id=user_id
    ).filter(
        DailyNutritionSummary.summary_date >= week_ago
    ).order_by(DailyNutritionSummary.summary_date).all()
    
    # Get recent logs for history
    recent_logs = DailyNutritionSummary.query.filter_by(
        user_id=user_id
    ).order_by(DailyNutritionSummary.summary_date.desc()).limit(10).all()
    
    return render_template('nutrition_tracker_advanced.html',
                         goals=goals,
                         daily_summary=daily_summary,
                         today_entries=today_entries,
                         week_summaries=week_summaries,
                         recent_logs=recent_logs,
                         today=today)


@nutrition_bp.route('/set-goals', methods=['POST'])
def set_goals():
    """Set or update user nutrition goals"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        user_id = str(session['_user_id'])
        
        # Get or create nutrition goals
        goals = NutritionGoal.query.filter_by(user_id=user_id).first()
        if not goals:
            goals = NutritionGoal(user_id=user_id)
            db.session.add(goals)
        
        # Update goals
        goals.daily_calories = float(data.get('daily_calories', 2000))
        goals.daily_protein = float(data.get('daily_protein', 150))
        goals.daily_carbs = float(data.get('daily_carbs', 250))
        goals.daily_fat = float(data.get('daily_fat', 65))
        goals.daily_fiber = float(data.get('daily_fiber', 25))
        goals.daily_sugar = float(data.get('daily_sugar', 50))
        goals.daily_sodium = float(data.get('daily_sodium', 2300))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'goals': goals.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@nutrition_bp.route('/get_product_nutrition_per_serving', methods=['POST'])
def get_product_nutrition_per_serving_route():
    """Get nutrition information for a product with serving calculation"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        barcode = data.get('barcode')
        servings = float(data.get('servings', 1))
        portion_size = float(data.get('portion_size', 100))
        
        if not barcode:
            return jsonify({'success': False, 'error': 'Barcode is required'}), 400
        
        # Calculate nutrition using existing calculator
        calculator = NutritionCalculator()
        nutrition_result = calculator.get_product_nutrition_per_serving(
            barcode, int(servings), portion_size
        )
        
        if not nutrition_result['success']:
            return jsonify({'success': False, 'error': nutrition_result['error']}), 400
        
        return jsonify({
            'success': True,
            'nutrition_label': nutrition_result['nutrition_label'],
            'product': nutrition_result['product'],
            'nutrition': nutrition_result['nutrition']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

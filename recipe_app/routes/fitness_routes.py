# --- API endpoint: Get user's latest weight (for calorie calculation) ---

"""
Routes for tracking weight and fitness activities.
"""
from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from datetime import datetime, date
from recipe_app.db import db
from recipe_app.models import WeightLog, WorkoutLog, ExerciseLog
from recipe_app.models.models import WeightGoal

from flask_wtf.csrf import validate_csrf, ValidationError
import math

fitness_bp = Blueprint('fitness', __name__)



# --- API endpoint: Save weight goal (POST) and get weight goal (GET) ---
@fitness_bp.route('/api/weight-goal', methods=['GET', 'POST'])
def api_weight_goal():
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    user_id = session['_user_id']
    if request.method == 'GET':
        goal = WeightGoal.query.filter_by(user_id=user_id).first()
        if goal:
            return jsonify({'success': True, 'goal': goal.to_dict()})
        else:
            return jsonify({'success': True, 'goal': None})
    elif request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Missing JSON data'}), 400
        try:
            current_weight = float(data.get('current_weight'))
            target_weight = float(data.get('target_weight'))
            time_frame_weeks = int(data.get('time_frame_weeks'))
            weight_unit = data.get('weight_unit', 'kg')
        except Exception:
            return jsonify({'success': False, 'error': 'Invalid data'}), 400
        goal = WeightGoal.query.filter_by(user_id=user_id).first()
        if not goal:
            goal = WeightGoal(user_id=user_id, current_weight=current_weight, target_weight=target_weight, time_frame_weeks=time_frame_weeks, weight_unit=weight_unit)
            db.session.add(goal)
        else:
            goal.current_weight = current_weight
            goal.target_weight = target_weight
            goal.time_frame_weeks = time_frame_weeks
            goal.weight_unit = weight_unit
            goal.date_set = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'goal': goal.to_dict()})
@fitness_bp.route('/test')
def test():
    """Test route to verify fitness blueprint is working"""
    return "Fitness routes are working!"

def calculate_bmi(weight_kg, height_cm):
    """Calculate BMI given weight in kg and height in cm"""
    height_m = height_cm / 100
    return weight_kg / (height_m * height_m)

def get_bmi_category(bmi):
    """Get BMI category based on BMI value"""
    if bmi < 18.5:
        return "Underweight", "text-info"
    elif 18.5 <= bmi < 25:
        return "Normal weight", "text-success"
    elif 25 <= bmi < 30:
        return "Overweight", "text-warning"
    else:
        return "Obese", "text-danger"

def calculate_safe_weight_change(current_weight, target_weight, weeks):
    """Calculate safe weight change ensuring no more than 2lbs per week"""
    weight_diff = target_weight - current_weight
    max_safe_change = 0.907 * weeks  # 2 lbs = 0.907 kg per week
    
    if abs(weight_diff) > max_safe_change:
        if weight_diff > 0:
            recommended_target = current_weight + max_safe_change
            message = f"For safe weight gain, we recommend targeting {recommended_target:.1f}kg instead."
        else:
            recommended_target = current_weight - max_safe_change
            message = f"For safe weight loss, we recommend targeting {recommended_target:.1f}kg instead."
        return False, message, recommended_target
    
    return True, "Target weight is within safe limits.", target_weight

@fitness_bp.route('/dashboard')
def fitness_dashboard():
    """Display fitness dashboard with BMI calculator and weight tracking"""
    if '_user_id' not in session:
        flash('Please log in to access fitness features.', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = session['_user_id']
    
    # Get recent weight logs
    recent_weights = WeightLog.query.filter_by(user_id=user_id).order_by(
        WeightLog.log_date.desc()
    ).limit(10).all()
    
    # Get recent workouts
    recent_workouts = WorkoutLog.query.filter_by(user_id=user_id).order_by(
        WorkoutLog.workout_date.desc()
    ).limit(5).all()
    
    return render_template('fitness/dashboard.html', 
                         recent_weights=recent_weights,
                         recent_workouts=recent_workouts,
                         title="Fitness Dashboard")

@fitness_bp.route('/api/latest-weight')
def api_latest_weight():
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    user_id = session['_user_id']
    latest_weight = WeightLog.query.filter_by(user_id=user_id).order_by(WeightLog.log_date.desc()).first()
    if latest_weight:
        return jsonify({'success': True, 'weight_kg': latest_weight.weight_kg})
    else:
        return jsonify({'success': True, 'weight_kg': None})

@fitness_bp.route('/bmi-calculator', methods=['GET', 'POST'])
def bmi_calculator():
    """BMI Calculator page with multiple unit support"""
    if '_user_id' not in session:
        flash('Please log in to access fitness features.', 'warning')
        return redirect(url_for('auth.login'))
    
    bmi_result = None
    category = None
    color_class = None
    weight_display = None
    height_display = None
    
    if request.method == 'POST':
        try:
            # Get weight in kg
            weight_unit = request.form.get('weight_unit', 'kg')
            if weight_unit == 'kg':
                weight_kg = float(request.form.get('weight_kg', 0))
                weight_display = f"{weight_kg} kg"
            elif weight_unit == 'lbs':
                weight_lbs = float(request.form.get('weight_lbs', 0))
                weight_kg = weight_lbs / 2.205
                weight_display = f"{weight_lbs} lbs"
            elif weight_unit == 'st_lbs':
                stones = float(request.form.get('weight_stones', 0))
                pounds = float(request.form.get('weight_pounds', 0))
                total_lbs = (stones * 14) + pounds
                weight_kg = total_lbs / 2.205
                weight_display = f"{int(stones)} st {pounds} lbs"
            
            # Get height in cm
            height_unit = request.form.get('height_unit', 'cm')
            if height_unit == 'cm':
                height_cm = float(request.form.get('height_cm', 0))
                height_display = f"{height_cm} cm"
            elif height_unit == 'ft_in':
                feet = float(request.form.get('height_feet', 0))
                inches = float(request.form.get('height_inches', 0))
                total_inches = (feet * 12) + inches
                height_cm = total_inches * 2.54
                height_display = f"{int(feet)}' {inches}\""
            
            # Calculate BMI
            bmi_result = calculate_bmi(weight_kg, height_cm)
            category, color_class = get_bmi_category(bmi_result)
            
        except (ValueError, TypeError, ZeroDivisionError):
            flash('Please enter valid numbers for weight and height.', 'error')
    
    return render_template('fitness/bmi_calculator.html', 
                         bmi=bmi_result,
                         category=category,
                         color_class=color_class,
                         weight_display=weight_display,
                         height_display=height_display,
                         title="BMI Calculator")

@fitness_bp.route('/weight-goal-planner', methods=['GET', 'POST'])
def weight_goal_planner():
    """Safe weight goal planner with multiple unit support"""
    if '_user_id' not in session:
        flash('Please log in to access fitness features.', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = session['_user_id']
    result = None
    
    # Get current weight from most recent log
    latest_weight = WeightLog.query.filter_by(user_id=user_id).order_by(
        WeightLog.log_date.desc()
    ).first()
    
    current_weight = latest_weight.weight_kg if latest_weight else None
    
    if request.method == 'POST':
        try:
            # Use converted weights if available (from JavaScript form submission)
            if request.form.get('current_weight_converted') and request.form.get('target_weight_converted'):
                current_weight_kg = float(request.form.get('current_weight_converted'))
                target_weight_kg = float(request.form.get('target_weight_converted'))
            else:
                # Fallback to manual conversion (shouldn't happen with the updated form)
                weight_unit = request.form.get('weight_unit', 'kg')
                
                # Get current weight in kg
                if weight_unit == 'kg':
                    current_weight_kg = float(request.form.get('current_weight_kg', current_weight or 0))
                elif weight_unit == 'lbs':
                    current_weight_lbs = float(request.form.get('current_weight_lbs', 0))
                    current_weight_kg = current_weight_lbs / 2.205
                elif weight_unit == 'st_lbs':
                    stones = float(request.form.get('current_weight_stones', 0))
                    pounds = float(request.form.get('current_weight_pounds', 0))
                    total_lbs = (stones * 14) + pounds
                    current_weight_kg = total_lbs / 2.205
                
                # Get target weight in kg
                if weight_unit == 'kg':
                    target_weight_kg = float(request.form.get('target_weight_kg', 0))
                elif weight_unit == 'lbs':
                    target_weight_lbs = float(request.form.get('target_weight_lbs', 0))
                    target_weight_kg = target_weight_lbs / 2.205
                elif weight_unit == 'st_lbs':
                    stones = float(request.form.get('target_weight_stones', 0))
                    pounds = float(request.form.get('target_weight_pounds', 0))
                    total_lbs = (stones * 14) + pounds
                    target_weight_kg = total_lbs / 2.205
            
            weeks = int(request.form.get('weeks', 1))
            
            is_safe, message, recommended_target = calculate_safe_weight_change(
                current_weight_kg, target_weight_kg, weeks
            )
            
            result = {
                'is_safe': is_safe,
                'message': message,
                'recommended_target': recommended_target,
                'weekly_change': abs(target_weight_kg - current_weight_kg) / weeks,
                'max_safe_weekly': 0.907  # 2 lbs in kg
            }
            
        except (ValueError, TypeError, ZeroDivisionError) as e:
            flash('Please enter valid numbers for all fields.', 'error')
    
    return render_template('fitness/weight_goal_planner.html',
                         current_weight=current_weight,
                         result=result,
                         title="Safe Weight Goal Planner")

@fitness_bp.route('/log-weight-page')
def log_weight_page():
    """Weight logging page"""
    if '_user_id' not in session:
        flash('Please log in to access fitness features.', 'warning')
        return redirect(url_for('auth.login'))
    
    return render_template('fitness/log_weight.html', title="Log Weight")

@fitness_bp.route('/weight-history')
def weight_history():
    """Display weight history with charts"""
    if '_user_id' not in session:
        flash('Please log in to access fitness features.', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = session['_user_id']
    weights = WeightLog.query.filter_by(user_id=user_id).order_by(
        WeightLog.log_date.desc()
    ).all()
    
    return render_template('fitness/weight_history.html',
                         weights=weights,
                         title="Weight History")

@fitness_bp.route('/weight-logs/<int:log_id>', methods=['DELETE'])
def delete_weight_log(log_id):
    """Delete a weight log entry"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        # Validate CSRF token for DELETE requests
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except ValidationError:
            return jsonify({'success': False, 'error': 'CSRF token validation failed'}), 400
        
        user_id = session['_user_id']
        log = WeightLog.query.filter_by(id=log_id, user_id=user_id).first()
        
        if not log:
            return jsonify({'success': False, 'error': 'Weight log not found'}), 404
            
        db.session.delete(log)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Weight log deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@fitness_bp.route('/log-workout-page')
def log_workout_page():
    """Display the workout logging page"""
    if '_user_id' not in session:
        flash('Please log in to access fitness features.', 'warning')
        return redirect(url_for('auth.login'))
    
    return render_template('fitness/log_workout.html')

@fitness_bp.route('/log-workout', methods=['POST'])
def log_workout():
    """Log a workout entry for the current user."""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        # Validate CSRF token for JSON requests
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except ValidationError:
            return jsonify({'success': False, 'error': 'CSRF token validation failed'}), 400
        
        data = request.get_json()
        user_id = session['_user_id']

        workout_date_str = data.get('workout_date', date.today().isoformat())
        workout_date = datetime.strptime(workout_date_str, '%Y-%m-%d').date()

        # Create new workout log
        workout_log = WorkoutLog(
            user_id=user_id,
            workout_date=workout_date,
            workout_type=data.get('workout_type'),
            duration_minutes=data.get('duration_minutes'),
            notes=data.get('notes'),
            calories_burned=data.get('calories_burned')
        )
        
        # Handle start and end times if provided
        if data.get('start_time'):
            start_time_str = f"{workout_date_str} {data['start_time']}:00"
            workout_log.start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
            
        if data.get('end_time'):
            end_time_str = f"{workout_date_str} {data['end_time']}:00"
            workout_log.end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')

        db.session.add(workout_log)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Workout logged successfully', 'workout': workout_log.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@fitness_bp.route('/log-exercise', methods=['POST'])
def log_exercise():
    """Log an exercise entry for a workout."""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        # Validate CSRF token for JSON requests
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except ValidationError:
            return jsonify({'success': False, 'error': 'CSRF token validation failed'}), 400
        
        data = request.get_json()
        user_id = session['_user_id']
        workout_log_id = data.get('workout_log_id')

        # Verify the workout belongs to the current user
        workout_log = WorkoutLog.query.filter_by(id=workout_log_id, user_id=user_id).first()
        if not workout_log:
            return jsonify({'success': False, 'error': 'Workout not found or access denied'}), 404

        # Create new exercise log
        exercise_log = ExerciseLog(
            workout_log_id=workout_log_id,
            exercise_name=data.get('exercise_name'),
            exercise_type=data.get('exercise_type'),
            sets=data.get('sets'),
            reps=data.get('reps'),
            weight_kg=data.get('weight_kg'),
            distance_km=data.get('distance_km'),
            duration_minutes=data.get('duration_minutes'),
            calories_burned=data.get('calories_burned'),
            notes=data.get('notes')
        )

        db.session.add(exercise_log)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Exercise logged successfully', 'exercise': exercise_log.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@fitness_bp.route('/exercise-logs/<int:exercise_id>', methods=['DELETE'])
def delete_exercise_log(exercise_id):
    """Delete an exercise log entry"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        # Validate CSRF token for DELETE requests
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except ValidationError:
            return jsonify({'success': False, 'error': 'CSRF token validation failed'}), 400
        
        user_id = session['_user_id']
        
        # Find the exercise log and verify it belongs to the user
        exercise_log = ExerciseLog.query.join(WorkoutLog).filter(
            ExerciseLog.id == exercise_id,
            WorkoutLog.user_id == user_id
        ).first()
        
        if not exercise_log:
            return jsonify({'success': False, 'error': 'Exercise log not found'}), 404
            
        db.session.delete(exercise_log)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Exercise log deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@fitness_bp.route('/workout-history')
def workout_history():
    """Display workout history with detailed exercise information"""
    if '_user_id' not in session:
        flash('Please log in to access fitness features.', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = session['_user_id']
    workouts = WorkoutLog.query.filter_by(user_id=user_id).order_by(
        WorkoutLog.workout_date.desc()
    ).all()
    
    # Define workout type icons
    workout_type_icons = {
        'Strength Training': 'dumbbell',
        'Cardio': 'running',
        'HIIT': 'fire',
        'Yoga': 'leaf',
        'Pilates': 'circle',
        'Stretching': 'expand-arrows-alt',
        'Sports': 'futbol',
        'Mixed': 'random',
        'Other': 'dumbbell'
    }
    
    # Calculate seven days ago for statistics
    from datetime import timedelta
    seven_days_ago = date.today() - timedelta(days=7)
    
    return render_template('fitness/workout_history.html',
                         workouts=workouts,
                         workout_type_icons=workout_type_icons,
                         seven_days_ago=seven_days_ago,
                         title="Workout History")

@fitness_bp.route('/workout-logs/<int:workout_id>', methods=['DELETE'])
def delete_workout_log(workout_id):
    """Delete a workout log entry and all associated exercises"""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        # Validate CSRF token for DELETE requests
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except ValidationError:
            return jsonify({'success': False, 'error': 'CSRF token validation failed'}), 400
        
        user_id = session['_user_id']
        workout = WorkoutLog.query.filter_by(id=workout_id, user_id=user_id).first()
        
        if not workout:
            return jsonify({'success': False, 'error': 'Workout not found'}), 404
            
        # Delete all associated exercises first
        ExerciseLog.query.filter_by(workout_log_id=workout_id).delete()
        
        # Then delete the workout
        db.session.delete(workout)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Workout and all exercises deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@fitness_bp.route('/log-weight', methods=['POST'])
def log_weight():
    """Log a weight entry for the current user."""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401

    try:
        # Validate CSRF token for JSON requests
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except ValidationError:
            return jsonify({'success': False, 'error': 'CSRF token validation failed'}), 400
        
        data = request.get_json()
        user_id = session['_user_id']

        log_date_str = data.get('log_date', date.today().isoformat())
        log_date = datetime.strptime(log_date_str, '%Y-%m-%d').date()

        # Check for an existing entry for this date
        weight_log = WeightLog.query.filter_by(user_id=user_id, log_date=log_date).first()

        if not weight_log:
            weight_log = WeightLog(user_id=user_id, log_date=log_date)
            db.session.add(weight_log)

        weight_log.weight_kg = float(data['weight_kg'])
        if 'body_fat_percentage' in data and data['body_fat_percentage']:
            weight_log.body_fat_percentage = float(data['body_fat_percentage'])
        if 'notes' in data and data['notes']:
            weight_log.notes = data['notes']

        db.session.commit()

        return jsonify({'success': True, 'message': 'Weight logged successfully', 'log': weight_log.to_dict()})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@fitness_bp.route('/weight-logs', methods=['GET'])
def get_weight_logs():
    """Get all weight logs for the current user."""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
    user_id = session['_user_id']
    logs = WeightLog.query.filter_by(user_id=user_id).order_by(WeightLog.log_date.desc()).all()
    
    return jsonify({'success': True, 'logs': [log.to_dict() for log in logs]})

# Duplicate function removed - using the more complete version above

@fitness_bp.route('/workout-logs', methods=['GET'])
def get_workout_logs():
    """Get all workout logs for the current user."""
    if '_user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
    user_id = session['_user_id']
    logs = WorkoutLog.query.filter_by(user_id=user_id).order_by(WorkoutLog.workout_date.desc()).all()
    
    return jsonify({'success': True, 'logs': [log.to_dict() for log in logs]})

# Duplicate function removed - using the more complete version above with CSRF validation

@fitness_bp.route('/analytics')
def analytics():
    """Display fitness analytics and progress reports"""
    if '_user_id' not in session:
        flash('Please log in to access fitness features.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Placeholder for analytics page
    return render_template('fitness/analytics.html')

@fitness_bp.route('/achievements')
def achievements():
    """Display fitness achievements and milestones"""
    if '_user_id' not in session:
        flash('Please log in to access fitness features.', 'warning')
        return redirect(url_for('auth.login'))
    
    # Placeholder for achievements page
    return render_template('fitness/achievements.html')

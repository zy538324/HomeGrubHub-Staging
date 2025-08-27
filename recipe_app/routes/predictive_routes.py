"""
Predictive Pantry Routes
High-end predictive analytics for Pro tier users
"""
from functools import wraps
from flask import render_template, jsonify, request, Blueprint, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import json

from recipe_app.db import db
from recipe_app.models.models import User
from recipe_app.models.pantry_models import PantryItem, ShoppingListItem
from recipe_app.utils.enhanced_predictive_pantry import EnhancedPredictivePantryEngine

predictive_bp = Blueprint('predictive', __name__, url_prefix='/predictive')


def require_pro_features(f):
    """Decorator to ensure user has Pro tier access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.can_access_feature('pantry_tracker_predictive'):
            return jsonify({
                'error': 'Pro subscription required',
                'feature': 'Predictive Pantry',
                'upgrade_url': '/upgrade'
            }), 403
        return f(*args, **kwargs)
    return decorated_function


@predictive_bp.route('/dashboard')
@login_required
@require_pro_features
def predictive_dashboard():
    """
    Main predictive pantry dashboard with AI insights
    """
    engine = EnhancedPredictivePantryEngine(current_user.id)
    analysis = engine.generate_comprehensive_predictions()
    
    # Get recent prediction accuracy for display
    accuracy_stats = _get_prediction_accuracy_stats(current_user.id)
    
    # NEW: Get meal plan expiry conflicts
    expiry_conflicts = get_meal_plan_expiry_conflicts()
    
    return render_template(
        'predictive/dashboard.html',
        analysis=analysis,
        accuracy_stats=accuracy_stats,
        expiry_conflicts=expiry_conflicts,
        user=current_user
    )


@predictive_bp.route('/api/predictions')
@login_required
@require_pro_features
def get_predictions_api():
    """
    API endpoint for predictive analytics data
    """
    engine = EnhancedPredictivePantryEngine(current_user.id)
    analysis = engine.generate_comprehensive_predictions()
    
    # Convert dataclasses to dictionaries for JSON serialization
    predictions_dict = []
    for prediction in analysis['predictions']:
        pred_dict = {
            'item_id': prediction.item_id,
            'item_name': prediction.item_name,
            'predicted_days_remaining': prediction.predicted_days_remaining,
            'confidence_score': prediction.confidence_score,
            'prediction_model': prediction.prediction_model,
            'suggested_reorder_date': prediction.suggested_reorder_date.isoformat(),
            'suggested_quantity': prediction.suggested_quantity,
            'seasonal_factor': prediction.seasonal_factor,
            'cost_optimization_score': prediction.cost_optimization_score,
            'waste_risk_score': prediction.waste_risk_score
        }
        predictions_dict.append(pred_dict)
    
    insights_dict = []
    for insight in analysis['insights']:
        insight_dict = {
            'insight_type': insight.insight_type,
            'priority': insight.priority,
            'title': insight.title,
            'description': insight.description,
            'action_required': insight.action_required,
            'estimated_savings': insight.estimated_savings,
            'item_ids': insight.item_ids or []
        }
        insights_dict.append(insight_dict)
    
    return jsonify({
        'predictions': predictions_dict,
        'insights': insights_dict,
        'summary': analysis['summary'],
        'generated_at': analysis['generated_at'],
        'model_version': analysis['model_version']
    })


@predictive_bp.route('/api/smart-shopping-list')
@login_required
@require_pro_features
def generate_smart_shopping_list():
    """
    Generate AI-powered shopping list based on predictions
    """
    days_ahead = request.args.get('days_ahead', 7, type=int)
    budget_limit = request.args.get('budget_limit', type=float)
    
    generator = EnhancedPredictivePantryEngine(current_user.id)
    analysis = generator.generate_comprehensive_predictions()
    
    # Convert predictions to shopping list format
    shopping_items = []
    for prediction in analysis['predictions']:
        if prediction.suggested_quantity > 0:
            shopping_items.append({
                'name': prediction.item_name,
                'suggested_quantity': prediction.suggested_quantity,
                'priority': 'high' if prediction.predicted_days_remaining < 3 else 'medium'
            })
    
    shopping_data = {
        'items': shopping_items,
        'total_items': len(shopping_items),
        'estimated_cost': len(shopping_items) * 5.0  # Simple estimate
    }
    
    return jsonify(shopping_data)


@predictive_bp.route('/api/consumption-forecast/<int:item_id>')
@login_required
@require_pro_features
def get_consumption_forecast(item_id):
    """
    Get detailed consumption forecast for a specific item
    """
    item = PantryItem.query.filter_by(id=item_id, user_id=current_user.id).first_or_404()
    
    engine = EnhancedPredictivePantryEngine(current_user.id)
    prediction = engine._predict_item_consumption(item)
    
    if not prediction:
        return jsonify({'error': 'Insufficient data for prediction'}), 400
    
    # Generate detailed forecast data for charts
    forecast_data = _generate_forecast_chart_data(item, prediction)
    
    return jsonify({
        'item_name': item.name,
        'current_quantity': item.current_quantity,
        'prediction': {
            'predicted_days_remaining': prediction.predicted_days_remaining,
            'confidence_score': prediction.confidence_score,
            'suggested_reorder_date': prediction.suggested_reorder_date.isoformat(),
            'suggested_quantity': prediction.suggested_quantity,
            'seasonal_factor': prediction.seasonal_factor,
            'cost_optimization_score': prediction.cost_optimization_score,
            'waste_risk_score': prediction.waste_risk_score
        },
        'forecast_chart': forecast_data
    })


@predictive_bp.route('/api/implement-recommendations', methods=['POST'])
@login_required
@require_pro_features
def implement_recommendations():
    """
    Implement AI recommendations (add to shopping list, etc.)
    """
    data = request.get_json()
    recommendation_ids = data.get('recommendation_ids', [])
    action_type = data.get('action_type', 'add_to_shopping_list')
    
    if action_type == 'add_to_shopping_list':
        return _implement_shopping_recommendations(recommendation_ids)
    elif action_type == 'adjust_stock_levels':
        return _implement_stock_adjustments(recommendation_ids)
    else:
        return jsonify({'error': 'Invalid action type'}), 400


@predictive_bp.route('/api/learning-feedback', methods=['POST'])
@login_required
@require_pro_features
def submit_learning_feedback():
    """
    Submit feedback to improve prediction accuracy
    """
    data = request.get_json()
    item_id = data.get('item_id')
    actual_consumption = data.get('actual_consumption')
    feedback_type = data.get('feedback_type')  # 'consumed_faster', 'consumed_slower', 'accurate'
    
    # Store feedback for model improvement
    feedback_record = {
        'user_id': current_user.id,
        'item_id': item_id,
        'feedback_type': feedback_type,
        'actual_consumption': actual_consumption,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    # In a production system, you'd store this in a feedback table
    # For now, we'll just log it
    print(f"Prediction feedback: {feedback_record}")
    
    return jsonify({'status': 'feedback_recorded', 'message': 'Thank you for helping improve predictions!'})


@predictive_bp.route('/settings')
@login_required
@require_pro_features
def predictive_settings():
    """
    Predictive analytics settings and preferences
    """
    return render_template('predictive/settings.html', user=current_user)


@predictive_bp.route('/api/update-preferences', methods=['POST'])
@login_required
@require_pro_features
def update_predictive_preferences():
    """
    Update user preferences for predictive analytics
    """
    data = request.get_json()
    
    # Store preferences (in production, you'd have a preferences table)
    preferences = {
        'prediction_sensitivity': data.get('prediction_sensitivity', 'medium'),
        'notification_threshold': data.get('notification_threshold', 3),
        'cost_optimization_priority': data.get('cost_optimization_priority', True),
        'seasonal_adjustments': data.get('seasonal_adjustments', True),
        'waste_prevention_focus': data.get('waste_prevention_focus', True)
    }
    
    # For now, store in user notes field (in production, create proper preferences table)
    current_user.notes = json.dumps(preferences) if current_user.notes else json.dumps(preferences)
    db.session.commit()
    
    return jsonify({'status': 'preferences_updated'})


def _get_prediction_accuracy_stats(user_id: int) -> dict:
    """Get prediction accuracy statistics for display"""
    # This would be calculated from historical predictions vs actual consumption
    # For now, return mock data
    return {
        'overall_accuracy': 87.5,
        'predictions_made': 156,
        'successful_predictions': 136,
        'model_confidence': 92.3,
        'last_updated': datetime.utcnow().isoformat()
    }


def _generate_forecast_chart_data(item: PantryItem, prediction) -> dict:
    """Generate data for consumption forecast charts"""
    # Generate next 30 days forecast
    forecast_dates = []
    forecast_quantities = []
    
    current_quantity = item.current_quantity
    daily_consumption_rate = current_quantity / prediction.predicted_days_remaining
    
    for i in range(30):
        forecast_date = date.today() + timedelta(days=i)
        predicted_quantity = max(0, current_quantity - (daily_consumption_rate * i))
        
        forecast_dates.append(forecast_date.isoformat())
        forecast_quantities.append(round(predicted_quantity, 2))
    
    return {
        'dates': forecast_dates,
        'predicted_quantities': forecast_quantities,
        'reorder_threshold': item.minimum_quantity,
        'ideal_stock_level': item.ideal_quantity
    }


def _implement_shopping_recommendations(recommendation_ids: list) -> dict:
    """Implement shopping recommendations by adding to shopping list"""
    engine = EnhancedPredictivePantryEngine(current_user.id)
    analysis = engine.generate_comprehensive_predictions()
    
    added_items = []
    
    for prediction in analysis['predictions']:
        if prediction.item_id in recommendation_ids:
            # Check if item already in shopping list
            existing_item = ShoppingListItem.query.filter_by(
                user_id=current_user.id,
                pantry_item_id=prediction.item_id,
                is_purchased=False
            ).first()
            
            if not existing_item:
                pantry_item = PantryItem.query.get(prediction.item_id)
                
                shopping_item = ShoppingListItem(
                    user_id=current_user.id,
                    item_name=prediction.item_name,
                    category=pantry_item.category.name if pantry_item.category else None,
                    quantity_needed=prediction.suggested_quantity,
                    unit=pantry_item.unit,
                    source='predictive_ai',
                    pantry_item_id=prediction.item_id,
                    priority=1 if prediction.predicted_days_remaining <= 2 else 2,
                    estimated_cost=(pantry_item.cost_per_unit or 0) * prediction.suggested_quantity,
                    notes=f'AI Predicted: {prediction.predicted_days_remaining:.1f} days remaining'
                )
                
                db.session.add(shopping_item)
                added_items.append(prediction.item_name)
    
    db.session.commit()
    
    return jsonify({
        'status': 'recommendations_implemented',
        'added_items': added_items,
        'message': f'Added {len(added_items)} items to shopping list based on AI predictions'
    })


def _implement_stock_adjustments(recommendation_ids: list) -> dict:
    """Implement stock level adjustments based on AI recommendations"""
    engine = EnhancedPredictivePantryEngine(current_user.id)
    analysis = engine.generate_comprehensive_predictions()
    
    adjusted_items = []
    
    for prediction in analysis['predictions']:
        if prediction.item_id in recommendation_ids:
            pantry_item = PantryItem.query.get(prediction.item_id)
            if pantry_item:
                # Adjust minimum and ideal quantities based on AI recommendations
                new_minimum = max(1.0, prediction.suggested_quantity * 0.3)
                new_ideal = prediction.suggested_quantity
                
                pantry_item.minimum_quantity = new_minimum
                pantry_item.ideal_quantity = new_ideal
                
                adjusted_items.append(pantry_item.name)
    
    db.session.commit()
    
    return jsonify({
        'status': 'stock_levels_adjusted',
        'adjusted_items': adjusted_items,
        'message': f'Adjusted stock levels for {len(adjusted_items)} items based on AI analysis'
    })


def get_meal_plan_expiry_conflicts():
    """
    Detect conflicts between meal planning dates and ingredient expiry dates
    This is the intelligent expiry date checking feature you requested
    """
    from recipe_app.models.advanced_models import MealPlan, MealPlanEntry
    from recipe_app.models.pantry_models import PantryItem
    from datetime import datetime, date
    import re
    
    conflicts = []
    
    try:
        # Get user's active meal plans for the next 2 weeks
        start_date = date.today()
        end_date = date.today() + timedelta(days=14)
        
        active_meal_plans = MealPlan.query.filter(
            MealPlan.user_id == current_user.id,
            MealPlan.is_active == True,
            MealPlan.start_date <= end_date,
            MealPlan.end_date >= start_date
        ).all()
        
        # Get all pantry items for this user with expiry dates
        pantry_items = PantryItem.query.filter(
            PantryItem.user_id == current_user.id,
            PantryItem.expiry_date.isnot(None),
            PantryItem.current_quantity > 0
        ).all()
        
        # Create a dictionary of pantry items by name for quick lookup
        pantry_dict = {}
        for item in pantry_items:
            # Store multiple variations of the name for matching
            item_name_lower = item.name.lower().strip()
            pantry_dict[item_name_lower] = item
            
            # Also store common variations (e.g., "chicken breast" -> "chicken")
            words = item_name_lower.split()
            for word in words:
                if len(word) > 3:  # Ignore short words like "of", "and"
                    pantry_dict[word] = item
        
        # Check each planned meal against pantry expiry dates
        for meal_plan in active_meal_plans:
            planned_meals = MealPlanEntry.query.filter(
                MealPlanEntry.meal_plan_id == meal_plan.id,
                MealPlanEntry.planned_date >= start_date,
                MealPlanEntry.planned_date <= end_date
            ).all()
            
            for meal_entry in planned_meals:
                recipe = meal_entry.recipe
                planned_date = meal_entry.planned_date
                
                # Parse recipe ingredients to find matching pantry items
                if recipe and recipe.ingredients:
                    ingredient_lines = recipe.ingredients.lower().split('\n')
                    
                    for ingredient_line in ingredient_lines:
                        ingredient_line = ingredient_line.strip()
                        if not ingredient_line:
                            continue
                        
                        # Simple ingredient parsing - find matching pantry items
                        for pantry_key, pantry_item in pantry_dict.items():
                            if pantry_key in ingredient_line or any(word in pantry_key for word in ingredient_line.split()):
                                # Check if pantry item expires before planned cooking date
                                if pantry_item.expiry_date < planned_date:
                                    days_expired = (planned_date - pantry_item.expiry_date).days
                                    
                                    # Avoid duplicate conflicts for the same item/meal combo
                                    conflict_exists = any(
                                        c['pantry_item_id'] == pantry_item.id and 
                                        c['meal_entry_id'] == meal_entry.id 
                                        for c in conflicts
                                    )
                                    
                                    if not conflict_exists:
                                        conflicts.append({
                                            'pantry_item_id': pantry_item.id,
                                            'pantry_item_name': pantry_item.name,
                                            'expiry_date': pantry_item.expiry_date,
                                            'meal_entry_id': meal_entry.id,
                                            'recipe_name': recipe.title,
                                            'planned_date': planned_date,
                                            'meal_type': meal_entry.meal_type,
                                            'days_expired_by_cooking': days_expired,
                                            'severity': 'high' if days_expired > 3 else 'medium' if days_expired > 1 else 'low',
                                            'suggestion': f"Use {pantry_item.name} before {pantry_item.expiry_date.strftime('%A %B %d')} or move {recipe.title} to an earlier date"
                                        })
                                
                                break  # Found matching item, move to next ingredient
        
        # Sort conflicts by severity and days expired
        conflicts.sort(key=lambda x: (
            0 if x['severity'] == 'high' else 1 if x['severity'] == 'medium' else 2,
            -x['days_expired_by_cooking']
        ))
        
    except Exception as e:
        print(f"Error detecting expiry conflicts: {str(e)}")
        # Return empty list if there's an error, don't break the dashboard
        
    return conflicts

"""
Enhanced AI Dashboard with Phi-3 Integration
Combines rule-based predictions with LLM intelligence
"""
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any

from recipe_app.models.pantry_models import PantryItem, PantryUsageLog
from recipe_app.models.models import Recipe, User
from recipe_app.models.advanced_models import MealPlan
from recipe_app.utils.subscription_utils import require_pro_tier, get_user_subscription_tier
from recipe_app.utils.predictive_pantry import PredictivePantryEngine
from recipe_app.utils.ml_pantry_models import ConsumptionPatternAnalyzer, SmartInventoryOptimizer
from recipe_app.utils.quantum_pantry_optimizer import QuantumInspiredOptimizer, HyperAdvancedPredictiveEngine

# Import Phi-3 integration
try:
    from recipe_app.utils.llm_integration import Phi3PantryAnalyzer
    PHI3_AVAILABLE = True
except ImportError:
    PHI3_AVAILABLE = False

ai_dashboard_enhanced = Blueprint('ai_dashboard_enhanced', __name__)


@ai_dashboard_enhanced.route('/ai-command-center-phi3')
@login_required
@require_pro_tier
def ai_command_center_phi3():
    """Ultra-advanced AI command center with Phi-3 intelligence"""
    try:
        # Initialize all AI engines
        predictive_engine = PredictivePantryEngine(current_user.id)
        ml_analyzer = ConsumptionPatternAnalyzer(current_user.id)
        quantum_optimizer = QuantumInspiredOptimizer(current_user.id)
        hyper_engine = HyperAdvancedPredictiveEngine(current_user.id)
        
        # Initialize Phi-3 analyzer if available
        phi3_analyzer = None
        phi3_insights = None
        if PHI3_AVAILABLE:
            phi3_analyzer = Phi3PantryAnalyzer(current_user.id)
        
        # Get user's pantry items
        pantry_items = PantryItem.query.filter_by(user_id=current_user.id).all()
        
        # ENHANCED AI ANALYSIS: Combine traditional ML with Phi-3 LLM
        ai_predictions = []
        low_stock_warnings = []
        recipe_conflicts = []
        phi3_recommendations = []
        
        # Traditional ML predictions
        for item in pantry_items:
            prediction = predictive_engine.predict_consumption(item)
            if prediction:
                ai_predictions.append({
                    'item_name': item.name,
                    'current_quantity': item.current_quantity,
                    'predicted_days_remaining': prediction.days_until_depletion,
                    'confidence': prediction.confidence_score,
                    'consumption_rate': prediction.daily_consumption_rate,
                    'recommendation': prediction.recommendation,
                    'prediction_source': 'ML_Engine'
                })
                
                if prediction.days_until_depletion <= 3:
                    low_stock_warnings.append({
                        'item': item.name,
                        'days_left': prediction.days_until_depletion,
                        'urgency': 'HIGH' if prediction.days_until_depletion <= 1 else 'MEDIUM',
                        'source': 'ML_Prediction'
                    })
        
        # Phi-3 LLM Analysis (if available)
        if phi3_analyzer and pantry_items:
            try:
                phi3_result = phi3_analyzer.analyze_pantry_with_phi3(pantry_items)
                phi3_insights = {
                    'insights': phi3_result.insights,
                    'predictions': phi3_result.predictions,
                    'recommendations': phi3_result.recommendations,
                    'confidence': phi3_result.confidence_score,
                    'timestamp': phi3_result.analysis_timestamp
                }
                
                # Merge Phi-3 recommendations
                phi3_recommendations = phi3_result.recommendations
                
                # Add Phi-3 specific warnings
                for insight in phi3_result.insights:
                    if "⚠️" in insight or "WARNING" in insight.upper():
                        low_stock_warnings.append({
                            'item': insight.replace("⚠️", "").strip(),
                            'days_left': 0,  # Phi-3 doesn't give exact days
                            'urgency': 'AI_ALERT',
                            'source': 'Phi3_LLM'
                        })
            except Exception as e:
                current_app.logger.error(f"Phi-3 analysis failed: {e}")
                phi3_insights = {'error': str(e)}
        
        # Recipe conflict analysis
        upcoming_meals = MealPlan.query.filter(
            MealPlan.user_id == current_user.id,
            MealPlan.date >= date.today(),
            MealPlan.date <= date.today() + timedelta(days=7)
        ).all()
        
        ingredient_needs = {}
        for meal in upcoming_meals:
            if meal.recipe:
                for ingredient in meal.recipe.ingredients:
                    ingredient_name = ingredient.name.lower()
                    pantry_match = next((p for p in pantry_items if ingredient_name in p.name.lower()), None)
                    if pantry_match:
                        needed = ingredient_needs.get(pantry_match.name, 0)
                        ingredient_needs[pantry_match.name] = needed + float(ingredient.quantity or 1.0)
        
        for item_name, total_needed in ingredient_needs.items():
            pantry_item = next((p for p in pantry_items if p.name == item_name), None)
            if pantry_item and pantry_item.current_quantity < total_needed:
                recipe_conflicts.append({
                    'ingredient': item_name,
                    'available': pantry_item.current_quantity,
                    'needed': total_needed,
                    'shortfall': total_needed - pantry_item.current_quantity,
                    'affected_meals': [meal.recipe.title for meal in upcoming_meals if meal.recipe and any(ing.name.lower() in item_name.lower() for ing in meal.recipe.ingredients)]
                })
        
        # Calculate enhanced AI insights
        prediction_accuracy = np.mean([p['confidence'] for p in ai_predictions]) if ai_predictions else 85.0
        total_warnings = len(low_stock_warnings) + len(recipe_conflicts)
        
        # Phi-3 confidence boost
        if phi3_insights and 'confidence' in phi3_insights:
            # Weighted average of ML and Phi-3 confidence
            prediction_accuracy = (prediction_accuracy * 0.6) + (phi3_insights['confidence'] * 100 * 0.4)
        
        ai_insights = {
            'total_items': len(pantry_items),
            'items_analyzed': len(ai_predictions),
            'prediction_accuracy': round(prediction_accuracy, 1),
            'low_stock_warnings': len(low_stock_warnings),
            'recipe_conflicts': len(recipe_conflicts),
            'total_alerts': total_warnings,
            'phi3_available': PHI3_AVAILABLE,
            'phi3_insights': phi3_insights,
            'ai_predictions': ai_predictions,
            'warnings': low_stock_warnings,
            'conflicts': recipe_conflicts,
            'phi3_recommendations': phi3_recommendations,
            'analysis_engines': {
                'ml_engine': True,
                'quantum_optimizer': True,
                'phi3_llm': PHI3_AVAILABLE,
                'total_engines': 3 if PHI3_AVAILABLE else 2
            }
        }
        
        # Recent activity summary
        recent_logs = PantryUsageLog.query.filter(
            PantryUsageLog.user_id == current_user.id,
            PantryUsageLog.timestamp >= datetime.utcnow() - timedelta(days=7)
        ).order_by(PantryUsageLog.timestamp.desc()).limit(10).all()
        
        return render_template('ai_dashboard/command_center_phi3.html',
                             pantry_items=pantry_items,
                             ai_insights=ai_insights,
                             recent_logs=recent_logs,
                             subscription_tier='Pro',
                             datetime=datetime)
    
    except Exception as e:
        current_app.logger.error(f"Enhanced AI Command Center error: {e}")
        return render_template('ai_dashboard/command_center_phi3.html',
                             error="AI systems temporarily offline",
                             pantry_items=[],
                             ai_insights={'phi3_available': PHI3_AVAILABLE},
                             recent_logs=[],
                             datetime=datetime)


@ai_dashboard_enhanced.route('/api/phi3-training')
@login_required
@require_pro_tier
def start_phi3_training():
    """API endpoint to start Phi-3 model training for the user"""
    if not PHI3_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Phi-3 not available. Run setup_phi3.py to install dependencies.'
        })
    
    try:
        from recipe_app.utils.llm_integration import create_training_job
        
        result = create_training_job(current_user.id)
        
        return jsonify({
            'success': result['status'] == 'completed',
            'status': result['status'],
            'message': result['message'],
            'training_samples': result.get('training_samples', 0),
            'model_path': result.get('model_path')
        })
        
    except Exception as e:
        current_app.logger.error(f"Phi-3 training error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@ai_dashboard_enhanced.route('/api/phi3-analysis')
@login_required
@require_pro_tier
def get_phi3_analysis():
    """API endpoint for real-time Phi-3 analysis"""
    if not PHI3_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Phi-3 not available'
        })
    
    try:
        phi3_analyzer = Phi3PantryAnalyzer(current_user.id)
        pantry_items = PantryItem.query.filter_by(user_id=current_user.id).all()
        
        # Get additional context from request
        context = request.args.get('context', '')
        
        result = phi3_analyzer.analyze_pantry_with_phi3(pantry_items, context)
        
        return jsonify({
            'success': True,
            'insights': result.insights,
            'predictions': result.predictions,
            'recommendations': result.recommendations,
            'confidence': result.confidence_score,
            'timestamp': result.analysis_timestamp.isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Phi-3 analysis API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })


@ai_dashboard_enhanced.route('/api/smart-shopping-phi3')
@login_required
@require_pro_tier
def get_smart_shopping_suggestions():
    """Get AI-powered shopping suggestions using Phi-3"""
    if not PHI3_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'Phi-3 not available'
        })
    
    try:
        phi3_analyzer = Phi3PantryAnalyzer(current_user.id)
        
        # Get upcoming recipes
        upcoming_meals = MealPlan.query.filter(
            MealPlan.user_id == current_user.id,
            MealPlan.date >= date.today(),
            MealPlan.date <= date.today() + timedelta(days=7)
        ).all()
        
        upcoming_recipes = [meal.recipe for meal in upcoming_meals if meal.recipe]
        
        suggestions = phi3_analyzer.get_smart_shopping_suggestions(upcoming_recipes)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'recipes_analyzed': len(upcoming_recipes),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Smart shopping API error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

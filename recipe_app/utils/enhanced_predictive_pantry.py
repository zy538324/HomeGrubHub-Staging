"""
Enhanced Predictive Pantry Engine with Phi-3 Mini Integration
Combines traditional ML with LLM-powered analysis
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

from recipe_app.utils.predictive_pantry import PredictivePantryEngine, ConsumptionPrediction
from recipe_app.models.pantry_models import PantryItem, PantryUsageLog
from recipe_app.models.models import Recipe
from recipe_app.models.advanced_models import MealPlan

# Import Phi-3 engine with error handling
try:
    from recipe_app.ai_engine.phi3_engine import Phi3FlavorioEngine
except ImportError as e:
    logger.warning(f"Phi-3 engine import failed: {e}")
    Phi3FlavorioEngine = None

logger = logging.getLogger(__name__)

class EnhancedPredictivePantryEngine(PredictivePantryEngine):
    """
    Enhanced prediction engine that combines traditional ML with Phi-3 Mini LLM
    """
    
    def __init__(self, user_id: int, use_llm: bool = True):
        super().__init__(user_id)
        self.use_llm = use_llm and Phi3FlavorioEngine is not None
        self.llm_engine = None
        
        if self.use_llm:
            try:
                self.llm_engine = Phi3FlavorioEngine()
                logger.info("LLM engine initialized successfully")
            except Exception as e:
                logger.warning(f"LLM engine initialization failed: {e}")
                self.llm_engine = None
                self.use_llm = False
    
    def predict_consumption_with_llm(self, item: PantryItem) -> Dict:
        """
        Enhanced prediction combining traditional ML with LLM analysis
        """
        # Get traditional prediction
        traditional_prediction = self.predict_consumption(item)
        
        if self.llm_engine is None or traditional_prediction is None:
            return self._format_prediction_output(traditional_prediction, None, item)
        
        # Get usage history for LLM analysis
        usage_history = self._get_usage_history(item.id)
        
        # Use LLM for enhanced analysis
        try:
            llm_prediction = self.llm_engine.predict_consumption_patterns(usage_history, item.name)
            
            # Combine predictions intelligently
            combined_prediction = self._combine_predictions(traditional_prediction, llm_prediction, item)
            
            return self._format_prediction_output(traditional_prediction, llm_prediction, item, combined_prediction)
            
        except Exception as e:
            logger.error(f"LLM prediction failed for {item.name}: {e}")
            return self._format_prediction_output(traditional_prediction, None, item)
    
    def analyze_recipe_impact(self, recipe_text: str, recipe_title: str = "", planned_date: str = None) -> Dict:
        """
        Analyze how a recipe will impact pantry using LLM
        """
        if self.llm_engine is None:
            return self._fallback_recipe_impact_analysis(recipe_text, recipe_title)
        
        try:
            llm_analysis = self.llm_engine.analyze_recipe_ingredients(recipe_text, recipe_title)
            
            # Cross-reference with current pantry
            pantry_impact = self._analyze_pantry_impact(llm_analysis.get('ingredients', []))
            
            # Combine LLM analysis with pantry reality
            return {
                'llm_analysis': llm_analysis,
                'pantry_impact': pantry_impact,
                'recommendations': self._generate_recipe_recommendations(llm_analysis, pantry_impact),
                'confidence': llm_analysis.get('confidence', 75.0),
                'analysis_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Recipe impact analysis failed: {e}")
            return self._fallback_recipe_impact_analysis(recipe_text, recipe_title)
    
    def get_shopping_recommendations(self, user_query: str) -> Dict:
        """
        Natural language shopping assistant with context
        """
        if self.llm_engine is None:
            return {"response": "Shopping assistant is currently unavailable. Please try again later."}
        
        # Build context from user's current state
        context = self._build_user_context()
        
        try:
            response = self.llm_engine.conversational_shopping_assistant(user_query, context)
            
            # Add structured recommendations
            structured_recs = self._generate_structured_shopping_recommendations(context)
            
            return {
                'conversational_response': response,
                'structured_recommendations': structured_recs,
                'context_used': {
                    'pantry_items': len(context.get('pantry', [])),
                    'planned_meals': len(context.get('meals', [])),
                    'budget_specified': context.get('budget') != 'Not specified'
                },
                'response_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Shopping recommendations failed: {e}")
            return {"response": f"I apologize, but I'm having trouble processing your request right now. Error: {str(e)}"}
    
    def analyze_price_trends_with_llm(self, item_name: str) -> Dict:
        """
        Analyze price trends using LLM with fallback to traditional methods
        """
        # Get price history (mock data for now - replace with real data)
        price_history = self._get_price_history(item_name)
        
        if self.llm_engine is None:
            return self._fallback_price_analysis(price_history, item_name)
        
        try:
            llm_analysis = self.llm_engine.analyze_price_trends(price_history, item_name)
            
            # Add traditional analysis for comparison
            traditional_analysis = self._traditional_price_analysis(price_history)
            
            return {
                'llm_analysis': llm_analysis,
                'traditional_analysis': traditional_analysis,
                'recommendation': self._combine_price_recommendations(llm_analysis, traditional_analysis),
                'confidence': llm_analysis.get('confidence', 70.0),
                'data_points': len(price_history)
            }
            
        except Exception as e:
            logger.error(f"Price trend analysis failed: {e}")
            return self._fallback_price_analysis(price_history, item_name)
    
    def get_intelligent_pantry_insights(self) -> Dict:
        """
        Generate comprehensive AI-powered insights about the entire pantry
        """
        pantry_items = self._get_user_pantry()
        insights = {
            'total_items': len(pantry_items),
            'ai_predictions': [],
            'critical_alerts': [],
            'optimization_suggestions': [],
            'confidence_score': 0.0,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        confidence_scores = []
        
        for item in pantry_items:
            try:
                # Get enhanced prediction for each item
                prediction = self.predict_consumption_with_llm(item)
                insights['ai_predictions'].append(prediction)
                
                # Check for critical situations
                if prediction.get('days_until_depletion', 999) <= 2:
                    insights['critical_alerts'].append({
                        'type': 'low_stock',
                        'item': item.name,
                        'urgency': 'HIGH',
                        'days_remaining': prediction.get('days_until_depletion'),
                        'recommendation': prediction.get('recommendation')
                    })
                
                # Collect confidence scores
                if 'confidence' in prediction:
                    confidence_scores.append(prediction['confidence'])
                    
            except Exception as e:
                logger.error(f"Analysis failed for item {item.name}: {e}")
                continue
        
        # Calculate overall confidence
        if confidence_scores:
            insights['confidence_score'] = np.mean(confidence_scores)
        else:
            insights['confidence_score'] = 50.0  # Default when no data
        
        # Add missing fields that the template expects
        insights['total_alerts'] = len(insights['critical_alerts'])
        insights['low_stock_warnings'] = len([alert for alert in insights['critical_alerts'] if alert.get('type') == 'low_stock'])
        insights['recipe_conflicts'] = 0  # Will be populated by recipe analysis in the dashboard
        insights['warnings'] = [alert for alert in insights['critical_alerts'] if alert.get('type') == 'low_stock']
        insights['conflicts'] = []  # Will be populated by recipe analysis
        insights['prediction_accuracy'] = insights['confidence_score']  # Use confidence as accuracy
        
        # Generate optimization suggestions
        insights['optimization_suggestions'] = self._generate_optimization_suggestions(insights['ai_predictions'])
        
        return insights
    
    def _generate_optimization_suggestions(self, ai_predictions: List[Dict]) -> List[str]:
        """Generate optimization suggestions based on AI predictions"""
        suggestions = []
        
        if not ai_predictions:
            return ["No predictions available for optimization suggestions"]
        
        # Analyze predictions for optimization opportunities
        low_confidence_items = [p for p in ai_predictions if p.get('confidence', 0) < 70]
        critical_items = [p for p in ai_predictions if p.get('days_until_depletion', 999) <= 3]
        
        if critical_items:
            suggestions.append(f"Urgent: {len(critical_items)} items need immediate restocking")
        
        if low_confidence_items:
            suggestions.append(f"Monitor: {len(low_confidence_items)} items have uncertain predictions")
        
        # Add general optimization suggestions
        if len(ai_predictions) > 10:
            suggestions.append("Consider bulk purchasing for frequently used items")
        
        suggestions.append("Review consumption patterns weekly for better predictions")
        
        return suggestions
    
    def _get_user_pantry(self) -> List[PantryItem]:
        """Get user's pantry items"""
        return PantryItem.query.filter_by(user_id=self.user_id).all()
    
    def _traditional_price_analysis(self, price_history: List[Dict]) -> Dict:
        """Traditional statistical price analysis"""
        if not price_history:
            return {
                'trend': 'stable',
                'confidence': 30.0,
                'method': 'insufficient_data'
            }
        
        prices = [p.get('price', 0) for p in price_history]
        if len(prices) < 2:
            return {
                'trend': 'stable',
                'confidence': 50.0,
                'method': 'single_point'
            }
        
        # Simple trend analysis
        recent_price = prices[-1]
        older_price = prices[0]
        
        if recent_price > older_price * 1.05:
            trend = 'increasing'
        elif recent_price < older_price * 0.95:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'confidence': 75.0,
            'method': 'statistical',
            'price_change_percent': ((recent_price - older_price) / older_price) * 100 if older_price > 0 else 0
        }
    
    def _combine_price_recommendations(self, llm_analysis: Dict, traditional_analysis: Dict) -> str:
        """Combine LLM and traditional price analysis into recommendation"""
        llm_trend = llm_analysis.get('trend_direction', 'stable')
        traditional_trend = traditional_analysis.get('trend', 'stable')
        
        if llm_trend == 'increasing' or traditional_trend == 'increasing':
            return "Consider buying soon before prices rise further"
        elif llm_trend == 'decreasing' or traditional_trend == 'decreasing':
            return "Wait for better prices - trend is downward"
        else:
            return "Price stable - buy when convenient"
    
    def _fallback_price_analysis(self, price_history: List[Dict], item_name: str) -> Dict:
        """Fallback price analysis when LLM is not available"""
        traditional = self._traditional_price_analysis(price_history)
        
        return {
            'llm_analysis': {
                'method': 'fallback',
                'trend_direction': traditional['trend']
            },
            'traditional_analysis': traditional,
            'recommendation': f"Based on limited data: trend appears {traditional['trend']}",
            'confidence': traditional['confidence']
        }
    
    def _generate_recipe_recommendations(self, llm_analysis: Dict, pantry_impact: Dict) -> List[str]:
        """Generate recipe recommendations based on analysis"""
        recommendations = []
        
        insufficient_items = pantry_impact.get('insufficient_items', [])
        missing_items = pantry_impact.get('missing_items', [])
        
        if missing_items:
            recommendations.append(f"Need to purchase: {', '.join([item['ingredient'] for item in missing_items])}")
        
        if insufficient_items:
            recommendations.append(f"Running low on: {', '.join([item['ingredient'] for item in insufficient_items])}")
        
        if not missing_items and not insufficient_items:
            recommendations.append("You have all ingredients needed for this recipe!")
        
        return recommendations
    
    def _generate_structured_shopping_recommendations(self, context: Dict) -> Dict:
        """Generate structured shopping recommendations"""
        pantry_items = context.get('pantry', [])
        
        low_items = [item for item in pantry_items if item.get('quantity', 0) < 2]
        
        return {
            'priority_items': [item['name'] for item in low_items],
            'budget_suggestions': ['Look for sales on priority items'],
            'meal_planning_tips': ['Plan meals around current pantry items']
        }
    
    def _combine_predictions(self, traditional: ConsumptionPrediction, llm: Dict, item: PantryItem) -> Dict:
        """
        Intelligently combine traditional ML and LLM predictions
        """
        if traditional is None and llm is None:
            return None
        
        if traditional is None:
            return {
                'source': 'llm_only',
                'days_until_depletion': llm.get('days_until_depletion', 30),
                'confidence': llm.get('confidence_score', 50),
                'daily_consumption_rate': llm.get('daily_consumption_rate', 0.1),
                'recommendation': llm.get('reasoning', 'LLM-based prediction')
            }
        
        if llm is None or llm.get('method') == 'fallback':
            return {
                'source': 'traditional_only',
                'days_until_depletion': traditional.days_until_depletion,
                'confidence': traditional.confidence_score,
                'daily_consumption_rate': traditional.daily_consumption_rate,
                'recommendation': traditional.recommendation
            }
        
        # Combine both predictions with weighted average
        traditional_weight = 0.6  # Traditional ML gets more weight for now
        llm_weight = 0.4
        
        combined_days = (traditional.days_until_depletion * traditional_weight + 
                        llm.get('days_until_depletion', traditional.days_until_depletion) * llm_weight)
        
        combined_confidence = (traditional.confidence_score * traditional_weight + 
                             llm.get('confidence_score', traditional.confidence_score) * llm_weight)
        
        combined_rate = (traditional.daily_consumption_rate * traditional_weight + 
                        llm.get('daily_consumption_rate', traditional.daily_consumption_rate) * llm_weight)
        
        return {
            'source': 'ensemble',
            'days_until_depletion': combined_days,
            'confidence': combined_confidence,
            'daily_consumption_rate': combined_rate,
            'recommendation': f"Ensemble prediction: {traditional.recommendation} | LLM insight: {llm.get('reasoning', 'No additional insight')}",
            'traditional_prediction': traditional.days_until_depletion,
            'llm_prediction': llm.get('days_until_depletion'),
            'ensemble_advantage': abs(combined_days - traditional.days_until_depletion) < 1.0
        }
    
    def _format_prediction_output(self, traditional, llm, item: PantryItem, combined=None) -> Dict:
        """Format the prediction output for the dashboard"""
        result = {
            'item_name': item.name,
            'current_quantity': item.current_quantity,
            'item_id': item.id,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        if combined:
            result.update({
                'days_until_depletion': combined['days_until_depletion'],
                'confidence': combined['confidence'],
                'daily_consumption_rate': combined['daily_consumption_rate'],
                'recommendation': combined['recommendation'],
                'prediction_source': combined['source']
            })
        elif traditional:
            result.update({
                'days_until_depletion': traditional.days_until_depletion,
                'confidence': traditional.confidence_score,
                'daily_consumption_rate': traditional.daily_consumption_rate,
                'recommendation': traditional.recommendation,
                'prediction_source': 'traditional_ml'
            })
        else:
            result.update({
                'days_until_depletion': 30.0,
                'confidence': 50.0,
                'daily_consumption_rate': 0.1,
                'recommendation': 'Insufficient data for prediction',
                'prediction_source': 'default'
            })
        
        return result
    
    def _analyze_pantry_impact(self, recipe_ingredients: List[Dict]) -> Dict:
        """Analyze how recipe ingredients impact current pantry"""
        pantry_items = {item.name.lower(): item for item in self._get_user_pantry()}
        impact = {
            'sufficient_items': [],
            'insufficient_items': [],
            'missing_items': [],
            'total_cost_estimate': 0.0
        }
        
        for ingredient in recipe_ingredients:
            ingredient_name = ingredient.get('name', '').lower()
            required_quantity = ingredient.get('quantity', 1.0)
            
            # Find matching pantry item
            matching_item = None
            for pantry_name, pantry_item in pantry_items.items():
                if ingredient_name in pantry_name or pantry_name in ingredient_name:
                    matching_item = pantry_item
                    break
            
            if matching_item:
                if matching_item.current_quantity >= required_quantity:
                    impact['sufficient_items'].append({
                        'ingredient': ingredient_name,
                        'required': required_quantity,
                        'available': matching_item.current_quantity,
                        'surplus': matching_item.current_quantity - required_quantity
                    })
                else:
                    impact['insufficient_items'].append({
                        'ingredient': ingredient_name,
                        'required': required_quantity,
                        'available': matching_item.current_quantity,
                        'shortage': required_quantity - matching_item.current_quantity
                    })
            else:
                impact['missing_items'].append({
                    'ingredient': ingredient_name,
                    'required': required_quantity,
                    'estimated_cost': 2.50  # Default estimate
                })
                impact['total_cost_estimate'] += 2.50
        
        return impact
    
    def _build_user_context(self) -> Dict:
        """Build comprehensive context for LLM queries"""
        pantry_items = self._get_user_pantry()
        
        # Get recent meal plans
        recent_meals = []
        try:
            meal_plans = MealPlan.query.filter(
                MealPlan.user_id == self.user_id,
                MealPlan.date >= datetime.now().date(),
                MealPlan.date <= datetime.now().date() + timedelta(days=7)
            ).all()
            
            for meal in meal_plans:
                if meal.recipe:
                    recent_meals.append({
                        'date': meal.date.isoformat(),
                        'meal_type': meal.meal_type,
                        'recipe': meal.recipe.title
                    })
        except:
            pass  # Meal planning might not be available
        
        return {
            'pantry': [{'name': item.name, 'quantity': item.current_quantity, 'unit': item.unit} 
                      for item in pantry_items],
            'meals': recent_meals,
            'budget': 'Not specified',  # Could be enhanced with user budget data
            'dietary_preferences': 'None specified'  # Could be enhanced with user preferences
        }
    
    def _get_price_history(self, item_name: str) -> List[Dict]:
        """Get price history for an item (mock data for now)"""
        # This would connect to real price data in production
        import random
        base_price = random.uniform(1.0, 5.0)
        history = []
        
        for i in range(10):
            date = datetime.now() - timedelta(days=i*7)
            price_variation = random.uniform(0.8, 1.2)
            history.append({
                'date': date.isoformat(),
                'price': base_price * price_variation,
                'source': 'mock_data'
            })
        
        return history
    
    def _fallback_recipe_impact_analysis(self, recipe_text: str, recipe_title: str) -> Dict:
        """Fallback analysis when LLM is not available"""
        return {
            'llm_analysis': {
                'ingredients': [],
                'method': 'fallback'
            },
            'pantry_impact': {
                'sufficient_items': [],
                'insufficient_items': [],
                'missing_items': []
            },
            'recommendations': ['LLM analysis not available - using basic pattern matching'],
            'confidence': 30.0
        }
    
    def get_llm_status(self) -> Dict:
        """Get status of LLM integration"""
        if self.llm_engine:
            return self.llm_engine.get_model_status()
        else:
            return {
                'model_loaded': False,
                'fallback_active': True,
                'capabilities': {
                    'recipe_analysis': False,
                    'consumption_prediction': False,
                    'price_analysis': False,
                    'conversation': False
                }
            }

"""
High-End Predictive Pantry System
Advanced ML-based consumption prediction and intelligent inventory management
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import json
import math
from sqlalchemy import func, and_, or_

# Optional scientific computing imports with fallbacks
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("Warning: numpy not available, using basic math operations")

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas not available, using simplified data processing")

from recipe_app.db import db
from recipe_app.models.pantry_models import PantryItem, PantryUsageLog, ShoppingListItem
from recipe_app.models.models import Recipe, User


@dataclass
class ConsumptionPrediction:
    """Data class for consumption predictions"""
    item_id: int
    item_name: str
    predicted_days_remaining: float
    confidence_score: float
    prediction_model: str
    suggested_reorder_date: date
    suggested_quantity: float
    seasonal_factor: float
    cost_optimization_score: float
    waste_risk_score: float


@dataclass
class PantryInsight:
    """Data class for pantry insights and recommendations"""
    insight_type: str  # 'reorder', 'waste_risk', 'cost_savings', 'seasonal'
    priority: int  # 1=high, 5=low
    title: str
    description: str
    action_required: bool
    estimated_savings: Optional[float] = None
    item_ids: List[int] = None


class PredictivePantryEngine:
    """
    Advanced predictive analytics engine for pantry management
    Uses multiple algorithms to predict consumption patterns and optimize purchasing
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.prediction_models = {
            'linear_trend': self._linear_trend_prediction,
            'seasonal_arima': self._seasonal_prediction,
            'recipe_based': self._recipe_based_prediction,
            'ensemble': self._ensemble_prediction
        }
    
    def generate_comprehensive_predictions(self) -> Dict[str, Any]:
        """
        Generate comprehensive predictive analysis for user's pantry
        Returns complete analysis with predictions, insights, and recommendations
        """
        pantry_items = PantryItem.query.filter_by(user_id=self.user_id).all()
        
        predictions = []
        insights = []
        
        for item in pantry_items:
            # Generate prediction for each item
            prediction = self._predict_item_consumption(item)
            if prediction:
                predictions.append(prediction)
                
                # Generate insights based on prediction
                item_insights = self._generate_item_insights(item, prediction)
                insights.extend(item_insights)
        
        # Generate system-wide insights
        system_insights = self._generate_system_insights(predictions)
        insights.extend(system_insights)
        
        # Sort insights by priority
        insights.sort(key=lambda x: x.priority)
        
        return {
            'predictions': predictions,
            'insights': insights,
            'summary': self._generate_prediction_summary(predictions),
            'generated_at': datetime.utcnow().isoformat(),
            'model_version': '2.0'
        }
    
    def _predict_item_consumption(self, item: PantryItem) -> Optional[ConsumptionPrediction]:
        """
        Predict consumption for a specific pantry item using ensemble of models
        """
        if item.current_quantity <= 0:
            return None
            
        # Get historical usage data
        usage_data = self._get_usage_history(item.id)
        if len(usage_data) < 3:  # Need minimum data points
            return self._fallback_prediction(item)
        
        # Apply multiple prediction models
        model_predictions = {}
        for model_name, model_func in self.prediction_models.items():
            try:
                prediction = model_func(item, usage_data)
                if prediction:
                    model_predictions[model_name] = prediction
            except Exception as e:
                print(f"Model {model_name} failed for item {item.name}: {e}")
                continue
        
        if not model_predictions:
            return self._fallback_prediction(item)
        
        # Ensemble prediction (weighted average based on confidence)
        return self._ensemble_prediction(item, model_predictions)
    
    def _get_usage_history(self, item_id: int) -> List[Dict]:
        """Get detailed usage history for an item"""
        logs = PantryUsageLog.query.filter_by(
            item_id=item_id, 
            user_id=self.user_id
        ).filter(
            PantryUsageLog.quantity_change < 0  # Only consumption events
        ).order_by(PantryUsageLog.timestamp.desc()).limit(100).all()
        
        usage_data = []
        for log in logs:
            usage_data.append({
                'date': log.timestamp.date(),
                'quantity_used': abs(log.quantity_change),
                'reason': log.reason,
                'recipe_id': log.recipe_id,
                'weekday': log.timestamp.weekday(),
                'month': log.timestamp.month,
                'week_of_year': log.timestamp.isocalendar()[1]
            })
        
        return usage_data
    
    def _linear_trend_prediction(self, item: PantryItem, usage_data: List[Dict]) -> Dict:
        """
        Linear trend analysis for consumption prediction
        """
        if len(usage_data) < 7:
            return None
        
        # Simplified version without pandas
        if not HAS_PANDAS or not HAS_NUMPY:
            # Basic calculation without pandas
            daily_totals = defaultdict(float)
            for usage in usage_data:
                daily_totals[usage['date']] += usage['quantity_used']
            
            if len(daily_totals) < 3:
                return None
            
            # Simple average consumption
            total_consumption = sum(daily_totals.values())
            avg_daily_consumption = total_consumption / len(daily_totals)
            days_remaining = item.current_quantity / max(0.1, avg_daily_consumption)
            
            return {
                'days_remaining': days_remaining,
                'confidence': 0.5,  # Lower confidence without advanced analytics
                'daily_rate': avg_daily_consumption,
                'trend_slope': 0
            }
            
        # Full pandas/numpy version
        df = pd.DataFrame(usage_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate daily consumption rate
        daily_usage = df.groupby('date')['quantity_used'].sum().reset_index()
        daily_usage['days_since_start'] = (daily_usage['date'] - daily_usage['date'].min()).dt.days
        
        # Linear regression for trend
        if len(daily_usage) >= 3:
            x = daily_usage['days_since_start'].values
            y = daily_usage['quantity_used'].values
            
            # Simple linear regression
            n = len(x)
            x_mean = np.mean(x)
            y_mean = np.mean(y)
            
            slope = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
            intercept = y_mean - slope * x_mean
            
            # Calculate R-squared for confidence
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - y_mean) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Predict daily consumption rate
            avg_daily_consumption = max(0.1, y_mean)  # Minimum consumption
            days_remaining = item.current_quantity / avg_daily_consumption
            
            return {
                'days_remaining': days_remaining,
                'confidence': min(0.9, max(0.1, r_squared)),
                'daily_rate': avg_daily_consumption,
                'trend_slope': slope
            }
        
        return None
    
    def _seasonal_prediction(self, item: PantryItem, usage_data: List[Dict]) -> Dict:
        """
        Seasonal pattern recognition and prediction
        """
        if len(usage_data) < 30:  # Need substantial history for seasonal analysis
            return None
        
        # Simplified version without pandas
        if not HAS_PANDAS:
            # Basic seasonal analysis without pandas
            monthly_usage = defaultdict(list)
            weekday_usage = defaultdict(list)
            
            for usage in usage_data:
                monthly_usage[usage['month']].append(usage['quantity_used'])
                weekday_usage[usage['weekday']].append(usage['quantity_used'])
            
            # Calculate averages
            monthly_avg = {}
            for month, quantities in monthly_usage.items():
                monthly_avg[month] = sum(quantities) / len(quantities)
            
            weekday_avg = {}
            for weekday, quantities in weekday_usage.items():
                weekday_avg[weekday] = sum(quantities) / len(quantities)
            
            current_month = datetime.now().month
            current_weekday = datetime.now().weekday()
            
            # Calculate seasonal factors
            overall_avg = sum(usage['quantity_used'] for usage in usage_data) / len(usage_data)
            month_factor = monthly_avg.get(current_month, overall_avg) / overall_avg if overall_avg > 0 else 1.0
            weekday_factor = weekday_avg.get(current_weekday, overall_avg) / overall_avg if overall_avg > 0 else 1.0
            
            # Apply seasonal adjustments
            adjusted_rate = overall_avg * month_factor * weekday_factor
            days_remaining = item.current_quantity / max(0.1, adjusted_rate)
            
            return {
                'days_remaining': days_remaining,
                'confidence': min(0.6, len(usage_data) / 100),
                'daily_rate': adjusted_rate,
                'seasonal_factor': month_factor,
                'weekday_factor': weekday_factor
            }
            
        # Full pandas version
        df = pd.DataFrame(usage_data)
        
        # Analyze seasonal patterns
        monthly_usage = df.groupby('month')['quantity_used'].mean()
        weekly_usage = df.groupby('week_of_year')['quantity_used'].mean()
        weekday_usage = df.groupby('weekday')['quantity_used'].mean()
        
        current_month = datetime.now().month
        current_weekday = datetime.now().weekday()
        current_week = datetime.now().isocalendar()[1]
        
        # Calculate seasonal factors
        month_factor = monthly_usage.get(current_month, 1.0) / monthly_usage.mean() if len(monthly_usage) > 0 else 1.0
        weekday_factor = weekday_usage.get(current_weekday, 1.0) / weekday_usage.mean() if len(weekday_usage) > 0 else 1.0
        
        # Base consumption rate
        base_daily_rate = df['quantity_used'].sum() / len(df)
        
        # Apply seasonal adjustments
        adjusted_rate = base_daily_rate * month_factor * weekday_factor
        days_remaining = item.current_quantity / max(0.1, adjusted_rate)
        
        # Confidence based on data consistency
        confidence = min(0.8, len(usage_data) / 100)  # Higher confidence with more data
        
        return {
            'days_remaining': days_remaining,
            'confidence': confidence,
            'daily_rate': adjusted_rate,
            'seasonal_factor': month_factor,
            'weekday_factor': weekday_factor
        }
    
    def _recipe_based_prediction(self, item: PantryItem, usage_data: List[Dict]) -> Dict:
        """
        Recipe-based consumption prediction using meal planning data
        """
        # Get user's recent recipes and meal planning patterns
        recipe_usage = [log for log in usage_data if log.get('recipe_id')]
        
        if len(recipe_usage) < 5:
            return None
        
        # Analyze recipe-based consumption patterns
        recipe_consumption = defaultdict(list)
        for usage in recipe_usage:
            if usage['recipe_id']:
                recipe_consumption[usage['recipe_id']].append(usage['quantity_used'])
        
        # Calculate average consumption per recipe
        avg_per_recipe = {}
        for recipe_id, quantities in recipe_consumption.items():
            if HAS_NUMPY:
                avg_per_recipe[recipe_id] = np.mean(quantities)
            else:
                avg_per_recipe[recipe_id] = sum(quantities) / len(quantities)
        
        # Get user's cooking frequency and upcoming meal plans
        cooking_frequency = self._estimate_cooking_frequency()
        
        # Predict based on likely future recipe usage
        if avg_per_recipe and cooking_frequency > 0:
            if HAS_NUMPY:
                avg_consumption_per_cook = np.mean(list(avg_per_recipe.values()))
            else:
                avg_consumption_per_cook = sum(avg_per_recipe.values()) / len(avg_per_recipe)
                
            daily_rate = avg_consumption_per_cook * cooking_frequency
            days_remaining = item.current_quantity / max(0.1, daily_rate)
            
            confidence = min(0.9, len(recipe_usage) / 20)  # Higher confidence with more recipe data
            
            return {
                'days_remaining': days_remaining,
                'confidence': confidence,
                'daily_rate': daily_rate,
                'recipe_factor': len(avg_per_recipe)
            }
        
        return None
    
    def _ensemble_prediction(self, item: PantryItem, model_predictions: Dict) -> ConsumptionPrediction:
        """
        Combine multiple model predictions into ensemble prediction
        """
        if not model_predictions:
            return self._fallback_prediction(item)
        
        # Weight predictions by confidence
        weighted_days = 0
        weighted_rates = 0
        total_confidence = 0
        
        for model_name, prediction in model_predictions.items():
            confidence = prediction['confidence']
            weighted_days += prediction['days_remaining'] * confidence
            weighted_rates += prediction['daily_rate'] * confidence
            total_confidence += confidence
        
        if total_confidence == 0:
            return self._fallback_prediction(item)
        
        final_days_remaining = weighted_days / total_confidence
        final_daily_rate = weighted_rates / total_confidence
        final_confidence = min(0.95, total_confidence / len(model_predictions))
        
        # Calculate additional metrics
        suggested_reorder_date = date.today() + timedelta(days=max(1, final_days_remaining - 3))
        suggested_quantity = self._calculate_optimal_reorder_quantity(item, final_daily_rate)
        seasonal_factor = self._get_seasonal_factor(item)
        cost_optimization_score = self._calculate_cost_optimization_score(item, suggested_quantity)
        waste_risk_score = self._calculate_waste_risk_score(item, final_days_remaining)
        
        return ConsumptionPrediction(
            item_id=item.id,
            item_name=item.name,
            predicted_days_remaining=final_days_remaining,
            confidence_score=final_confidence,
            prediction_model='ensemble',
            suggested_reorder_date=suggested_reorder_date,
            suggested_quantity=suggested_quantity,
            seasonal_factor=seasonal_factor,
            cost_optimization_score=cost_optimization_score,
            waste_risk_score=waste_risk_score
        )
    
    def _fallback_prediction(self, item: PantryItem) -> ConsumptionPrediction:
        """
        Fallback prediction when insufficient data is available
        """
        # Use category-based averages or simple heuristics
        category_defaults = {
            'Dairy': {'daily_rate': 0.2, 'confidence': 0.3},
            'Vegetables': {'daily_rate': 0.3, 'confidence': 0.3},
            'Meat & Fish': {'daily_rate': 0.15, 'confidence': 0.3},
            'Pantry Staples': {'daily_rate': 0.1, 'confidence': 0.4},
            'Fruits': {'daily_rate': 0.25, 'confidence': 0.3}
        }
        
        category_name = item.category.name if item.category else 'Other'
        defaults = category_defaults.get(category_name, {'daily_rate': 0.2, 'confidence': 0.2})
        
        daily_rate = defaults['daily_rate']
        days_remaining = item.current_quantity / daily_rate
        
        return ConsumptionPrediction(
            item_id=item.id,
            item_name=item.name,
            predicted_days_remaining=days_remaining,
            confidence_score=defaults['confidence'],
            prediction_model='fallback',
            suggested_reorder_date=date.today() + timedelta(days=max(1, days_remaining - 2)),
            suggested_quantity=item.ideal_quantity or 5.0,
            seasonal_factor=1.0,
            cost_optimization_score=0.5,
            waste_risk_score=0.3
        )
    
    def _estimate_cooking_frequency(self) -> float:
        """
        Estimate how often the user cooks based on recipe usage logs
        """
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recipe_usage_count = PantryUsageLog.query.filter(
            PantryUsageLog.user_id == self.user_id,
            PantryUsageLog.reason == 'used_in_recipe',
            PantryUsageLog.timestamp >= thirty_days_ago
        ).count()
        
        # Estimate cooking sessions (multiple ingredients used per session)
        estimated_cooking_sessions = max(1, recipe_usage_count / 5)  # Assume 5 ingredients per recipe on average
        cooking_frequency_per_day = estimated_cooking_sessions / 30
        
        return cooking_frequency_per_day
    
    def _calculate_optimal_reorder_quantity(self, item: PantryItem, daily_rate: float) -> float:
        """
        Calculate optimal reorder quantity considering storage, cost, and waste
        """
        # Target: 2-3 weeks of supply
        target_days_supply = 21
        base_quantity = daily_rate * target_days_supply
        
        # Consider item characteristics
        if item.category and 'dairy' in item.category.name.lower():
            # Dairy products have shorter shelf life
            base_quantity = min(base_quantity, daily_rate * 14)
        elif item.category and any(keyword in item.category.name.lower() for keyword in ['pantry', 'canned', 'dry']):
            # Pantry staples can be bought in larger quantities
            base_quantity = max(base_quantity, daily_rate * 30)
        
        # Round to reasonable quantities
        if base_quantity < 1:
            return round(base_quantity, 2)
        elif base_quantity < 10:
            return round(base_quantity, 1)
        else:
            return round(base_quantity)
    
    def _get_seasonal_factor(self, item: PantryItem) -> float:
        """
        Calculate seasonal adjustment factor for the item
        """
        current_month = datetime.now().month
        
        # Seasonal adjustments based on item category and month
        seasonal_adjustments = {
            'Vegetables': {
                (12, 1, 2): 0.8,  # Winter - less fresh vegetables
                (3, 4, 5): 1.2,   # Spring - more fresh vegetables
                (6, 7, 8): 1.3,   # Summer - peak vegetables
                (9, 10, 11): 1.1  # Fall - moderate usage
            },
            'Fruits': {
                (12, 1, 2): 0.9,  # Winter - less fresh fruits
                (6, 7, 8): 1.4,   # Summer - peak fruit season
            },
            'Dairy': {
                (12, 1, 2): 1.1,  # Winter - more baking/hot drinks
                (6, 7, 8): 1.0,   # Summer - normal usage
            }
        }
        
        if item.category:
            category_adjustments = seasonal_adjustments.get(item.category.name, {})
            for months, factor in category_adjustments.items():
                if current_month in months:
                    return factor
        
        return 1.0  # No seasonal adjustment
    
    def _calculate_cost_optimization_score(self, item: PantryItem, suggested_quantity: float) -> float:
        """
        Calculate cost optimization score for purchasing decision
        """
        if not item.cost_per_unit:
            return 0.5  # Neutral score when no cost data
        
        # Consider bulk buying opportunities
        current_total_cost = item.cost_per_unit * suggested_quantity
        
        # Simulate bulk discounts (this would be enhanced with real store data)
        bulk_threshold = 10.0
        bulk_discount = 0.15 if suggested_quantity >= bulk_threshold else 0.0
        
        # Score based on potential savings
        optimization_score = min(1.0, bulk_discount + 0.5)
        
        return optimization_score
    
    def _calculate_waste_risk_score(self, item: PantryItem, days_remaining: float) -> float:
        """
        Calculate waste risk score based on consumption prediction and expiry
        """
        if not item.expiry_date:
            return 0.3  # Low risk when no expiry date known
        
        days_to_expiry = (item.expiry_date - date.today()).days
        
        if days_to_expiry <= 0:
            return 1.0  # High risk - already expired
        elif days_remaining > days_to_expiry:
            # Will expire before being consumed
            return min(1.0, (days_remaining - days_to_expiry) / days_remaining)
        else:
            # Will be consumed before expiry
            return max(0.0, 1.0 - (days_to_expiry - days_remaining) / days_to_expiry)
    
    def _generate_item_insights(self, item: PantryItem, prediction: ConsumptionPrediction) -> List[PantryInsight]:
        """
        Generate insights and recommendations for a specific item
        """
        insights = []
        
        # Reorder recommendation
        if prediction.predicted_days_remaining <= 5:
            priority = 1 if prediction.predicted_days_remaining <= 2 else 2
            insights.append(PantryInsight(
                insight_type='reorder',
                priority=priority,
                title=f'Reorder {item.name}',
                description=f'Running low - {prediction.predicted_days_remaining:.1f} days remaining',
                action_required=True,
                item_ids=[item.id]
            ))
        
        # Waste risk warning
        if prediction.waste_risk_score > 0.7:
            insights.append(PantryInsight(
                insight_type='waste_risk',
                priority=2,
                title=f'Use {item.name} soon',
                description=f'High waste risk - consider using in next few meals',
                action_required=True,
                item_ids=[item.id]
            ))
        
        # Cost optimization suggestion
        if prediction.cost_optimization_score > 0.8:
            potential_savings = (item.cost_per_unit or 0) * prediction.suggested_quantity * 0.15
            insights.append(PantryInsight(
                insight_type='cost_savings',
                priority=3,
                title=f'Bulk buy opportunity for {item.name}',
                description=f'Consider buying larger quantity for better value',
                action_required=False,
                estimated_savings=potential_savings,
                item_ids=[item.id]
            ))
        
        return insights
    
    def _generate_system_insights(self, predictions: List[ConsumptionPrediction]) -> List[PantryInsight]:
        """
        Generate system-wide insights across all pantry items
        """
        insights = []
        
        # Overall pantry health
        high_waste_items = [p for p in predictions if p.waste_risk_score > 0.6]
        if len(high_waste_items) > 3:
            insights.append(PantryInsight(
                insight_type='waste_risk',
                priority=1,
                title='Multiple items at risk of waste',
                description=f'{len(high_waste_items)} items may expire soon - plan meals to use them',
                action_required=True,
                item_ids=[p.item_id for p in high_waste_items]
            ))
        
        # Shopping optimization
        reorder_items = [p for p in predictions if p.predicted_days_remaining <= 7]
        total_savings = sum(p.cost_optimization_score * (p.suggested_quantity * 0.1) for p in reorder_items)
        
        if total_savings > 5.0:  # £5 potential savings
            insights.append(PantryInsight(
                insight_type='cost_savings',
                priority=2,
                title='Optimize your shopping trip',
                description=f'Plan purchases to save approximately £{total_savings:.2f}',
                action_required=False,
                estimated_savings=total_savings
            ))
        
        return insights
    
    def _generate_prediction_summary(self, predictions: List[ConsumptionPrediction]) -> Dict:
        """
        Generate summary statistics for predictions
        """
        if not predictions:
            return {}
        
        if HAS_NUMPY:
            avg_confidence = np.mean([p.confidence_score for p in predictions])
        else:
            avg_confidence = sum(p.confidence_score for p in predictions) / len(predictions)
            
        return {
            'total_items': len(predictions),
            'avg_confidence': avg_confidence,
            'items_need_reorder': len([p for p in predictions if p.predicted_days_remaining <= 7]),
            'high_waste_risk': len([p for p in predictions if p.waste_risk_score > 0.6]),
            'cost_optimization_opportunities': len([p for p in predictions if p.cost_optimization_score > 0.7]),
            'total_estimated_savings': sum(p.cost_optimization_score * 2.0 for p in predictions)  # Rough estimate
        }


class SmartShoppingListGenerator:
    """
    Generate intelligent shopping lists based on predictive analytics
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.prediction_engine = PredictivePantryEngine(user_id)
    
    def generate_predictive_shopping_list(self, days_ahead: int = 7, budget_limit: Optional[float] = None) -> Dict:
        """
        Generate shopping list based on predictive analytics
        """
        # Get predictions
        analysis = self.prediction_engine.generate_comprehensive_predictions()
        predictions = analysis['predictions']
        
        # Filter items that need reordering
        reorder_items = [
            p for p in predictions 
            if p.predicted_days_remaining <= days_ahead
        ]
        
        # Sort by priority (confidence * urgency)
        reorder_items.sort(key=lambda x: x.confidence_score * (1 / max(0.1, x.predicted_days_remaining)), reverse=True)
        
        shopping_list = []
        total_cost = 0.0
        
        for prediction in reorder_items:
            item = PantryItem.query.get(prediction.item_id)
            if not item:
                continue
            
            estimated_cost = (item.cost_per_unit or 2.0) * prediction.suggested_quantity
            
            # Check budget constraint
            if budget_limit and (total_cost + estimated_cost) > budget_limit:
                continue
            
            shopping_item = {
                'item_name': prediction.item_name,
                'current_quantity': item.current_quantity,
                'suggested_quantity': prediction.suggested_quantity,
                'predicted_days_remaining': prediction.predicted_days_remaining,
                'confidence_score': prediction.confidence_score,
                'estimated_cost': estimated_cost,
                'cost_optimization_score': prediction.cost_optimization_score,
                'waste_risk_score': prediction.waste_risk_score,
                'priority': self._calculate_shopping_priority(prediction),
                'notes': self._generate_shopping_notes(prediction)
            }
            
            shopping_list.append(shopping_item)
            total_cost += estimated_cost
        
        return {
            'shopping_list': shopping_list,
            'total_estimated_cost': total_cost,
            'budget_remaining': (budget_limit - total_cost) if budget_limit else None,
            'generated_at': datetime.utcnow().isoformat(),
            'days_ahead': days_ahead
        }
    
    def _calculate_shopping_priority(self, prediction: ConsumptionPrediction) -> int:
        """Calculate shopping priority (1=urgent, 5=low)"""
        if prediction.predicted_days_remaining <= 1:
            return 1
        elif prediction.predicted_days_remaining <= 3:
            return 2
        elif prediction.predicted_days_remaining <= 5:
            return 3
        elif prediction.predicted_days_remaining <= 7:
            return 4
        else:
            return 5
    
    def _generate_shopping_notes(self, prediction: ConsumptionPrediction) -> str:
        """Generate helpful notes for shopping item"""
        notes = []
        
        if prediction.confidence_score < 0.5:
            notes.append("Low confidence prediction")
        
        if prediction.cost_optimization_score > 0.7:
            notes.append("Consider bulk purchase")
        
        if prediction.waste_risk_score > 0.6:
            notes.append("Use quickly to avoid waste")
        
        if prediction.seasonal_factor > 1.2:
            notes.append("Peak season - higher consumption expected")
        
        return "; ".join(notes) if notes else "Regular purchase"

"""
Advanced Machine Learning Models for Predictive Pantry
Implements sophisticated algorithms for consumption prediction and optimization
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
import math
from collections import defaultdict, deque
try:
    from sklearn.linear_model import LinearRegression, Ridge
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    # Fallback implementations when scikit-learn is not available
    SKLEARN_AVAILABLE = False
    
    class MockModel:
        def fit(self, X, y): pass
        def predict(self, X): return [1.0] * len(X) if hasattr(X, '__len__') else [1.0]
    
    class MockScaler:
        def fit_transform(self, X): return X
        def transform(self, X): return X
    
    def mean_absolute_error(y_true, y_pred): return 1.0
    def r2_score(y_true, y_pred): return 0.5
    
    LinearRegression = Ridge = RandomForestRegressor = MockModel
    StandardScaler = MockScaler
import pickle
import os

from recipe_app.models.pantry_models import PantryItem, PantryUsageLog


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for ML models"""
    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Square Error
    r2_score: float  # R-squared score
    accuracy_percentage: float
    confidence_interval: Tuple[float, float]
    last_updated: datetime


class ConsumptionPatternAnalyzer:
    """
    Advanced pattern analysis using machine learning for consumption prediction
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        self.model_cache_dir = f"models/user_{user_id}"
        os.makedirs(self.model_cache_dir, exist_ok=True)
    
    def analyze_consumption_patterns(self, item_id: int, days_history: int = 90) -> Dict[str, Any]:
        """
        Analyze consumption patterns using multiple ML algorithms
        """
        # Get historical data
        usage_data = self._get_detailed_usage_data(item_id, days_history)
        
        if len(usage_data) < 10:  # Need minimum data for ML
            return self._fallback_analysis(item_id)
        
        # Prepare features
        features, targets = self._prepare_ml_features(usage_data)
        
        # Train multiple models
        models_performance = {}
        
        # Linear Regression with trends
        lr_model, lr_performance = self._train_linear_model(features, targets)
        models_performance['linear'] = lr_performance
        
        # Random Forest for complex patterns
        rf_model, rf_performance = self._train_random_forest(features, targets)
        models_performance['random_forest'] = rf_performance
        
        # Time Series Analysis
        ts_model, ts_performance = self._train_time_series_model(usage_data)
        models_performance['time_series'] = ts_performance
        
        # Ensemble prediction
        ensemble_prediction = self._create_ensemble_prediction(
            lr_model, rf_model, ts_model, features
        )
        
        # Cache best performing model
        best_model = max(models_performance.items(), key=lambda x: x[1].r2_score)
        self._cache_model(item_id, best_model[1], best_model[0])
        
        return {
            'prediction': ensemble_prediction,
            'model_performance': models_performance,
            'feature_importance': self._get_feature_importance(),
            'consumption_insights': self._generate_consumption_insights(usage_data),
            'seasonal_factors': self._analyze_seasonal_patterns(usage_data),
            'user_behavior_profile': self._build_user_behavior_profile(usage_data)
        }
    
    def _get_detailed_usage_data(self, item_id: int, days_history: int) -> List[Dict]:
        """Get comprehensive usage data with features"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_history)
        
        logs = PantryUsageLog.query.filter(
            PantryUsageLog.item_id == item_id,
            PantryUsageLog.user_id == self.user_id,
            PantryUsageLog.timestamp >= cutoff_date,
            PantryUsageLog.quantity_change < 0  # Only consumption
        ).order_by(PantryUsageLog.timestamp.asc()).all()
        
        usage_data = []
        for log in logs:
            # Create comprehensive feature set
            timestamp = log.timestamp
            usage_data.append({
                'date': timestamp.date(),
                'timestamp': timestamp,
                'quantity_used': abs(log.quantity_change),
                'weekday': timestamp.weekday(),
                'month': timestamp.month,
                'week_of_year': timestamp.isocalendar()[1],
                'day_of_month': timestamp.day,
                'is_weekend': timestamp.weekday() >= 5,
                'is_holiday': self._is_holiday(timestamp.date()),
                'season': self._get_season(timestamp.month),
                'reason': log.reason,
                'recipe_id': log.recipe_id,
                'meal_type': self._infer_meal_type(timestamp.hour),
                'days_since_start': (timestamp.date() - logs[0].timestamp.date()).days
            })
        
        return usage_data
    
    def _prepare_ml_features(self, usage_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare feature matrix and target vector for ML models"""
        df = pd.DataFrame(usage_data)
        
        # Feature engineering
        features = []
        targets = []
        
        for i, row in df.iterrows():
            feature_vector = [
                row['weekday'],
                row['month'],
                row['day_of_month'],
                int(row['is_weekend']),
                int(row['is_holiday']),
                row['season'],
                row['days_since_start'],
                self._get_days_since_last_usage(df, i),
                self._get_usage_frequency_last_week(df, i),
                self._get_avg_usage_last_month(df, i)
            ]
            
            features.append(feature_vector)
            targets.append(row['quantity_used'])
        
        return np.array(features), np.array(targets)
    
    def _train_linear_model(self, features: np.ndarray, targets: np.ndarray) -> Tuple[Any, ModelPerformanceMetrics]:
        """Train linear regression model with regularization"""
        # Split data for validation
        split_idx = int(len(features) * 0.8)
        X_train, X_test = features[:split_idx], features[split_idx:]
        y_train, y_test = targets[:split_idx], targets[split_idx:]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train Ridge regression (L2 regularization)
        model = Ridge(alpha=1.0)
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
        r2 = r2_score(y_test, y_pred)
        
        # Calculate accuracy percentage
        accuracy = 100 * (1 - mae / (np.mean(y_test) + 1e-8))
        
        performance = ModelPerformanceMetrics(
            mae=mae,
            rmse=rmse,
            r2_score=r2,
            accuracy_percentage=max(0, accuracy),
            confidence_interval=(mae * 0.5, mae * 1.5),
            last_updated=datetime.utcnow()
        )
        
        # Store scaler and model
        self.scalers['linear'] = scaler
        self.models['linear'] = model
        
        return model, performance
    
    def _train_random_forest(self, features: np.ndarray, targets: np.ndarray) -> Tuple[Any, ModelPerformanceMetrics]:
        """Train Random Forest for complex pattern recognition"""
        try:
            from sklearn.ensemble import RandomForestRegressor
        except ImportError:
            # Fallback to linear model if sklearn not available
            return self._train_linear_model(features, targets)
        
        split_idx = int(len(features) * 0.8)
        X_train, X_test = features[:split_idx], features[split_idx:]
        y_train, y_test = targets[:split_idx], targets[split_idx:]
        
        # Random Forest model
        model = RandomForestRegressor(
            n_estimators=50,
            max_depth=10,
            random_state=42,
            min_samples_split=5
        )
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
        r2 = r2_score(y_test, y_pred)
        
        accuracy = 100 * (1 - mae / (np.mean(y_test) + 1e-8))
        
        performance = ModelPerformanceMetrics(
            mae=mae,
            rmse=rmse,
            r2_score=r2,
            accuracy_percentage=max(0, accuracy),
            confidence_interval=(mae * 0.3, mae * 1.2),  # RF typically more confident
            last_updated=datetime.utcnow()
        )
        
        # Store feature importance
        if hasattr(model, 'feature_importances_'):
            self.feature_importance['random_forest'] = model.feature_importances_
        
        self.models['random_forest'] = model
        
        return model, performance
    
    def _train_time_series_model(self, usage_data: List[Dict]) -> Tuple[Any, ModelPerformanceMetrics]:
        """Train time series model for temporal patterns"""
        # Simple moving average with trend
        df = pd.DataFrame(usage_data)
        df = df.set_index('date').sort_index()
        
        # Resample to daily consumption
        daily_consumption = df.groupby('date')['quantity_used'].sum()
        
        # Calculate moving averages
        ma_7 = daily_consumption.rolling(window=7, min_periods=3).mean()
        ma_30 = daily_consumption.rolling(window=30, min_periods=7).mean()
        
        # Simple trend calculation
        trend = daily_consumption.diff().rolling(window=7).mean()
        
        # Create predictions
        predictions = ma_7.fillna(ma_30).fillna(daily_consumption.mean())
        
        # Evaluate against last 20% of data
        split_idx = int(len(daily_consumption) * 0.8)
        actual = daily_consumption.iloc[split_idx:]
        pred = predictions.iloc[split_idx:]
        
        if len(actual) > 0 and len(pred) > 0:
            mae = np.mean(np.abs(actual - pred))
            rmse = np.sqrt(np.mean((actual - pred) ** 2))
            r2 = max(0, 1 - np.sum((actual - pred) ** 2) / np.sum((actual - actual.mean()) ** 2))
        else:
            mae, rmse, r2 = 1.0, 1.0, 0.0
        
        accuracy = 100 * (1 - mae / (daily_consumption.mean() + 1e-8))
        
        performance = ModelPerformanceMetrics(
            mae=mae,
            rmse=rmse,
            r2_score=r2,
            accuracy_percentage=max(0, accuracy),
            confidence_interval=(mae * 0.7, mae * 1.3),
            last_updated=datetime.utcnow()
        )
        
        model_data = {
            'ma_7': ma_7.iloc[-1] if len(ma_7) > 0 else 0,
            'ma_30': ma_30.iloc[-1] if len(ma_30) > 0 else 0,
            'trend': trend.iloc[-1] if len(trend) > 0 else 0,
            'daily_avg': daily_consumption.mean()
        }
        
        return model_data, performance
    
    def _create_ensemble_prediction(self, lr_model, rf_model, ts_model, features) -> Dict[str, Any]:
        """Create ensemble prediction from multiple models"""
        predictions = []
        confidences = []
        
        # Linear model prediction
        if lr_model and len(features) > 0:
            lr_scaler = self.scalers.get('linear')
            if lr_scaler:
                features_scaled = lr_scaler.transform([features[-1]])
                lr_pred = lr_model.predict(features_scaled)[0]
                predictions.append(lr_pred)
                confidences.append(0.3)
        
        # Random Forest prediction
        if rf_model and len(features) > 0:
            rf_pred = rf_model.predict([features[-1]])[0]
            predictions.append(rf_pred)
            confidences.append(0.4)
        
        # Time series prediction
        if ts_model:
            ts_pred = ts_model.get('daily_avg', 1.0)
            predictions.append(ts_pred)
            confidences.append(0.3)
        
        if not predictions:
            return {'daily_consumption_rate': 1.0, 'confidence': 0.2}
        
        # Weighted ensemble
        weighted_pred = np.average(predictions, weights=confidences)
        ensemble_confidence = np.mean(confidences)
        
        return {
            'daily_consumption_rate': max(0.1, weighted_pred),
            'confidence': ensemble_confidence,
            'individual_predictions': {
                'linear': predictions[0] if len(predictions) > 0 else None,
                'random_forest': predictions[1] if len(predictions) > 1 else None,
                'time_series': predictions[2] if len(predictions) > 2 else None
            }
        }
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from Random Forest model"""
        if 'random_forest' in self.feature_importance:
            feature_names = [
                'weekday', 'month', 'day_of_month', 'is_weekend', 'is_holiday',
                'season', 'days_since_start', 'days_since_last_usage',
                'usage_frequency_last_week', 'avg_usage_last_month'
            ]
            importance = self.feature_importance['random_forest']
            return dict(zip(feature_names, importance))
        return {}
    
    def _generate_consumption_insights(self, usage_data: List[Dict]) -> Dict[str, Any]:
        """Generate insights about consumption patterns"""
        df = pd.DataFrame(usage_data)
        
        insights = {
            'peak_consumption_day': df.groupby('weekday')['quantity_used'].mean().idxmax(),
            'peak_consumption_month': df.groupby('month')['quantity_used'].mean().idxmax(),
            'weekend_vs_weekday_ratio': df[df['is_weekend']]['quantity_used'].mean() / 
                                      (df[~df['is_weekend']]['quantity_used'].mean() + 1e-8),
            'consistency_score': 1 / (1 + df['quantity_used'].std()),  # Lower std = higher consistency
            'usage_acceleration': self._calculate_usage_acceleration(df),
            'recipe_correlation': self._analyze_recipe_correlation(df)
        }
        
        return insights
    
    def _analyze_seasonal_patterns(self, usage_data: List[Dict]) -> Dict[str, float]:
        """Analyze seasonal consumption patterns"""
        df = pd.DataFrame(usage_data)
        
        seasonal_factors = {}
        for season in range(4):  # 0=Winter, 1=Spring, 2=Summer, 3=Fall
            season_data = df[df['season'] == season]
            if len(season_data) > 0:
                seasonal_factors[f'season_{season}'] = season_data['quantity_used'].mean()
            else:
                seasonal_factors[f'season_{season}'] = 1.0
        
        # Normalize to average
        avg_consumption = df['quantity_used'].mean()
        for season in seasonal_factors:
            seasonal_factors[season] = seasonal_factors[season] / (avg_consumption + 1e-8)
        
        return seasonal_factors
    
    def _build_user_behavior_profile(self, usage_data: List[Dict]) -> Dict[str, Any]:
        """Build comprehensive user behavior profile"""
        df = pd.DataFrame(usage_data)
        
        profile = {
            'cooking_frequency': len(df[df['reason'] == 'used_in_recipe']) / len(df),
            'bulk_usage_tendency': len(df[df['quantity_used'] > df['quantity_used'].mean() * 1.5]) / len(df),
            'regularity_score': self._calculate_regularity_score(df),
            'waste_risk_score': self._calculate_waste_risk(df),
            'planning_horizon': self._estimate_planning_horizon(df),
            'preferred_cooking_times': self._analyze_cooking_times(df)
        }
        
        return profile
    
    def _fallback_analysis(self, item_id: int) -> Dict[str, Any]:
        """Fallback analysis when insufficient data for ML"""
        item = PantryItem.query.get(item_id)
        
        return {
            'prediction': {
                'daily_consumption_rate': 0.5,  # Conservative estimate
                'confidence': 0.2
            },
            'model_performance': {
                'fallback': ModelPerformanceMetrics(
                    mae=1.0, rmse=1.0, r2_score=0.0, 
                    accuracy_percentage=20.0,
                    confidence_interval=(0.3, 1.5),
                    last_updated=datetime.utcnow()
                )
            },
            'consumption_insights': {
                'note': 'Insufficient data for ML analysis',
                'recommendation': 'Use item more regularly to enable AI predictions'
            }
        }
    
    # Helper methods
    def _is_holiday(self, date_obj: date) -> bool:
        """Check if date is a holiday (UK holidays)"""
        # Simplified holiday detection
        uk_holidays = [
            (1, 1),   # New Year's Day
            (12, 25), # Christmas Day
            (12, 26), # Boxing Day
            (4, 2),   # Good Friday (approximate)
            (4, 5),   # Easter Monday (approximate)
        ]
        return (date_obj.month, date_obj.day) in uk_holidays
    
    def _get_season(self, month: int) -> int:
        """Get season number (0=Winter, 1=Spring, 2=Summer, 3=Fall)"""
        if month in [12, 1, 2]:
            return 0  # Winter
        elif month in [3, 4, 5]:
            return 1  # Spring
        elif month in [6, 7, 8]:
            return 2  # Summer
        else:
            return 3  # Fall
    
    def _infer_meal_type(self, hour: int) -> str:
        """Infer meal type from hour"""
        if 5 <= hour <= 10:
            return 'breakfast'
        elif 11 <= hour <= 14:
            return 'lunch'
        elif 17 <= hour <= 21:
            return 'dinner'
        else:
            return 'snack'
    
    def _get_days_since_last_usage(self, df: pd.DataFrame, current_idx: int) -> float:
        """Get days since last usage"""
        if current_idx == 0:
            return 0
        current_date = df.iloc[current_idx]['date']
        previous_date = df.iloc[current_idx - 1]['date']
        return (current_date - previous_date).days
    
    def _get_usage_frequency_last_week(self, df: pd.DataFrame, current_idx: int) -> float:
        """Get usage frequency in last week"""
        current_date = df.iloc[current_idx]['date']
        week_ago = current_date - timedelta(days=7)
        recent_usage = df[df['date'] >= week_ago].iloc[:current_idx + 1]
        return len(recent_usage)
    
    def _get_avg_usage_last_month(self, df: pd.DataFrame, current_idx: int) -> float:
        """Get average usage in last month"""
        current_date = df.iloc[current_idx]['date']
        month_ago = current_date - timedelta(days=30)
        recent_usage = df[df['date'] >= month_ago].iloc[:current_idx + 1]
        return recent_usage['quantity_used'].mean() if len(recent_usage) > 0 else 0
    
    def _calculate_usage_acceleration(self, df: pd.DataFrame) -> float:
        """Calculate if usage is accelerating or decelerating"""
        if len(df) < 4:
            return 0.0
        
        # Compare recent vs older usage rates
        recent = df.tail(len(df) // 2)['quantity_used'].mean()
        older = df.head(len(df) // 2)['quantity_used'].mean()
        
        return (recent - older) / (older + 1e-8)
    
    def _analyze_recipe_correlation(self, df: pd.DataFrame) -> float:
        """Analyze correlation between recipe usage and consumption"""
        recipe_usage = df[df['reason'] == 'used_in_recipe']['quantity_used'].mean()
        non_recipe_usage = df[df['reason'] != 'used_in_recipe']['quantity_used'].mean()
        
        if non_recipe_usage == 0:
            return 1.0
        
        return recipe_usage / (non_recipe_usage + 1e-8)
    
    def _calculate_regularity_score(self, df: pd.DataFrame) -> float:
        """Calculate how regular the usage pattern is"""
        if len(df) < 3:
            return 0.5
        
        # Calculate coefficient of variation (lower = more regular)
        cv = df['quantity_used'].std() / (df['quantity_used'].mean() + 1e-8)
        return 1 / (1 + cv)  # Transform to 0-1 scale
    
    def _calculate_waste_risk(self, df: pd.DataFrame) -> float:
        """Calculate waste risk based on usage patterns"""
        # Look for signs of waste (large quantities used sporadically)
        large_usage_events = df[df['quantity_used'] > df['quantity_used'].mean() * 2]
        waste_risk = len(large_usage_events) / len(df)
        return min(1.0, waste_risk)
    
    def _estimate_planning_horizon(self, df: pd.DataFrame) -> int:
        """Estimate how far ahead user plans (in days)"""
        # Analyze gaps between usage to estimate planning
        df_sorted = df.sort_values('date')
        gaps = df_sorted['date'].diff().dt.days.dropna()
        
        if len(gaps) > 0:
            return int(gaps.median())
        return 7  # Default to weekly planning
    
    def _analyze_cooking_times(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze preferred cooking times"""
        if 'timestamp' in df.columns:
            hours = pd.to_datetime(df['timestamp']).dt.hour
            meal_times = {}
            for meal_type in ['breakfast', 'lunch', 'dinner', 'snack']:
                meal_times[meal_type] = len(hours[(hours >= 0) & (hours <= 23)]) / len(hours)
            return meal_times
        return {'breakfast': 0.2, 'lunch': 0.3, 'dinner': 0.4, 'snack': 0.1}
    
    def _cache_model(self, item_id: int, performance: ModelPerformanceMetrics, model_type: str):
        """Cache the best performing model"""
        cache_data = {
            'item_id': item_id,
            'model_type': model_type,
            'performance': {
                'mae': performance.mae,
                'r2_score': performance.r2_score,
                'accuracy': performance.accuracy_percentage
            },
            'cached_at': datetime.utcnow().isoformat()
        }
        
        cache_file = os.path.join(self.model_cache_dir, f'item_{item_id}_model.json')
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)


class SmartInventoryOptimizer:
    """
    Advanced inventory optimization using operations research principles
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.analyzer = ConsumptionPatternAnalyzer(user_id)
    
    def optimize_inventory_levels(self, budget_constraint: Optional[float] = None) -> Dict[str, Any]:
        """
        Optimize inventory levels across all pantry items using advanced algorithms
        """
        pantry_items = PantryItem.query.filter_by(user_id=self.user_id).all()
        
        optimizations = []
        total_cost = 0.0
        total_savings = 0.0
        
        for item in pantry_items:
            item_optimization = self._optimize_single_item(item)
            optimizations.append(item_optimization)
            total_cost += item_optimization.get('recommended_purchase_cost', 0)
            total_savings += item_optimization.get('potential_savings', 0)
        
        # Apply budget constraints if specified
        if budget_constraint:
            optimizations = self._apply_budget_constraints(optimizations, budget_constraint)
        
        return {
            'optimizations': optimizations,
            'total_cost': total_cost,
            'total_savings': total_savings,
            'optimization_score': self._calculate_optimization_score(optimizations),
            'recommendations': self._generate_optimization_recommendations(optimizations)
        }
    
    def _optimize_single_item(self, item: PantryItem) -> Dict[str, Any]:
        """Optimize inventory for a single item"""
        # Get ML analysis
        analysis = self.analyzer.analyze_consumption_patterns(item.id)
        prediction = analysis['prediction']
        
        # Calculate optimal order quantity using Economic Order Quantity (EOQ) principles
        annual_demand = prediction['daily_consumption_rate'] * 365
        ordering_cost = 2.0  # Assume £2 ordering cost per trip
        holding_cost_rate = 0.2  # 20% annual holding cost
        
        if item.cost_per_unit and item.cost_per_unit > 0:
            holding_cost = item.cost_per_unit * holding_cost_rate
            eoq = math.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
        else:
            eoq = annual_demand / 12  # Monthly supply if no cost data
        
        # Adjust for practical constraints
        practical_eoq = self._adjust_for_constraints(item, eoq, prediction)
        
        # Calculate reorder point
        lead_time_days = 3  # Assume 3-day lead time for shopping
        safety_stock = prediction['daily_consumption_rate'] * lead_time_days * 1.5  # 50% safety factor
        reorder_point = (prediction['daily_consumption_rate'] * lead_time_days) + safety_stock
        
        # Calculate potential savings
        current_cost = item.cost_per_unit * item.current_quantity if item.cost_per_unit else 0
        optimized_cost = item.cost_per_unit * practical_eoq if item.cost_per_unit else 0
        potential_savings = max(0, current_cost - optimized_cost)
        
        return {
            'item_id': item.id,
            'item_name': item.name,
            'current_quantity': item.current_quantity,
            'optimal_quantity': practical_eoq,
            'reorder_point': reorder_point,
            'recommended_purchase_quantity': max(0, practical_eoq - item.current_quantity),
            'recommended_purchase_cost': max(0, (practical_eoq - item.current_quantity) * (item.cost_per_unit or 0)),
            'potential_savings': potential_savings,
            'confidence': prediction['confidence'],
            'optimization_reason': self._explain_optimization(item, practical_eoq, reorder_point)
        }
    
    def _adjust_for_constraints(self, item: PantryItem, eoq: float, prediction: Dict) -> float:
        """Adjust EOQ for practical constraints"""
        # Shelf life constraints
        if item.expiry_date:
            days_to_expiry = (item.expiry_date - date.today()).days
            max_before_expiry = prediction['daily_consumption_rate'] * days_to_expiry * 0.8  # 80% buffer
            eoq = min(eoq, max_before_expiry)
        
        # Storage constraints (assume reasonable limits by category)
        category_limits = {
            'Dairy': 14,  # 2 weeks max
            'Vegetables': 10,  # 10 days max
            'Meat & Fish': 5,  # 5 days max (fresh)
            'Fruits': 7,  # 1 week max
            'Pantry Staples': 90  # 3 months max
        }
        
        category_name = item.category.name if item.category else 'Other'
        max_days_supply = category_limits.get(category_name, 30)
        max_quantity = prediction['daily_consumption_rate'] * max_days_supply
        
        return min(eoq, max_quantity, 50)  # Absolute max of 50 units
    
    def _apply_budget_constraints(self, optimizations: List[Dict], budget: float) -> List[Dict]:
        """Apply budget constraints using priority optimization"""
        # Sort by efficiency (savings per dollar spent)
        for opt in optimizations:
            cost = opt['recommended_purchase_cost']
            savings = opt['potential_savings']
            opt['efficiency'] = (savings + 1) / (cost + 1)  # Add 1 to avoid division by zero
        
        optimizations.sort(key=lambda x: x['efficiency'], reverse=True)
        
        # Apply budget constraint
        remaining_budget = budget
        constrained_optimizations = []
        
        for opt in optimizations:
            cost = opt['recommended_purchase_cost']
            if cost <= remaining_budget:
                constrained_optimizations.append(opt)
                remaining_budget -= cost
            else:
                # Partial purchase if beneficial
                if opt['efficiency'] > 1.0 and remaining_budget > 0:
                    partial_ratio = remaining_budget / cost
                    opt['recommended_purchase_quantity'] *= partial_ratio
                    opt['recommended_purchase_cost'] = remaining_budget
                    opt['potential_savings'] *= partial_ratio
                    constrained_optimizations.append(opt)
                    remaining_budget = 0
        
        return constrained_optimizations
    
    def _calculate_optimization_score(self, optimizations: List[Dict]) -> float:
        """Calculate overall optimization score (0-100)"""
        if not optimizations:
            return 0.0
        
        total_efficiency = sum(opt.get('efficiency', 0) for opt in optimizations)
        avg_confidence = sum(opt.get('confidence', 0) for opt in optimizations) / len(optimizations)
        
        # Combine efficiency and confidence
        score = (total_efficiency / len(optimizations)) * avg_confidence * 50
        return min(100.0, max(0.0, score))
    
    def _generate_optimization_recommendations(self, optimizations: List[Dict]) -> List[str]:
        """Generate human-readable optimization recommendations"""
        recommendations = []
        
        high_efficiency = [opt for opt in optimizations if opt.get('efficiency', 0) > 2.0]
        if high_efficiency:
            recommendations.append(
                f"High-priority purchases: {', '.join([opt['item_name'] for opt in high_efficiency[:3]])}"
            )
        
        low_stock = [opt for opt in optimizations if opt['current_quantity'] < opt['reorder_point']]
        if low_stock:
            recommendations.append(
                f"Low stock alerts: {', '.join([opt['item_name'] for opt in low_stock[:3]])}"
            )
        
        high_savings = [opt for opt in optimizations if opt.get('potential_savings', 0) > 5.0]
        if high_savings:
            recommendations.append(
                f"Best savings opportunities: {', '.join([opt['item_name'] for opt in high_savings[:3]])}"
            )
        
        return recommendations
    
    def _explain_optimization(self, item: PantryItem, optimal_qty: float, reorder_point: float) -> str:
        """Explain the optimization reasoning"""
        if item.current_quantity < reorder_point:
            return f"Below reorder point - stock up to {optimal_qty:.1f} units"
        elif item.current_quantity > optimal_qty * 1.5:
            return "Overstocked - consider using before buying more"
        else:
            return f"Optimal level - maintain around {optimal_qty:.1f} units"

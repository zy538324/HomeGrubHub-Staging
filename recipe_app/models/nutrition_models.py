"""
Nutrition tracking models for daily/weekly/monthly logging
"""
from datetime import datetime, date
from recipe_app.db import db


class NutritionEntry(db.Model):
    """Individual nutrition log entry (meal/snack)"""
    __tablename__ = 'nutrition_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), nullable=False, index=True)
    entry_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    entry_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Product information
    barcode = db.Column(db.String(50))
    product_name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100))
    
    # Portion information
    portion_size = db.Column(db.Float, nullable=False, default=100.0)  # grams
    servings = db.Column(db.Float, nullable=False, default=1.0)
    total_weight = db.Column(db.Float)  # calculated: portion_size * servings
    
    # Nutritional values (per total consumed amount)
    calories = db.Column(db.Float, default=0.0)
    protein = db.Column(db.Float, default=0.0)  # grams
    carbs = db.Column(db.Float, default=0.0)  # grams
    fat = db.Column(db.Float, default=0.0)  # grams
    fiber = db.Column(db.Float, default=0.0)  # grams
    sugar = db.Column(db.Float, default=0.0)  # grams
    sodium = db.Column(db.Float, default=0.0)  # mg
    cholesterol = db.Column(db.Float, default=0.0)  # mg
    saturated_fat = db.Column(db.Float, default=0.0)  # grams
    
    # Meal category
    meal_type = db.Column(db.String(20), default='snack')  # breakfast, lunch, dinner, snack
    
    # Additional metadata
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<NutritionEntry {self.product_name} - {self.entry_date}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'entry_date': self.entry_date.isoformat(),
            'entry_time': self.entry_time.isoformat(),
            'barcode': self.barcode,
            'product_name': self.product_name,
            'brand': self.brand,
            'portion_size': self.portion_size,
            'servings': self.servings,
            'total_weight': self.total_weight,
            'calories': self.calories,
            'protein': self.protein,
            'carbs': self.carbs,
            'fat': self.fat,
            'fiber': self.fiber,
            'sugar': self.sugar,
            'sodium': self.sodium,
            'cholesterol': self.cholesterol,
            'saturated_fat': self.saturated_fat,
            'meal_type': self.meal_type,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DailyNutritionSummary(db.Model):
    """Daily nutrition summary for quick access"""
    __tablename__ = 'daily_nutrition_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), nullable=False, index=True)
    summary_date = db.Column(db.Date, nullable=False, index=True)
    
    # Daily totals
    total_calories = db.Column(db.Float, default=0.0)
    total_protein = db.Column(db.Float, default=0.0)
    total_carbs = db.Column(db.Float, default=0.0)
    total_fat = db.Column(db.Float, default=0.0)
    total_fiber = db.Column(db.Float, default=0.0)
    total_sugar = db.Column(db.Float, default=0.0)
    total_sodium = db.Column(db.Float, default=0.0)
    total_cholesterol = db.Column(db.Float, default=0.0)
    total_saturated_fat = db.Column(db.Float, default=0.0)
    
    # Meal breakdown
    breakfast_calories = db.Column(db.Float, default=0.0)
    lunch_calories = db.Column(db.Float, default=0.0)
    dinner_calories = db.Column(db.Float, default=0.0)
    snack_calories = db.Column(db.Float, default=0.0)
    
    # Entry counts
    total_entries = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'summary_date', name='unique_user_date'),)
    
    def __repr__(self):
        return f'<DailyNutritionSummary {self.user_id} - {self.summary_date}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'summary_date': self.summary_date.isoformat(),
            'total_calories': self.total_calories,
            'total_protein': self.total_protein,
            'total_carbs': self.total_carbs,
            'total_fat': self.total_fat,
            'total_fiber': self.total_fiber,
            'total_sugar': self.total_sugar,
            'total_sodium': self.total_sodium,
            'total_cholesterol': self.total_cholesterol,
            'total_saturated_fat': self.total_saturated_fat,
            'breakfast_calories': self.breakfast_calories,
            'lunch_calories': self.lunch_calories,
            'dinner_calories': self.dinner_calories,
            'snack_calories': self.snack_calories,
            'total_entries': self.total_entries,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class NutritionGoal(db.Model):
    """User nutrition goals"""
    __tablename__ = 'nutrition_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(128), nullable=False, unique=True, index=True)
    
    # Daily goals
    daily_calories = db.Column(db.Float, default=2000.0)
    daily_protein = db.Column(db.Float, default=150.0)  # grams
    daily_carbs = db.Column(db.Float, default=250.0)  # grams
    daily_fat = db.Column(db.Float, default=65.0)  # grams
    daily_fiber = db.Column(db.Float, default=25.0)  # grams
    daily_sugar = db.Column(db.Float, default=50.0)  # grams (max)
    daily_sodium = db.Column(db.Float, default=2300.0)  # mg (max)
    daily_cholesterol = db.Column(db.Float, default=300.0)  # mg (max)
    
    # User profile for goal calculation
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))  # male, female, other
    height = db.Column(db.Float)  # cm
    weight = db.Column(db.Float)  # kg
    activity_level = db.Column(db.String(20), default='moderate')  # sedentary, light, moderate, active, very_active
    goal_type = db.Column(db.String(20), default='maintain')  # lose, maintain, gain
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<NutritionGoal {self.user_id}>'
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'daily_calories': self.daily_calories,
            'daily_protein': self.daily_protein,
            'daily_carbs': self.daily_carbs,
            'daily_fat': self.daily_fat,
            'daily_fiber': self.daily_fiber,
            'daily_sugar': self.daily_sugar,
            'daily_sodium': self.daily_sodium,
            'daily_cholesterol': self.daily_cholesterol,
            'age': self.age,
            'gender': self.gender,
            'height': self.height,
            'weight': self.weight,
            'activity_level': self.activity_level,
            'goal_type': self.goal_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def calculate_bmr(self):
        """Calculate Basal Metabolic Rate using Mifflin-St Jeor Equation"""
        if not all([self.age, self.gender, self.height, self.weight]):
            return None
            
        if self.gender.lower() == 'male':
            bmr = 88.362 + (13.397 * self.weight) + (4.799 * self.height) - (5.677 * self.age)
        else:  # female or other
            bmr = 447.593 + (9.247 * self.weight) + (3.098 * self.height) - (4.330 * self.age)
        
        return bmr
    
    def calculate_tdee(self):
        """Calculate Total Daily Energy Expenditure"""
        bmr = self.calculate_bmr()
        if not bmr:
            return None
            
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        
        multiplier = activity_multipliers.get(self.activity_level, 1.55)
        return bmr * multiplier

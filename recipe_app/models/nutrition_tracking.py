from flask_sqlalchemy import SQLAlchemy
from recipe_app.db import db
from datetime import datetime, date

class Food(db.Model):
    __tablename__ = 'foods'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    brand = db.Column(db.String(128), nullable=True)
    barcode = db.Column(db.String(64), nullable=True, index=True)
    calories = db.Column(db.Float, nullable=False)
    protein = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    serving_size = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'barcode': self.barcode,
            'calories': self.calories,
            'protein': self.protein,
            'carbs': self.carbs,
            'fat': self.fat,
            'serving_size': self.serving_size,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Meal(db.Model):
    __tablename__ = 'meals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    nutrition_log_id = db.Column(db.Integer, db.ForeignKey('nutrition_logs.id'), nullable=True, index=True)
    meal_type = db.Column(db.String(32), nullable=False) # breakfast, lunch, dinner, snack
    meal_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    foods = db.relationship('Food', secondary='meal_foods', lazy='subquery')
    total_calories = db.Column(db.Float, nullable=True)
    total_protein = db.Column(db.Float, nullable=True)
    total_carbs = db.Column(db.Float, nullable=True)
    total_fat = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'meal_type': self.meal_type,
            'meal_date': self.meal_date.isoformat(),
            'foods': [food.to_dict() for food in self.foods],
            'total_calories': self.total_calories,
            'total_protein': self.total_protein,
            'total_carbs': self.total_carbs,
            'total_fat': self.total_fat,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Association table for many-to-many relationship between Meal and Food
meal_foods = db.Table('meal_foods',
    db.Column('meal_id', db.Integer, db.ForeignKey('meals.id'), primary_key=True),
    db.Column('food_id', db.Integer, db.ForeignKey('foods.id'), primary_key=True)
)

class NutritionLog(db.Model):
    __tablename__ = 'nutrition_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    log_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    meals = db.relationship('Meal', backref='nutrition_log', lazy='dynamic', foreign_keys='Meal.nutrition_log_id')
    daily_calories = db.Column(db.Float, nullable=True)
    daily_protein = db.Column(db.Float, nullable=True)
    daily_carbs = db.Column(db.Float, nullable=True)
    daily_fat = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'log_date': self.log_date.isoformat(),
            'meals': [meal.to_dict() for meal in self.meals],
            'daily_calories': self.daily_calories,
            'daily_protein': self.daily_protein,
            'daily_carbs': self.daily_carbs,
            'daily_fat': self.daily_fat,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

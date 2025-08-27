#!/usr/bin/env python
"""
Database initialization script for advanced features
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from recipe_app.db import app, db
from recipe_app.models.models import *  # Import all models
from recipe_app.models.advanced_models import *  # Import advanced models
from recipe_app.models.fitness_models import *  # Import fitness models

def init_database():
    """Initialize the database with all tables"""
    
    with app.app_context():
        print("Creating database tables...")
        
        # Drop all tables if they exist (for clean setup)
        # db.drop_all()
        
        # Create all tables
        db.create_all()
        
        print("Database tables created successfully!")
        
        # Add some sample data
        from recipe_app.models.models import User
        
        # Check if admin user exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            from werkzeug.security import generate_password_hash
            admin_user = User(
                username='admin',
                email='admin@flavorio.com',
                password_hash=generate_password_hash('admin123'),
                current_plan='Pro',
                is_admin=True
            )
            db.session.add(admin_user)
            print("Created admin user (username: admin, password: admin123)")
        
        # Add sample equipment
        from recipe_app.advanced_models import Equipment
        equipment_list = [
            'Oven', 'Stovetop', 'Microwave', 'Blender', 'Food Processor',
            'Stand Mixer', 'Hand Mixer', 'Slow Cooker', 'Pressure Cooker',
            'Air Fryer', 'Grill', 'Cast Iron Pan', 'Non-stick Pan',
            'Baking Sheet', 'Roasting Pan', 'Mixing Bowls', 'Measuring Cups',
            'Kitchen Scale', 'Whisk', 'Spatula'
        ]
        
        for eq_name in equipment_list:
            if not Equipment.query.filter_by(name=eq_name).first():
                equipment = Equipment(
                    name=eq_name,
                    category='kitchen' if 'Pan' in eq_name or 'Bowl' in eq_name else 'appliance',
                    description=f"Essential kitchen {eq_name.lower()}"
                )
                db.session.add(equipment)
        
        # Add sample dietary restrictions
        from recipe_app.advanced_models import DietaryRestriction
        dietary_restrictions = [
            {'name': 'Vegetarian', 'description': 'No meat or fish'},
            {'name': 'Vegan', 'description': 'No animal products'},
            {'name': 'Gluten-Free', 'description': 'No gluten-containing ingredients'},
            {'name': 'Dairy-Free', 'description': 'No dairy products'},
            {'name': 'Nut-Free', 'description': 'No nuts or nut products'},
            {'name': 'Soy-Free', 'description': 'No soy products'},
            {'name': 'Low-Carb', 'description': 'Reduced carbohydrate content'},
            {'name': 'Keto', 'description': 'Ketogenic diet compatible'},
            {'name': 'Paleo', 'description': 'Paleolithic diet compatible'},
            {'name': 'Low-Sodium', 'description': 'Reduced sodium content'},
        ]
        
        for dr in dietary_restrictions:
            if not DietaryRestriction.query.filter_by(name=dr['name']).first():
                restriction = DietaryRestriction(
                    name=dr['name'],
                    description=dr['description']
                )
                db.session.add(restriction)
        
        try:
            db.session.commit()
            print("Sample data added successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding sample data: {e}")
        
        print("\nDatabase initialization complete!")
        print("You can now run the application with: python run.py")

if __name__ == '__main__':
    init_database()

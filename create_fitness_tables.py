#!/usr/bin/env python
"""
Script to create fitness tracking tables
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recipe_app.db import app, db
from recipe_app.models.fitness_models import WeightLog, WorkoutLog, ExerciseLog

def create_fitness_tables():
    """Create fitness tracking tables"""
    
    with app.app_context():
        print("Creating fitness tables...")
        
        # Create the fitness tables
        try:
            # Create tables if they don't exist
            db.create_all()
            print("Fitness tables created successfully!")
            
            # Check if tables were created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            tables = inspector.get_table_names()
            fitness_tables = ['weight_logs', 'workout_logs', 'exercise_logs']
            
            for table in fitness_tables:
                if table in tables:
                    print(f"✓ {table} table exists")
                else:
                    print(f"✗ {table} table NOT found")
                    
        except Exception as e:
            print(f"Error creating tables: {e}")

if __name__ == "__main__":
    create_fitness_tables()

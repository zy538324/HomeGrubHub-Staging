#!/usr/bin/env python
"""
Database verification script for fitness tracking
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

def verify_database():
    """Verify database tables and connectivity"""
    
    try:
        print("Verifying database connection and tables...")
        
        from recipe_app.db import create_app, db
        from sqlalchemy import inspect, text
        
        app = create_app()
        
        with app.app_context():
            # Test basic connection (SQLAlchemy 2.x compatible)
            with db.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                print("✓ Database connection successful")
            
            # Get all tables
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n📊 Total tables in database: {len(tables)}")
            print("Tables:", ', '.join(sorted(tables)))
            
            # Check for fitness tables specifically
            fitness_tables = ['weight_logs', 'workout_logs', 'exercise_logs']
            print(f"\n🏋️ Fitness tracking tables:")
            
            for table in fitness_tables:
                if table in tables:
                    print(f"✓ {table}")
                    # Get column info
                    columns = inspector.get_columns(table)
                    column_names = [col['name'] for col in columns]
                    print(f"   Columns: {', '.join(column_names)}")
                else:
                    print(f"✗ {table} - MISSING")
            
            # Check user table (required for foreign keys)
            if 'user' in tables:
                print(f"\n✓ User table exists")
                with db.engine.connect() as connection:
                    result = connection.execute(text('SELECT COUNT(*) FROM "user"'))
                    user_count = result.fetchone()[0]
                    print(f"   User count: {user_count}")
            else:
                print(f"\n✗ User table missing - required for fitness tracking")
            
            # Test model imports
            try:
                from recipe_app.models.fitness_models import WeightLog, WorkoutLog, ExerciseLog
                print(f"\n✓ Fitness models imported successfully")
                
                # Test queries if tables exist
                if 'weight_logs' in tables:
                    weight_count = WeightLog.query.count()
                    print(f"   WeightLog entries: {weight_count}")
                
                if 'workout_logs' in tables:
                    workout_count = WorkoutLog.query.count()
                    print(f"   WorkoutLog entries: {workout_count}")
                
                if 'exercise_logs' in tables:
                    exercise_count = ExerciseLog.query.count()
                    print(f"   ExerciseLog entries: {exercise_count}")
                    
            except Exception as e:
                print(f"✗ Model import/query error: {e}")
                
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_database()

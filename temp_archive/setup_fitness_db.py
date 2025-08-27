#!/usr/bin/env python
"""
Database setup script specifically for fitness tracking system
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

def setup_fitness_database():
    """Set up the database with fitness tracking tables"""
    
    try:
        print("Setting up fitness tracking database...")
        
        # Import after setting path
        from recipe_app.db import create_app, db
        from recipe_app.models.fitness_models import WeightLog, WorkoutLog, ExerciseLog
        from recipe_app.models.models import User
        from sqlalchemy import inspect
        
        app = create_app()
        
        with app.app_context():
            print("Connected to database...")
            
            # Check existing tables
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            print(f"Existing tables: {existing_tables}")
            
            # Create all tables
            print("Creating all database tables...")
            db.create_all()
            
            # Verify fitness tables were created
            inspector = inspect(db.engine)
            updated_tables = inspector.get_table_names()
            
            fitness_tables = ['weight_logs', 'workout_logs', 'exercise_logs']
            created_tables = []
            missing_tables = []
            
            for table in fitness_tables:
                if table in updated_tables:
                    created_tables.append(table)
                    print(f"✓ {table} table exists")
                else:
                    missing_tables.append(table)
                    print(f"✗ {table} table NOT found")
            
            # Test table functionality
            if 'weight_logs' in created_tables:
                try:
                    count = WeightLog.query.count()
                    print(f"✓ WeightLog model working ({count} entries)")
                except Exception as e:
                    print(f"✗ WeightLog model error: {e}")
            
            if 'workout_logs' in created_tables:
                try:
                    count = WorkoutLog.query.count()
                    print(f"✓ WorkoutLog model working ({count} entries)")
                except Exception as e:
                    print(f"✗ WorkoutLog model error: {e}")
            
            if 'exercise_logs' in created_tables:
                try:
                    count = ExerciseLog.query.count()
                    print(f"✓ ExerciseLog model working ({count} entries)")
                except Exception as e:
                    print(f"✗ ExerciseLog model error: {e}")
            
            if missing_tables:
                print(f"\n⚠️  Missing tables: {missing_tables}")
                print("Attempting to create missing tables...")
                
                # Try to execute SQL directly
                for table in missing_tables:
                    if table == 'weight_logs':
                        try:
                            db.engine.execute("""
                                CREATE TABLE IF NOT EXISTS weight_logs (
                                    id SERIAL PRIMARY KEY,
                                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                                    log_date DATE NOT NULL,
                                    weight_kg FLOAT NOT NULL,
                                    body_fat_percentage FLOAT,
                                    notes TEXT,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    UNIQUE(user_id, log_date)
                                );
                                CREATE INDEX IF NOT EXISTS ix_weight_logs_user_id ON weight_logs(user_id);
                                CREATE INDEX IF NOT EXISTS ix_weight_logs_log_date ON weight_logs(log_date);
                            """)
                            print(f"✓ Manually created {table} table")
                        except Exception as e:
                            print(f"✗ Failed to create {table}: {e}")
                    
                    elif table == 'workout_logs':
                        try:
                            db.engine.execute("""
                                CREATE TABLE IF NOT EXISTS workout_logs (
                                    id SERIAL PRIMARY KEY,
                                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                                    workout_date DATE NOT NULL,
                                    start_time TIMESTAMP,
                                    end_time TIMESTAMP,
                                    duration_minutes INTEGER,
                                    workout_type VARCHAR(50),
                                    notes TEXT,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                );
                                CREATE INDEX IF NOT EXISTS ix_workout_logs_user_id ON workout_logs(user_id);
                                CREATE INDEX IF NOT EXISTS ix_workout_logs_workout_date ON workout_logs(workout_date);
                            """)
                            print(f"✓ Manually created {table} table")
                        except Exception as e:
                            print(f"✗ Failed to create {table}: {e}")
                    
                    elif table == 'exercise_logs':
                        try:
                            db.engine.execute("""
                                CREATE TABLE IF NOT EXISTS exercise_logs (
                                    id SERIAL PRIMARY KEY,
                                    workout_log_id INTEGER NOT NULL REFERENCES workout_logs(id) ON DELETE CASCADE,
                                    exercise_name VARCHAR(100) NOT NULL,
                                    exercise_type VARCHAR(50),
                                    sets INTEGER,
                                    reps INTEGER,
                                    weight_kg FLOAT,
                                    distance_km FLOAT,
                                    duration_minutes INTEGER,
                                    calories_burned FLOAT,
                                    notes TEXT,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                );
                                CREATE INDEX IF NOT EXISTS ix_exercise_logs_workout_id ON exercise_logs(workout_log_id);
                            """)
                            print(f"✓ Manually created {table} table")
                        except Exception as e:
                            print(f"✗ Failed to create {table}: {e}")
            
            print("\n🎉 Database setup completed!")
            print(f"✓ Created tables: {created_tables}")
            if missing_tables:
                print(f"⚠️  Could not create: {missing_tables}")
            
            # Final verification
            final_inspector = inspect(db.engine)
            final_tables = final_inspector.get_table_names()
            fitness_exists = all(table in final_tables for table in fitness_tables)
            
            if fitness_exists:
                print("\n✅ All fitness tracking tables are ready!")
                print("You can now use:")
                print("- Weight logging")
                print("- BMI calculator")
                print("- Workout tracking")
                print("- Exercise logging")
                print("- Weight history")
                print("- Workout history")
            else:
                print("\n❌ Some fitness tables are still missing")
                print("You may need to manually create tables or check database permissions")
                
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    setup_fitness_database()

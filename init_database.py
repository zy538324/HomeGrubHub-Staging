#!/usr/bin/env python3
"""
Database initialization and table creation script
"""

import sys
import os

# Add the parent directory to the path to access recipe_app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from recipe_app.db import create_app, db
from recipe_app.models.models import User
from recipe_app.models.family_models import (
    FamilyAccount, FamilyMember, FamilyMealPlan, 
    FamilyShoppingList, FamilyChallenge, FamilyAchievement
)
from recipe_app.models.nutrition_tracking import Food, Meal, NutritionLog

def init_database():
    """Initialize database and create all tables"""
    app = create_app()
    
    with app.app_context():
        print("🗃️ Initializing database...")
        print("=" * 50)
        
        try:
            # Create all tables
            db.create_all()
            print("✅ All database tables created successfully!")
            
            # Check which tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n📊 Found {len(tables)} tables in database:")
            for table in sorted(tables):
                print(f"  ✅ {table}")
            
            # Check family-specific tables
            family_tables = [t for t in tables if 'family' in t]
            if family_tables:
                print(f"\n👨‍👩‍👧‍👦 Family tables ({len(family_tables)}):")
                for table in family_tables:
                    print(f"  ✅ {table}")
            else:
                print("\n⚠️  No family tables found - family features may not work")
            
            # Check nutrition tables
            nutrition_tables = [t for t in tables if any(word in t for word in ['nutrition', 'food', 'meal'])]
            if nutrition_tables:
                print(f"\n🍎 Nutrition tables ({len(nutrition_tables)}):")
                for table in nutrition_tables:
                    print(f"  ✅ {table}")
            else:
                print("\n⚠️  No nutrition tables found - nutrition tracking may not work")
                
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def check_user_family_status():
    """Check if users have family accounts"""
    app = create_app()
    
    with app.app_context():
        print("\n\n👥 User Family Status")
        print("=" * 50)
        
        users = User.query.all()
        family_users = 0
        
        for user in users:
            try:
                family_account = user.get_family_account() if hasattr(user, 'get_family_account') else None
                if family_account:
                    family_users += 1
                    print(f"✅ {user.username:15} | {user.current_plan:10} | Family: {family_account.family_name}")
                else:
                    print(f"⭕ {user.username:15} | {user.current_plan:10} | No Family")
            except Exception as e:
                print(f"❌ {user.username:15} | {user.current_plan:10} | Error: {e}")
        
        print(f"\n📊 Summary: {family_users}/{len(users)} users have family accounts")

def create_test_family():
    """Create a test family account for testing"""
    app = create_app()
    
    with app.app_context():
        print("\n\n🏠 Creating Test Family")
        print("=" * 50)
        
        try:
            # Find a Family tier user
            family_user = User.query.filter_by(current_plan='Family').first()
            
            if not family_user:
                print("❌ No Family tier users found. Creating one...")
                test_user = User.query.filter_by(username='matt').first()
                if test_user:
                    test_user.current_plan = 'Family'
                    db.session.commit()
                    family_user = test_user
                else:
                    print("❌ No test user found to upgrade")
                    return False
            
            # Check if user already has a family
            existing_family = FamilyAccount.query.filter_by(primary_user_id=family_user.id).first()
            if existing_family:
                print(f"✅ User '{family_user.username}' already has family: '{existing_family.family_name}'")
                print(f"   Family Code: {existing_family.family_code}")
                return True
            
            # Create family account
            family_account = FamilyAccount(
                primary_user_id=family_user.id,
                family_name="Test Family Account",
                max_members=6
            )
            family_account.generate_family_code()
            
            db.session.add(family_account)
            db.session.flush()  # Get the family ID
            
            # Add primary user as admin family member
            primary_member = FamilyMember(
                family_id=family_account.id,
                user_id=family_user.id,
                role='admin',
                age_group='adult',
                display_name=family_user.username or 'Admin',
                permissions={
                    'manage_members': True,
                    'manage_meals': True,
                    'manage_budget': True,
                    'create_challenges': True,
                    'view_all_data': True
                }
            )
            
            db.session.add(primary_member)
            db.session.commit()
            
            print(f"✅ Test family created successfully!")
            print(f"   Family Name: {family_account.family_name}")
            print(f"   Family Code: {family_account.family_code}")
            print(f"   Primary User: {family_user.username}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Failed to create test family: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🚀 HomeGrubHub Database Manager")
    print("=" * 60)
    
    success = init_database()
    if success:
        check_user_family_status()
        create_test_family()
        
        print("\n\n🎉 Database initialization complete!")
        print("You can now start the application with: python run.py")
        print("The family creation feature should now work properly.")
    else:
        print("\n💥 Database initialization failed!")
        print("Please check the error messages above and try again.")

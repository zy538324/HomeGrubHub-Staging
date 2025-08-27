#!/usr/bin/env python3
"""
AWS RDS Setup and Migration Utility for HomeGrubHub

This script helps you:
1. Test AWS RDS connectivity
2. Set up the database schema
3. Migrate data from your current database
4. Switch your application to use AWS RDS

Usage:
python aws_rds_setup.py --test                    # Test connection only
python aws_rds_setup.py --setup-schema           # Create tables in AWS RDS
python aws_rds_setup.py --migrate-data           # Migrate all data
python aws_rds_setup.py --enable-aws-rds         # Switch app to use AWS RDS
python aws_rds_setup.py --full-migration         # Do everything (setup + migrate + switch)
"""

import argparse
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_connectivity():
    """Test AWS RDS connectivity"""
    print("🔍 Testing AWS RDS Connectivity...")
    print("=" * 50)
    
    from configs.aws_db_config import test_aws_connection
    success = test_aws_connection()
    
    if not success:
        print("\n❌ AWS RDS Connection Failed!")
        print("\n🔧 To fix this, you need to:")
        print("1. Make your RDS instance publicly accessible:")
        print("   - Go to AWS RDS Console")
        print("   - Select your instance")
        print("   - Click 'Modify'")
        print("   - Under 'Connectivity', set 'Public access' to 'Yes'")
        print("   - Apply changes")
        print("")
        print("2. Update the security group:")
        print("   - Go to EC2 Console > Security Groups")
        print("   - Find your RDS security group")
        print("   - Add inbound rule: PostgreSQL (5432) from your IP")
        print("   - Your current IP can be found at: https://whatismyipaddress.com/")
        print("")
        print("3. Verify the database exists:")
        print("   - Connect using a PostgreSQL client")
        print("   - Create database 'homegrubhub' if it doesn't exist")
        
        return False
    
    print("\n✅ AWS RDS Connection Successful!")
    return True


def setup_schema():
    """Set up the database schema in AWS RDS"""
    if not test_connectivity():
        return False
        
    print("\n🏗️  Setting up database schema...")
    
    try:
        # Set environment variable to use AWS RDS temporarily
        os.environ['USE_AWS_RDS'] = 'true'
        
        # Import and run Flask migrations
        from flask import Flask
        from flask_migrate import Migrate
        from configs.config import Config
        from recipe_app import create_app
        
        app = create_app()
        
        # Import all models to ensure they're registered
        from recipe_app.models.user import User
        from recipe_app.models.nutrition_tracking import (
            Food, Meal, NutritionLog, WeightLog, StepLog, WaterLog,
            Recipe, ShoppingItem, MealPlan, SmartShoppingItem, 
            AIMealPlan, RecipeAnalysis
        )
        
        with app.app_context():
            from recipe_app import db
            
            print("Creating all tables...")
            db.create_all()
            print("✅ Database schema created successfully!")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to set up schema: {e}")
        return False
    finally:
        # Reset environment variable
        if 'USE_AWS_RDS' in os.environ:
            del os.environ['USE_AWS_RDS']


def migrate_data():
    """Migrate data from current database to AWS RDS"""
    if not test_connectivity():
        return False
        
    print("\n📦 Migrating data to AWS RDS...")
    
    try:
        from scripts.migrate_to_aws_rds import run_migration
        success = run_migration(dry_run=False, backup=True)
        
        if success:
            print("✅ Data migration completed successfully!")
        else:
            print("❌ Data migration failed!")
            
        return success
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def enable_aws_rds():
    """Enable AWS RDS in the application configuration"""
    print("\n🔄 Enabling AWS RDS in application...")
    
    # Update .env file to use AWS RDS
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    try:
        # Read current .env file
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Add or update USE_AWS_RDS setting
        found_aws_rds = False
        new_lines = []
        
        for line in lines:
            if line.startswith('USE_AWS_RDS='):
                new_lines.append('USE_AWS_RDS=true\n')
                found_aws_rds = True
            else:
                new_lines.append(line)
        
        if not found_aws_rds:
            new_lines.append('\n# AWS RDS Configuration\n')
            new_lines.append('USE_AWS_RDS=true\n')
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
        
        print("✅ Updated .env file to use AWS RDS")
        print("⚠️  You'll need to restart your application for changes to take effect")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update configuration: {e}")
        return False


def disable_aws_rds():
    """Disable AWS RDS and go back to previous database"""
    print("\n🔄 Disabling AWS RDS (reverting to previous database)...")
    
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    
    try:
        # Read current .env file
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Update USE_AWS_RDS setting
        new_lines = []
        
        for line in lines:
            if line.startswith('USE_AWS_RDS='):
                new_lines.append('USE_AWS_RDS=false\n')
            else:
                new_lines.append(line)
        
        # Write back to .env file
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
        
        print("✅ Reverted to previous database configuration")
        print("⚠️  You'll need to restart your application for changes to take effect")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update configuration: {e}")
        return False


def full_migration():
    """Perform complete migration to AWS RDS"""
    print("🚀 Starting Full Migration to AWS RDS")
    print("=" * 50)
    
    steps = [
        ("Test connectivity", test_connectivity),
        ("Setup schema", setup_schema),
        ("Migrate data", migrate_data),
        ("Enable AWS RDS", enable_aws_rds)
    ]
    
    for step_name, step_func in steps:
        print(f"\n📍 Step: {step_name}")
        if not step_func():
            print(f"\n❌ Migration failed at step: {step_name}")
            print("🔄 You can retry individual steps or fix the issues and run again")
            return False
    
    print("\n🎉 Full migration completed successfully!")
    print("✅ Your HomeGrubHub application is now using AWS RDS")
    print("⚠️  Please restart your application to use the new database")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='AWS RDS Setup and Migration Utility')
    parser.add_argument('--test', action='store_true', help='Test AWS RDS connectivity')
    parser.add_argument('--setup-schema', action='store_true', help='Set up database schema in AWS RDS')
    parser.add_argument('--migrate-data', action='store_true', help='Migrate data to AWS RDS')
    parser.add_argument('--enable-aws-rds', action='store_true', help='Enable AWS RDS in application')
    parser.add_argument('--disable-aws-rds', action='store_true', help='Disable AWS RDS (revert to previous DB)')
    parser.add_argument('--full-migration', action='store_true', help='Perform complete migration')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    success = True
    
    if args.test:
        success = test_connectivity()
    elif args.setup_schema:
        success = setup_schema()
    elif args.migrate_data:
        success = migrate_data()
    elif args.enable_aws_rds:
        success = enable_aws_rds()
    elif args.disable_aws_rds:
        success = disable_aws_rds()
    elif args.full_migration:
        success = full_migration()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

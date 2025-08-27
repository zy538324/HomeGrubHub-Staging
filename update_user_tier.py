#!/usr/bin/env python3
"""
Script to update user subscription tier
"""

import sys
import os

# Add the parent directory to the path to access recipe_app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from recipe_app.db import create_app, db
from recipe_app.models.models import User

def update_user_tier(username_or_email, new_tier):
    """Update user's subscription tier"""
    app = create_app()
    
    with app.app_context():
        # Find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) | 
            (User.email == username_or_email)
        ).first()
        
        if not user:
            print(f"User '{username_or_email}' not found!")
            return False
        
        old_tier = user.current_plan
        user.current_plan = new_tier
        user.subscription_status = 'active'
        
        try:
            db.session.commit()
            print(f"✅ Successfully updated user '{user.username}' from '{old_tier}' to '{new_tier}'")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating user: {e}")
            return False

def list_all_users():
    """List all users and their current tiers"""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        print(f"\n📋 Found {len(users)} users:")
        print("-" * 60)
        for user in users:
            print(f"Username: {user.username:20} | Email: {user.email:30} | Tier: {user.current_plan}")

if __name__ == "__main__":
    print("🔧 HomeGrubHub User Tier Manager")
    print("=" * 50)
    
    if len(sys.argv) < 2:
        print("Usage: python update_user_tier.py [list|<username_or_email> <new_tier>]")
        print("\nExamples:")
        print("  python update_user_tier.py list")
        print("  python update_user_tier.py admin@example.com Family")
        print("  python update_user_tier.py testuser Pro")
        print("\nAvailable tiers: Free, Home, Family, Pro, Student")
        sys.exit(1)
    
    if sys.argv[1] == "list":
        list_all_users()
    elif len(sys.argv) == 3:
        username_or_email = sys.argv[1]
        new_tier = sys.argv[2]
        
        valid_tiers = ['Free', 'Home', 'Family', 'Pro', 'Student']
        if new_tier not in valid_tiers:
            print(f"❌ Invalid tier '{new_tier}'. Valid tiers: {', '.join(valid_tiers)}")
            sys.exit(1)
        
        success = update_user_tier(username_or_email, new_tier)
        if success:
            print(f"\n🎉 User upgrade complete! You can now access {new_tier} tier features.")
        else:
            print(f"\n💥 Failed to update user tier.")
    else:
        print("❌ Invalid arguments. Use 'list' or provide username/email and new tier.")

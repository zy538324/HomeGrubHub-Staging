"""
Enhanced Family Collaboration Models
Extending the family system with better collaboration features
"""

from datetime import datetime, timedelta
from recipe_app.db import db
from recipe_app.models.family_models import FamilyAccount, FamilyMember
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

class FamilyCookingAssignment(db.Model):
    """
    Cooking Assignment System - Delegate cooking responsibilities with schedules
    Supports recurring assignments, skill levels, and availability tracking
    """
    __tablename__ = 'family_cooking_assignments'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    assigned_member_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    meal_plan_id = Column(Integer, ForeignKey('family_meal_plans.id'), nullable=True)
    
    # Assignment Details
    assignment_type = Column(String(20), default='specific')  # specific, recurring, rotating
    cooking_date = Column(Date, nullable=False)
    meal_types = Column(JSON)  # ['breakfast', 'lunch', 'dinner'] for multi-meal assignments
    
    # Skill & Complexity Management
    required_skill_level = Column(String(20), default='beginner')  # beginner, intermediate, advanced
    estimated_time_minutes = Column(Integer)
    complexity_rating = Column(Integer, default=1)  # 1-5 scale
    
    # Assignment Status
    status = Column(String(20), default='assigned')  # assigned, accepted, in_progress, completed, skipped
    accepted_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Collaboration Features
    helper_members = Column(JSON)  # List of member IDs to help
    cooking_notes = Column(Text)
    prep_instructions = Column(Text)
    shopping_completed = Column(Boolean, default=False)
    
    # Automation & Scheduling
    auto_assigned = Column(Boolean, default=False)  # System-generated assignment
    recurring_pattern = Column(String(50))  # daily, weekly, bi_weekly, monthly
    next_occurrence = Column(Date)  # For recurring assignments
    
    # Feedback & Learning
    difficulty_feedback = Column(Integer)  # 1-5 how hard was it
    time_feedback = Column(Integer)  # actual time taken
    member_rating = Column(Integer)  # 1-5 how much they enjoyed it
    notes_for_next_time = Column(Text)
    
    created_by = Column(Integer, ForeignKey('family_members.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount')
    assigned_member = relationship('FamilyMember', foreign_keys=[assigned_member_id])
    meal_plan = relationship('FamilyMealPlan')
    creator = relationship('FamilyMember', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<CookingAssignment {self.assigned_member.display_name} on {self.cooking_date}>'
    
    def can_accept(self, member_id):
        """Check if member can accept this assignment"""
        return member_id == self.assigned_member_id
    
    def get_helper_names(self):
        """Get names of helper members"""
        if not self.helper_members:
            return []
        members = FamilyMember.query.filter(
            FamilyMember.id.in_(self.helper_members)
        ).all()
        return [m.display_name for m in members]

class FamilyRecipeCollection(db.Model):
    """
    Shared Family Recipe Collection - Collaborative recipe management
    Supports family favourites, member contributions, and rating system
    """
    __tablename__ = 'family_recipe_collections'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    recipe_id = Column(Integer, ForeignKey('recipe.id'))
    custom_recipe_data = Column(JSON)  # For recipes not in main recipe table
    
    # Collaboration Features
    added_by = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    recipe_name = Column(String(200), nullable=False)
    description = Column(Text)
    cuisine_type = Column(String(100))
    difficulty_level = Column(String(20), default='medium')
    prep_time = Column(Integer)
    cook_time = Column(Integer)
    servings = Column(Integer, default=4)
    
    # Family-Specific Customizations
    family_modifications = Column(JSON)  # Family's modifications to original recipe
    member_preferences = Column(JSON)  # Which members like/dislike this recipe
    dietary_adaptations = Column(JSON)  # Adaptations for family dietary needs
    
    # Rating & Feedback System
    family_rating = Column(Float, default=0.0)  # Average family rating
    member_ratings = Column(JSON)  # Individual member ratings
    cooking_notes = Column(Text)  # Family's cooking tips
    success_stories = Column(JSON)  # When recipe worked well
    
    # Usage Tracking
    times_cooked = Column(Integer, default=0)
    last_cooked = Column(Date)
    favourite_member = Column(Integer, ForeignKey('family_members.id'))  # Who likes it most
    
    # Categories & Organization
    family_tags = Column(JSON)  # Custom family tags
    meal_categories = Column(JSON)  # breakfast, lunch, dinner, snack
    occasion_tags = Column(JSON)  # birthday, holiday, quick_dinner, etc.
    
    is_family_favourite = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)  # Visible to all family members
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount')
    recipe = relationship('Recipe', backref='family_collections')
    contributor = relationship('FamilyMember', foreign_keys=[added_by])
    favourite_of = relationship('FamilyMember', foreign_keys=[favourite_member])
    
    def __repr__(self):
        return f'<FamilyRecipe {self.recipe_name}>'
    
    def get_average_rating(self):
        """Calculate average family rating"""
        if not self.member_ratings:
            return 0.0
        ratings = [r for r in self.member_ratings.values() if r > 0]
        return sum(ratings) / len(ratings) if ratings else 0.0
    
    def rate_recipe(self, member_id, rating):
        """Add or update member rating"""
        if not self.member_ratings:
            self.member_ratings = {}
        self.member_ratings[str(member_id)] = rating
        self.family_rating = self.get_average_rating()


class FamilyShoppingRequest(db.Model):
    """
    Enhanced Shopping Request System - Better coordination of family shopping needs
    Supports member requests, approval workflow, and delegation
    """
    __tablename__ = 'family_shopping_requests'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    requested_by = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    
    # Request Details
    item_name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))
    quantity = Column(String(50))
    brand_preference = Column(String(100))
    store_preference = Column(String(100))
    estimated_cost = Column(Float)
    
    # Priority & Urgency
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    needed_by_date = Column(Date)
    reason = Column(Text)  # Why is this needed
    
    # Approval Workflow
    approval_required = Column(Boolean, default=False)  # For children/parental controls
    approved_by = Column(Integer, ForeignKey('family_members.id'))
    approval_status = Column(String(20), default='pending')  # pending, approved, denied
    approval_notes = Column(Text)
    
    # Assignment & Completion
    assigned_shopper = Column(Integer, ForeignKey('family_members.id'))
    shopper_accepted = Column(Boolean, default=False)
    purchased = Column(Boolean, default=False)
    purchased_at = Column(DateTime)
    actual_cost = Column(Float)
    receipt_notes = Column(Text)
    
    # Status Tracking
    status = Column(String(20), default='requested')  # requested, approved, assigned, shopping, completed, cancelled
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount')
    requester = relationship('FamilyMember', foreign_keys=[requested_by])
    approver = relationship('FamilyMember', foreign_keys=[approved_by])
    shopper = relationship('FamilyMember', foreign_keys=[assigned_shopper])
    
    def __repr__(self):
        return f'<ShoppingRequest {self.item_name} by {self.requester.display_name}>'
    
    def can_approve(self, member_id):
        """Check if member can approve this request"""
        member = FamilyMember.query.get(member_id)
        return member and member.role in ['admin', 'parent']

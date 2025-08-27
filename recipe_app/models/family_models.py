"""
Family Tier Database Models
HomeGrubHub Multi-Tier Nutrition Platform
"""

from datetime import datetime
from recipe_app.db import db
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

class FamilyAccount(db.Model):
    """
    Family Account Model - Represents a family subscription account
    Supports up to 6 family members with shared resources
    """
    __tablename__ = 'family_accounts'
    
    id = Column(Integer, primary_key=True)
    primary_user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    family_name = Column(String(100), nullable=False)
    max_members = Column(Integer, default=6)
    current_members = Column(Integer, default=1)
    subscription_status = Column(String(20), default='active')  # active, suspended, cancelled
    family_code = Column(String(10), unique=True)  # Unique family invite code
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    primary_user = relationship('User', back_populates='owned_family')
    family_members = relationship('FamilyMember', back_populates='family', cascade='all, delete-orphan')
    meal_plans = relationship('FamilyMealPlan', back_populates='family', cascade='all, delete-orphan')
    shopping_lists = relationship('FamilyShoppingList', back_populates='family', cascade='all, delete-orphan')
    challenges = relationship('FamilyChallenge', back_populates='family', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FamilyAccount {self.family_name}>'
    
    def generate_family_code(self):
        """Generate unique 8-character family invite code"""
        import string
        import random
        
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not FamilyAccount.query.filter_by(family_code=code).first():
                self.family_code = code
                break
        return code

class FamilyMember(db.Model):
    """
    Family Member Model - Individual family members within a family account
    Includes role-based permissions and age-appropriate customization
    """
    __tablename__ = 'family_members'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    role = Column(String(20), default='member')  # 'admin', 'parent', 'teen', 'child'
    age_group = Column(String(20), default='adult')  # 'child', 'teen', 'adult'
    display_name = Column(String(50))  # Family nickname
    dietary_restrictions = Column(Text)  # JSON string of dietary restrictions
    allergies = Column(Text)  # JSON string of allergies
    favorite_foods = Column(Text)  # JSON string of favorite foods
    nutrition_goals = Column(JSON)  # Individual nutrition goals within family
    daily_calories_target = Column(Float)
    activity_level = Column(String(20), default='moderate')
    permissions = Column(JSON)  # Role-based permissions
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    family = relationship('FamilyAccount', back_populates='family_members')
    user = relationship('User', back_populates='family_memberships')
    assigned_meals = relationship('FamilyMealPlan', foreign_keys='FamilyMealPlan.assigned_cook', back_populates='cook')
    shopping_requests = relationship('FamilyShoppingList', foreign_keys='FamilyShoppingList.requested_by', back_populates='requester')
    
    def __repr__(self):
        return f'<FamilyMember {self.display_name} in {self.family.family_name}>'
    
    def has_permission(self, permission):
        """Check if member has specific permission"""
        if not self.permissions:
            return self.role in ['admin', 'parent']
        return self.permissions.get(permission, False)

class FamilyMealPlan(db.Model):
    """
    Family Meal Plan Model - Shared meal planning for family members
    Supports cooking assignments and member-specific preferences
    """
    __tablename__ = 'family_meal_plans'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    date = Column(Date, nullable=False)
    meal_type = Column(String(20), nullable=False)  # breakfast, lunch, dinner, snack
    recipe_id = Column(Integer, ForeignKey('recipe.id'))
    recipe_name = Column(String(200))  # For non-recipe meals
    assigned_cook = Column(Integer, ForeignKey('family_members.id'))
    servings_planned = Column(Integer, default=1)
    estimated_cost = Column(Float)
    prep_time = Column(Integer)  # minutes
    difficulty_level = Column(String(20), default='easy')
    member_preferences = Column(JSON)  # Which members want this meal
    cooking_notes = Column(Text)
    shopping_list_generated = Column(Boolean, default=False)
    meal_completed = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey('family_members.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount', back_populates='meal_plans')
    recipe = relationship('Recipe', backref='family_meal_plans')
    cook = relationship('FamilyMember', foreign_keys=[assigned_cook], back_populates='assigned_meals')
    creator = relationship('FamilyMember', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<FamilyMealPlan {self.meal_type} on {self.date}>'

class FamilyShoppingList(db.Model):
    """
    Family Shopping List Model - Consolidated shopping list for family
    Supports member requests, budget tracking, and store optimization
    """
    __tablename__ = 'family_shopping_lists'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    item_name = Column(String(200), nullable=False)
    category = Column(String(50))  # produce, dairy, meat, pantry, etc.
    quantity = Column(String(50))
    unit = Column(String(20))  # lbs, oz, pieces, etc.
    estimated_cost = Column(Float)
    actual_cost = Column(Float)
    store_preference = Column(String(100))
    brand_preference = Column(String(100))
    priority = Column(String(20), default='normal')  # low, normal, high, urgent
    requested_by = Column(Integer, ForeignKey('family_members.id'))
    approved_by = Column(Integer, ForeignKey('family_members.id'))  # For parental approval
    meal_plan_id = Column(Integer, ForeignKey('family_meal_plans.id'))  # If from meal plan
    purchased = Column(Boolean, default=False)
    purchased_by = Column(Integer, ForeignKey('family_members.id'))
    purchased_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount', back_populates='shopping_lists')
    requester = relationship('FamilyMember', foreign_keys=[requested_by], back_populates='shopping_requests')
    approver = relationship('FamilyMember', foreign_keys=[approved_by])
    purchaser = relationship('FamilyMember', foreign_keys=[purchased_by])
    meal_plan = relationship('FamilyMealPlan')
    
    def __repr__(self):
        return f'<FamilyShoppingItem {self.item_name}>'

class FamilyChallenge(db.Model):
    """
    Family Challenge Model - Nutrition and health challenges for families
    Supports individual and family-wide goals with achievement tracking
    """
    __tablename__ = 'family_challenges'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    challenge_name = Column(String(200), nullable=False)
    challenge_type = Column(String(50), nullable=False)  # nutrition, activity, cooking, learning
    description = Column(Text)
    target_metric = Column(String(100))  # calories, vegetables, water, etc.
    target_value = Column(Float)
    target_unit = Column(String(50))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    participants = Column(JSON)  # List of member IDs participating
    individual_targets = Column(JSON)  # Different targets per member
    reward_type = Column(String(50))  # points, badge, prize, activity
    reward_description = Column(String(200))
    difficulty_level = Column(String(20), default='medium')  # easy, medium, hard
    created_by = Column(Integer, ForeignKey('family_members.id'))
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount', back_populates='challenges')
    creator = relationship('FamilyMember')
    progress_entries = relationship('FamilyChallengeProgress', back_populates='challenge', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<FamilyChallenge {self.challenge_name}>'
    
    def get_family_progress(self):
        """Calculate overall family progress on challenge"""
        if not self.progress_entries:
            return 0
        
        total_progress = sum(entry.current_value for entry in self.progress_entries)
        target_total = self.target_value * len(self.participants)
        return min((total_progress / target_total) * 100, 100) if target_total > 0 else 0

class FamilyChallengeProgress(db.Model):
    """
    Family Challenge Progress Model - Track individual progress on family challenges
    """
    __tablename__ = 'family_challenge_progress'
    
    id = Column(Integer, primary_key=True)
    challenge_id = Column(Integer, ForeignKey('family_challenges.id'), nullable=False)
    member_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    current_value = Column(Float, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text)
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime)
    
    # Relationships
    challenge = relationship('FamilyChallenge', back_populates='progress_entries')
    member = relationship('FamilyMember')
    
    def __repr__(self):
        return f'<ChallengeProgress {self.member.display_name} - {self.current_value}>'

class FamilyAchievement(db.Model):
    """
    Family Achievement Model - Track family and individual achievements
    """
    __tablename__ = 'family_achievements'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    member_id = Column(Integer, ForeignKey('family_members.id'))  # NULL for family-wide achievements
    achievement_type = Column(String(50), nullable=False)  # nutrition, cooking, challenge, milestone
    achievement_name = Column(String(200), nullable=False)
    achievement_description = Column(Text)
    badge_icon = Column(String(100))  # Font Awesome icon class
    badge_color = Column(String(20), default='#007bff')
    points_earned = Column(Integer, default=0)
    earned_date = Column(DateTime, default=datetime.utcnow)
    related_challenge_id = Column(Integer, ForeignKey('family_challenges.id'))
    
    # Relationships
    family = relationship('FamilyAccount')
    member = relationship('FamilyMember')
    related_challenge = relationship('FamilyChallenge')
    
    def __repr__(self):
        return f'<FamilyAchievement {self.achievement_name}>'

# Update existing User model to include family relationships
# This would be added to the existing User model:
"""
# Add to User model:
owned_family = relationship('FamilyAccount', back_populates='primary_user', uselist=False)
family_memberships = relationship('FamilyMember', back_populates='user')

def get_family_account(self):
    '''Get user's family account (either owned or member of)'''
    if self.owned_family:
        return self.owned_family
    elif self.family_memberships:
        return self.family_memberships[0].family
    return None

def is_family_admin(self):
    '''Check if user is family account administrator'''
    return self.owned_family is not None

def get_family_role(self):
    '''Get user's role in family account'''
    if self.owned_family:
        return 'admin'
    elif self.family_memberships:
        return self.family_memberships[0].role
    return None
"""

# ============================================================================
# FAMILY COMMUNICATION MODELS (Phase 3)
# ============================================================================

class FamilyMessage(db.Model):
    """Family internal messaging system"""
    __tablename__ = 'family_messages'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    recipient_id = Column(Integer, ForeignKey('family_members.id'), nullable=True)  # None for family-wide
    
    message = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=False, default='general')  # general, meal_related, shopping, challenge
    priority = Column(String(20), nullable=False, default='normal')  # low, normal, high, urgent
    
    # Related content
    meal_plan_id = Column(Integer, ForeignKey('family_meal_plans.id'), nullable=True)
    challenge_id = Column(Integer, ForeignKey('family_challenges.id'), nullable=True)
    shopping_item_id = Column(Integer, ForeignKey('family_shopping_lists.id'), nullable=True)
    
    # Message status
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)
    is_pinned = Column(Boolean, nullable=False, default=False)
    is_archived = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount')
    sender = relationship('FamilyMember', foreign_keys=[sender_id])
    recipient = relationship('FamilyMember', foreign_keys=[recipient_id])
    meal_plan = relationship('FamilyMealPlan')
    challenge = relationship('FamilyChallenge')
    shopping_item = relationship('FamilyShoppingList')
    
    def mark_as_read(self):
        """Mark message as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def is_family_wide(self):
        """Check if message is for entire family"""
        return self.recipient_id is None

class FamilyNotification(db.Model):
    """System-generated notifications for family members"""
    __tablename__ = 'family_notifications'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    recipient_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    
    notification_type = Column(String(50), nullable=False)  # meal_reminder, shopping_alert, challenge_update, achievement_earned
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    # Notification data
    action_url = Column(String(500), nullable=True)  # Deep link for notification action
    notification_data = Column(JSON)  # Additional data for notification
    
    # Delivery status
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)
    is_delivered = Column(Boolean, nullable=False, default=False)
    delivered_at = Column(DateTime, nullable=True)
    
    # Scheduling
    scheduled_for = Column(DateTime, nullable=True)  # For future delivery
    expires_at = Column(DateTime, nullable=True)  # Notification expiration
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount')
    recipient = relationship('FamilyMember')
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = datetime.utcnow()
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.is_delivered = True
        self.delivered_at = datetime.utcnow()
    
    def is_expired(self):
        """Check if notification has expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at

class MealPlanComment(db.Model):
    """Comments on family meal plans"""
    __tablename__ = 'meal_plan_comments'
    
    id = Column(Integer, primary_key=True)
    meal_plan_id = Column(Integer, ForeignKey('family_meal_plans.id'), nullable=False)
    member_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    
    comment = Column(Text, nullable=False)
    comment_type = Column(String(50), nullable=False, default='general')  # general, suggestion, question, approval
    
    # Parent comment for replies
    parent_comment_id = Column(Integer, ForeignKey('meal_plan_comments.id'), nullable=True)
    
    # Reactions/voting
    likes_count = Column(Integer, nullable=False, default=0)
    is_helpful = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    meal_plan = relationship('FamilyMealPlan')
    member = relationship('FamilyMember')
    parent_comment = relationship('MealPlanComment', remote_side=[id])
    
    def get_replies(self):
        """Get all replies to this comment"""
        return MealPlanComment.query.filter_by(parent_comment_id=self.id).order_by(MealPlanComment.created_at).all()

# ============================================================================
# PARENTAL CONTROLS MODELS (Phase 3)
# ============================================================================

class ParentalControl(db.Model):
    """Parental control settings for family members"""
    __tablename__ = 'parental_controls'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    child_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    
    # Access Controls
    screen_time_limit = Column(Integer, nullable=True)  # Minutes per day
    allowed_hours_start = Column(String(8), nullable=True)  # e.g., "07:00"
    allowed_hours_end = Column(String(8), nullable=True)    # e.g., "21:00"
    
    # Content Restrictions
    content_filter_level = Column(String(20), nullable=False, default='moderate')  # strict, moderate, relaxed
    blocked_categories = Column(JSON)  # List of blocked content categories
    allowed_features = Column(JSON)    # List of allowed app features
    
    # Approval Requirements
    requires_meal_approval = Column(Boolean, nullable=False, default=True)
    requires_shopping_approval = Column(Boolean, nullable=False, default=False)
    requires_challenge_approval = Column(Boolean, nullable=False, default=False)
    
    # Monitoring Settings
    track_nutrition = Column(Boolean, nullable=False, default=True)
    track_screen_time = Column(Boolean, nullable=False, default=True)
    send_progress_reports = Column(Boolean, nullable=False, default=True)
    
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount')
    child = relationship('FamilyMember', foreign_keys=[child_id])
    parent = relationship('FamilyMember', foreign_keys=[parent_id])
    
    def is_within_allowed_hours(self):
        """Check if current time is within allowed hours"""
        if not self.allowed_hours_start or not self.allowed_hours_end:
            return True
        
        from datetime import datetime, time
        current_time = datetime.now().time()
        start_time = datetime.strptime(self.allowed_hours_start, "%H:%M").time()
        end_time = datetime.strptime(self.allowed_hours_end, "%H:%M").time()
        
        return start_time <= current_time <= end_time
    
    def get_remaining_screen_time(self):
        """Get remaining screen time for today (in minutes)"""
        if not self.screen_time_limit:
            return None
        
        # This would integrate with actual usage tracking
        # For now, return a mock value
        used_time = 45  # Mock: 45 minutes used today
        return max(0, self.screen_time_limit - used_time)

class ApprovalRequest(db.Model):
    """Approval requests from children to parents"""
    __tablename__ = 'approval_requests'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    child_id = Column(Integer, ForeignKey('family_members.id'), nullable=False)
    parent_id = Column(Integer, ForeignKey('family_members.id'), nullable=True)
    
    request_type = Column(String(50), nullable=False)  # meal_plan, shopping_item, challenge_join, screen_time
    request_title = Column(String(200), nullable=False)
    request_description = Column(Text)
    
    # Request data
    request_data = Column(JSON)  # Store specific request details
    
    # Approval status
    status = Column(String(20), nullable=False, default='pending')  # pending, approved, rejected
    parent_response = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Auto-expiration
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    family = relationship('FamilyAccount')
    child = relationship('FamilyMember', foreign_keys=[child_id])
    parent = relationship('FamilyMember', foreign_keys=[parent_id])
    
    def approve(self, parent_id, response=None):
        """Approve the request"""
        self.status = 'approved'
        self.parent_id = parent_id
        self.parent_response = response
        self.approved_at = datetime.utcnow()
    
    def reject(self, parent_id, response=None):
        """Reject the request"""
        self.status = 'rejected'
        self.parent_id = parent_id
        self.parent_response = response
    
    def is_expired(self):
        """Check if request has expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at

# ============================================================================
# FAMILY ANALYTICS MODELS (Phase 3)
# ============================================================================

class FamilyAnalytics(db.Model):
    """Store family analytics and trend data"""
    __tablename__ = 'family_analytics'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    
    metric_type = Column(String(50), nullable=False)  # nutrition_trend, cost_analysis, health_score, activity_summary
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    
    # Analytics data
    metric_data = Column(JSON, nullable=False)  # Store complex analytics data
    summary_stats = Column(JSON)  # Key summary statistics
    
    # Calculation metadata
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    calculation_version = Column(String(10), nullable=False, default='1.0')
    is_current = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    family = relationship('FamilyAccount')
    
    def __repr__(self):
        return f'<FamilyAnalytics {self.metric_type} - {self.period_start} to {self.period_end}>'

class FamilyCostTracking(db.Model):
    """Track family food and nutrition related expenses"""
    __tablename__ = 'family_cost_tracking'
    
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey('family_accounts.id'), nullable=False)
    
    expense_type = Column(String(50), nullable=False)  # groceries, dining_out, supplements, meal_delivery
    category = Column(String(50))  # produce, meat, dairy, etc.
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default='USD')
    
    # Transaction details
    transaction_date = Column(Date, nullable=False)
    description = Column(String(500))
    store_location = Column(String(200))
    
    # Related items
    shopping_list_id = Column(Integer, ForeignKey('family_shopping_lists.id'), nullable=True)
    meal_plan_id = Column(Integer, ForeignKey('family_meal_plans.id'), nullable=True)
    
    # Categorization
    is_planned = Column(Boolean, nullable=False, default=True)  # Was this expense planned?
    is_healthy = Column(Boolean, nullable=True)  # Healthy food expense rating
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    recorded_by = Column(Integer, ForeignKey('family_members.id'))
    
    # Relationships
    family = relationship('FamilyAccount')
    shopping_list = relationship('FamilyShoppingList')
    meal_plan = relationship('FamilyMealPlan')
    recorded_by_member = relationship('FamilyMember')
    
    def __repr__(self):
        return f'<FamilyCostTracking {self.expense_type} - ${self.amount}>'

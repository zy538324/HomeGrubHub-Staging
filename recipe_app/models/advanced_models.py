# Enhanced Models for Advanced Features
# This file contains the new database models for nutrition, meal planning, pantry management, etc.

from flask_sqlalchemy import SQLAlchemy
from recipe_app.db import db
from datetime import datetime, date
from decimal import Decimal

# ===============================
# NUTRITION & DIETARY MODELS
# ===============================

class NutritionProfile(db.Model):
    """Complete nutrition information for recipes"""
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    
    # Macronutrients (per serving)
    calories = db.Column(db.Float)
    protein_g = db.Column(db.Float)
    carbs_g = db.Column(db.Float)
    fat_g = db.Column(db.Float)
    fiber_g = db.Column(db.Float)
    sugar_g = db.Column(db.Float)
    
    # Micronutrients
    sodium_mg = db.Column(db.Float)
    potassium_mg = db.Column(db.Float)
    iron_mg = db.Column(db.Float)
    calcium_mg = db.Column(db.Float)
    vitamin_c_mg = db.Column(db.Float)
    vitamin_d_ug = db.Column(db.Float)
    
    # Calculated fields
    protein_percentage = db.Column(db.Float)  # % of total calories
    carbs_percentage = db.Column(db.Float)
    fat_percentage = db.Column(db.Float)
    
    # Nutritional flags
    is_high_protein = db.Column(db.Boolean, default=False)
    is_low_carb = db.Column(db.Boolean, default=False)
    is_high_fiber = db.Column(db.Boolean, default=False)
    is_low_sodium = db.Column(db.Boolean, default=False)
    is_iron_rich = db.Column(db.Boolean, default=False)
    
    # Data source and quality
    data_source = db.Column(db.String(50))  # 'manual', 'edamam', 'spoonacular'
    confidence_score = db.Column(db.Float)  # 0-1 quality rating
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    recipe = db.relationship('Recipe', backref=db.backref('nutrition_profile', uselist=False))
    
    def calculate_percentages(self):
        """Calculate macronutrient percentages"""
        if self.calories and self.calories > 0:
            total_macro_calories = (
                (self.protein_g or 0) * 4 +
                (self.carbs_g or 0) * 4 +
                (self.fat_g or 0) * 9
            )
            if total_macro_calories > 0:
                self.protein_percentage = ((self.protein_g or 0) * 4 / total_macro_calories) * 100
                self.carbs_percentage = ((self.carbs_g or 0) * 4 / total_macro_calories) * 100
                self.fat_percentage = ((self.fat_g or 0) * 9 / total_macro_calories) * 100
    
    def update_nutritional_flags(self):
        """Update boolean flags based on nutrition values"""
        # High protein: >20% of calories or >20g per serving
        self.is_high_protein = (self.protein_percentage or 0) > 20 or (self.protein_g or 0) > 20
        
        # Low carb: <20% of calories
        self.is_low_carb = (self.carbs_percentage or 0) < 20
        
        # High fiber: >5g per serving
        self.is_high_fiber = (self.fiber_g or 0) > 5
        
        # Low sodium: <300mg per serving
        self.is_low_sodium = (self.sodium_mg or 0) < 300
        
        # Iron rich: >3mg per serving (>15% DV)
        self.is_iron_rich = (self.iron_mg or 0) > 3


class DietaryRestriction(db.Model):
    """Dietary restrictions and preferences"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # 'vegetarian', 'vegan', 'gluten-free'
    description = db.Column(db.Text)
    category = db.Column(db.String(30))  # 'allergy', 'dietary_choice', 'medical', 'religious'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Association table for user dietary restrictions
user_dietary_restrictions = db.Table('user_dietary_restrictions',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('restriction_id', db.Integer, db.ForeignKey('dietary_restriction.id'), primary_key=True)
)

# Association table for recipe dietary compliance
recipe_dietary_compliance = db.Table('recipe_dietary_compliance',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True),
    db.Column('restriction_id', db.Integer, db.ForeignKey('dietary_restriction.id'), primary_key=True)
)


# ===============================
# EQUIPMENT & FILTERING MODELS
# ===============================

class Equipment(db.Model):
    """Kitchen equipment required for recipes"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(30))  # 'basic', 'appliance', 'specialty'
    description = db.Column(db.Text)
    is_common = db.Column(db.Boolean, default=True)  # Most kitchens have this
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Association table for recipe equipment requirements
recipe_equipment = db.Table('recipe_equipment',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True),
    db.Column('equipment_id', db.Integer, db.ForeignKey('equipment.id'), primary_key=True)
)

# Association table for user equipment
user_equipment = db.Table('user_equipment',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('equipment_id', db.Integer, db.ForeignKey('equipment.id'), primary_key=True)
)


class SeasonalTag(db.Model):
    """Seasonal tags for recipes"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)  # 'spring', 'summer', 'autumn', 'winter'
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#28a745')  # Hex color
    
    # Date ranges (can be multiple per season)
    start_month = db.Column(db.Integer)  # 1-12
    end_month = db.Column(db.Integer)    # 1-12


# Association table for recipe seasonal tags
recipe_seasonal_tags = db.Table('recipe_seasonal_tags',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True),
    db.Column('seasonal_tag_id', db.Integer, db.ForeignKey('seasonal_tag.id'), primary_key=True)
)


# ===============================
# MEAL PLANNING MODELS
# ===============================

class MealPlan(db.Model):
    """User's meal plans"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Date range
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Settings
    is_active = db.Column(db.Boolean, default=True)
    is_template = db.Column(db.Boolean, default=False)  # For reusable meal plans
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('meal_plans', lazy=True))
    
    def get_meal_for_day_and_type(self, day_index, meal_type):
        """Get meal entry for a specific day (0-6) and meal type"""
        from datetime import timedelta
        target_date = self.start_date + timedelta(days=day_index)
        return MealPlanEntry.query.filter_by(
            meal_plan_id=self.id,
            planned_date=target_date,
            meal_type=meal_type
        ).first()


class MealPlanEntry(db.Model):
    """Individual meals in a meal plan"""
    id = db.Column(db.Integer, primary_key=True)
    meal_plan_id = db.Column(db.Integer, db.ForeignKey('meal_plan.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    
    # Scheduling
    planned_date = db.Column(db.Date, nullable=False)  # Actual date, not day of week
    meal_type = db.Column(db.String(20), nullable=False)  # 'breakfast', 'lunch', 'dinner', 'snack'
    
    # Serving information
    planned_servings = db.Column(db.Integer, default=1)  # Match database column name
    scaling_factor = db.Column(db.Float, default=1.0)  # Recipe multiplier
    
    # Status
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Relationships
    meal_plan = db.relationship('MealPlan', backref=db.backref('planned_meals', lazy=True))
    recipe = db.relationship('Recipe', backref=db.backref('meal_plan_entries', lazy=True))


# ===============================
# PANTRY & SHOPPING MODELS
# ===============================

class Ingredient(db.Model):
    """Master ingredient database"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(50))  # 'protein', 'vegetable', 'grain', 'dairy', etc.
    common_unit = db.Column(db.String(20))  # 'grams', 'cups', 'pieces'
    
    # Nutritional info per 100g
    calories_per_100g = db.Column(db.Float)
    protein_per_100g = db.Column(db.Float)
    carbs_per_100g = db.Column(db.Float)
    fat_per_100g = db.Column(db.Float)
    
    # Storage info
    typical_shelf_life_days = db.Column(db.Integer)
    storage_location = db.Column(db.String(50))  # 'pantry', 'fridge', 'freezer'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LegacyPantryItem(db.Model):
    """User's pantry inventory (legacy model - replaced by new pantry system)"""
    __tablename__ = 'legacy_pantry_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    
    # Quantity
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    
    # Dates
    purchase_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    
    # Cost tracking
    cost = db.Column(db.Numeric(10, 2))
    store = db.Column(db.String(50))
    
    # Status
    is_running_low = db.Column(db.Boolean, default=False)
    is_expired = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('legacy_pantry_items', lazy=True))
    ingredient = db.relationship('Ingredient', backref=db.backref('legacy_pantry_items', lazy=True))



# ===============================
# PRICE TRACKING MODELS
# ===============================

class Store(db.Model):
    """Supermarket/store information"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    chain = db.Column(db.String(50))  # 'Tesco', 'Sainsbury\'s', 'ASDA'
    location = db.Column(db.String(100))
    
    # API info
    api_endpoint = db.Column(db.String(200))
    has_api = db.Column(db.Boolean, default=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class IngredientPrice(db.Model):
    """Price tracking for ingredients at different stores"""
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    
    # Price info
    price = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    
    # Price per standard unit (e.g., per 100g)
    price_per_100g = db.Column(db.Numeric(10, 2))
    
    # Product info
    product_name = db.Column(db.String(200))
    brand = db.Column(db.String(100))
    is_organic = db.Column(db.Boolean, default=False)
    is_on_sale = db.Column(db.Boolean, default=False)
    
    # Data tracking
    date_recorded = db.Column(db.Date, default=date.today)
    data_source = db.Column(db.String(50))  # 'api', 'manual', 'scraper'
    
    # Relationships
    ingredient = db.relationship('Ingredient', backref=db.backref('prices', lazy=True))
    store = db.relationship('Store', backref=db.backref('ingredient_prices', lazy=True))


# ===============================
# USER PREFERENCES MODELS
# ===============================

class UserPreferences(db.Model):
    """User's cooking and dietary preferences"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Simple JSON storage for preferences (easier than complex relationships)
    dietary_restriction_ids = db.Column(db.JSON)  # List of dietary restriction IDs
    equipment_ids = db.Column(db.JSON)  # List of equipment IDs
    
    # Cooking preferences
    preferred_meal_types = db.Column(db.JSON)  # ['breakfast', 'lunch', 'dinner']
    max_prep_time = db.Column(db.Integer)  # minutes
    max_cook_time = db.Column(db.Integer)  # minutes
    preferred_difficulty = db.Column(db.String(20))  # 'Easy', 'Medium', 'Hard'
    
    # Budget preferences
    max_cost_per_serving = db.Column(db.Numeric(10, 2))
    preferred_stores = db.Column(db.JSON)  # Store IDs
    
    # Nutritional goals
    daily_calorie_target = db.Column(db.Integer)
    protein_percentage_target = db.Column(db.Float)
    carb_percentage_target = db.Column(db.Float)
    fat_percentage_target = db.Column(db.Float)
    
    # Allergies and dislikes
    allergens = db.Column(db.JSON)  # List of allergen ingredients
    disliked_ingredients = db.Column(db.JSON)  # List of ingredient IDs
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('preferences', uselist=False))


# ===============================
# SUBSTITUTION & AI MODELS
# ===============================

class IngredientSubstitution(db.Model):
    """Ingredient substitution rules"""
    id = db.Column(db.Integer, primary_key=True)
    original_ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    substitute_ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    
    # Substitution ratio
    ratio = db.Column(db.Float, default=1.0)  # How much substitute to use
    ratio_notes = db.Column(db.String(200))  # "Use 3/4 cup substitute for 1 cup original"
    
    # Context
    dietary_reason = db.Column(db.String(50))  # 'vegan', 'gluten-free', 'allergy'
    cooking_method = db.Column(db.String(50))  # 'baking', 'frying', 'raw'
    
    # Impact on recipe
    taste_impact = db.Column(db.String(20))  # 'minimal', 'moderate', 'significant'
    texture_impact = db.Column(db.String(20))
    nutrition_impact = db.Column(db.String(20))
    
    # Confidence and source
    confidence_score = db.Column(db.Float)  # 0-1
    source = db.Column(db.String(100))  # 'nutritionist', 'chef', 'ai'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    original = db.relationship('Ingredient', foreign_keys=[original_ingredient_id])
    substitute = db.relationship('Ingredient', foreign_keys=[substitute_ingredient_id])


# ===============================
# RECIPE ENHANCEMENTS
# ===============================

# Add new fields to existing Recipe model through migration
# - cost_per_serving: Calculated field
# - estimated_cost: Total recipe cost
# - batch_cooking_notes: Text field for batch cooking instructions
# - freezing_instructions: Text field for freezing/storage
# - equipment_requirements: Many-to-many with Equipment
# - dietary_compliance: Many-to-many with DietaryRestriction
# - seasonal_tags: Many-to-many with SeasonalTag


# ===============================
# COMMUNITY & SOCIAL INTERACTION MODELS
# ===============================

class RecipeVote(db.Model):
    """Positive-only voting system to prevent bullying"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    vote_type = db.Column(db.String(20), nullable=False)  # 'love_it', 'want_to_try', 'not_favourite'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Prevent duplicate votes per user per recipe
    __table_args__ = (db.UniqueConstraint('user_id', 'recipe_id', name='unique_user_recipe_vote'),)
    
    # Relationships
    user = db.relationship('User', backref='recipe_votes')
    recipe = db.relationship('Recipe', backref='votes')
    
    @property
    def display_text(self):
        """Return friendly display text for vote type"""
        vote_map = {
            'love_it': '👍 Love it!',
            'want_to_try': '🤔 Want to try',
            'not_favourite': '😊 Not my favourite'
        }
        return vote_map.get(self.vote_type, '')


# ===============================
# CHALLENGE MODELS
# ===============================

class Challenge(db.Model):
    """Community challenges and competitions"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Challenge parameters
    challenge_type = db.Column(db.String(50))  # 'recipe_creation', 'meal_plan', 'budget_challenge'
    difficulty_level = db.Column(db.String(20))  # 'beginner', 'intermediate', 'advanced'
    
    # Dates
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    
    # Challenge criteria
    criteria = db.Column(db.JSON)  # Flexible criteria storage
    max_participants = db.Column(db.Integer)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    
    # Admin info
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref=db.backref('created_challenges', lazy=True))
    participations = db.relationship('ChallengeParticipation', back_populates='challenge', cascade='all, delete-orphan')
    
    @property
    def is_ongoing(self):
        """Check if challenge is currently ongoing"""
        now = datetime.utcnow()
        return self.start_date <= now <= self.end_date and self.is_active
    
    @property
    def participant_count(self):
        """Get number of participants"""
        return len(self.participations)
    
    @property
    def is_full(self):
        """Check if challenge has reached max participants"""
        if not self.max_participants:
            return False
        return self.participant_count >= self.max_participants
    
    def can_join(self, user):
        """Check if user can join the challenge"""
        if not self.is_ongoing or self.is_full:
            return False
        # Check if user is already participating
        return not any(p.user_id == user.id for p in self.participations)
    
    def get_user_participation(self, user):
        """Get user's participation in this challenge"""
        return next((p for p in self.participations if p.user_id == user.id), None)


class ChallengeParticipation(db.Model):
    """User participation in challenges"""
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenge.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Submission
    submitted_recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=True)
    submission_notes = db.Column(db.Text)
    submission_date = db.Column(db.DateTime)
    
    # Scoring
    score = db.Column(db.Float)
    rank = db.Column(db.Integer)
    
    # Status
    is_completed = db.Column(db.Boolean, default=False)
    is_winner = db.Column(db.Boolean, default=False)
    
    # Timestamps
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    challenge = db.relationship('Challenge', back_populates='participations')
    user = db.relationship('User', backref=db.backref('challenge_participations', lazy=True))
    submitted_recipe = db.relationship('Recipe', backref=db.backref('challenge_submissions', lazy=True))
    __table_args__ = (
        db.UniqueConstraint('challenge_id', 'user_id', name='uq_challenge_user'),
    )

# ===============================
# SHOPPING LIST MODELS
# ===============================

class ShoppingList(db.Model):
    """User shopping lists"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meal_plan_id = db.Column(db.Integer, db.ForeignKey('meal_plan.id'), nullable=True)  # Link to meal plan
    name = db.Column(db.String(100), nullable=False, default='My Shopping List')
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('shopping_lists', lazy=True))
    meal_plan = db.relationship('MealPlan', backref=db.backref('shopping_lists', lazy=True))


class ShoppingListItem(db.Model):
    @property
    def user_id(self):
        return self.shopping_list.user_id if self.shopping_list else None
    """Items in shopping lists"""
    id = db.Column(db.Integer, primary_key=True)
    shopping_list_id = db.Column(db.Integer, db.ForeignKey('shopping_list.id'), nullable=False)
    
    # Product information
    
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100))
    barcode = db.Column(db.String(20))  # For barcode-scanned items
    category = db.Column(db.String(50))  # Food category
    image_url = db.Column(db.String(500))  # Product image URL
    
    # Quantity and unit
    quantity = db.Column(db.Float, default=1.0)
    unit = db.Column(db.String(20), default='item')  # item, kg, lbs, etc.
    
    # Status
    is_purchased = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=1)  # 1=low, 2=medium, 3=high
    
    # Optional details
    notes = db.Column(db.Text)
    estimated_price = db.Column(db.Float)
    store_section = db.Column(db.String(50))  # Dairy, Produce, etc.
    
    # Source tracking
    source = db.Column(db.String(20), default='manual')  # manual, barcode_scan, recipe
    source_recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    purchased_at = db.Column(db.DateTime)
    
    # Relationships
    shopping_list = db.relationship('ShoppingList', backref=db.backref('items', lazy=True, cascade='all, delete-orphan'))
    source_recipe = db.relationship('Recipe', backref=db.backref('shopping_list_items', lazy=True))


class ScannedProduct(db.Model):
    """Cache for scanned products to avoid repeated API calls"""
    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Product details
    name = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100))
    image_url = db.Column(db.String(500))
    
    # Nutrition data (JSON stored as text)
    nutrition_data = db.Column(db.Text)  # JSON string
    ingredients_text = db.Column(db.Text)
    dietary_info = db.Column(db.Text)  # JSON string
    
    # Product metadata
    category = db.Column(db.String(100))
    quantity = db.Column(db.String(50))
    nutriscore = db.Column(db.String(1))
    
    # Data quality and source
    data_source = db.Column(db.String(20), default='openfoodfacts')
    data_quality = db.Column(db.Float)  # 0-1 score
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Usage tracking
    scan_count = db.Column(db.Integer, default=1)
    last_scanned = db.Column(db.DateTime, default=datetime.utcnow)

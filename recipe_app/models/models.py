from flask_sqlalchemy import SQLAlchemy
from recipe_app.db import db
from flask_login import UserMixin
from flask import url_for
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import datetime

from recipe_app.config.tiers import get_available_features

# --- WeightGoal model for user weight goal planner ---
class WeightGoal(db.Model):
    __tablename__ = 'weight_goals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True, unique=True)
    current_weight = db.Column(db.Float, nullable=False)
    target_weight = db.Column(db.Float, nullable=False)
    time_frame_weeks = db.Column(db.Integer, nullable=False)
    date_set = db.Column(db.DateTime, default=datetime.utcnow)
    # Optionally store unit (kg/lbs)
    weight_unit = db.Column(db.String(10), default='kg')
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'current_weight': self.current_weight,
            'target_weight': self.target_weight,
            'time_frame_weeks': self.time_frame_weeks,
            'date_set': self.date_set.isoformat() if self.date_set else None,
            'weight_unit': self.weight_unit
        }

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))  # Increased to 256 for longer hashes
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Email verification fields
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(128), unique=True, nullable=True)
    email_verification_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Password reset fields
    password_reset_token = db.Column(db.String(128), unique=True, nullable=True)
    password_reset_sent_at = db.Column(db.DateTime, nullable=True)
    
    # New fields for subscription management
    current_plan = db.Column(db.String(64), default='Free')
    trial_end = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship to track user's favourite recipes
    favourites = db.relationship('Recipe', secondary='user_favourites', lazy='subquery',
                               backref=db.backref('favourited_by', lazy=True))

    # Family relationships (for Phase 3 family features)
    owned_family = db.relationship('FamilyAccount', back_populates='primary_user', uselist=False, lazy='select')
    family_memberships = db.relationship('FamilyMember', back_populates='user', lazy='select')

    # Stripe customer ID for payment processing
    stripe_customer_id = db.Column(db.String(64), index=True, unique=True, nullable=True)
    stripe_subscription_id = db.Column(db.String(64), index=True, unique=True, nullable=True)
    subscription_status = db.Column(db.String(32), default='inactive')  # active, trialing, past_due, canceled, etc.
    
    # Location data for price comparison
    postcode = db.Column(db.String(10), nullable=True)  # UK postcode format
    
    # Profile image fields
    profile_image = db.Column(db.String(120), nullable=True)  # Filename of uploaded image
    profile_bio = db.Column(db.Text, nullable=True)  # Short bio for community features
    display_name = db.Column(db.String(100), nullable=True)  # Display name (can be different from username)
    social_links = db.Column(db.JSON, nullable=True)  # JSON field for social media links

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_email_verification_token(self):
        """Generate and set email verification token"""
        import secrets
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_sent_at = datetime.utcnow()
        return self.email_verification_token
    
    def generate_password_reset_token(self):
        """Generate and set password reset token"""
        import secrets
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_sent_at = datetime.utcnow()
        return self.password_reset_token
    
    def verify_email(self, token):
        """Verify email with token and mark as verified"""
        if self.email_verification_token == token:
            self.email_verified = True
            self.email_verification_token = None
            self.email_verification_sent_at = None
            return True
        return False
    
    def reset_password_with_token(self, token, new_password):
        """Reset password using token"""
        if self.password_reset_token == token:
            # Check if token is not too old (24 hours)
            if self.password_reset_sent_at and \
               (datetime.utcnow() - self.password_reset_sent_at).total_seconds() < 86400:
                self.set_password(new_password)
                self.password_reset_token = None
                self.password_reset_sent_at = None
                return True
        return False
    
    def is_favourite(self, recipe):
        return recipe in self.favourites
    
    def add_favourite(self, recipe):
        if not self.is_favourite(recipe):
            self.favourites.append(recipe)
    
    def remove_favourite(self, recipe):
        if self.is_favourite(recipe):
            self.favourites.remove(recipe)
    
    # Subscription management methods
    def can_add_recipe(self):
        """Check if user can add more recipes based on their plan"""
        if self.current_plan == 'Free':
            recipe_count = Recipe.query.filter_by(user_id=self.id).count()
            return recipe_count < 10
        return True  # Home plan has unlimited recipes
    
    def get_recipe_limit(self):
        """Get the recipe limit for the user's current plan"""
        limits = {
            'Free': 10,
            'Home': None,  # Unlimited
        }
        return limits.get(self.current_plan, 10)
    
    def get_recipe_count(self):
        """Get the current number of recipes for this user"""
        return Recipe.query.filter_by(user_id=self.id).count()
    
    def is_on_trial(self):
        """Check if user is currently on a trial"""
        if not self.trial_end:
            return False
        return datetime.utcnow() < self.trial_end
    
    def days_left_in_trial(self):
        """Get days remaining in trial"""
        if not self.is_on_trial():
            return 0
        return (self.trial_end - datetime.utcnow()).days
    
    def can_access_feature(self, feature):
        """Check if user can access a specific feature based on their plan."""
        return feature in get_available_features(self.current_plan)
    
    # Family connection methods removed as only supporting Home users now
    
    def __repr__(self):
        return f'<User {self.username}>'

    def get_default_recipe_privacy(self):
        """Get the default privacy setting for new recipes based on user's plan"""
        if self.current_plan == 'Free':
            return True  # Free users' recipes are private by default
        return False  # Paid users' recipes are public by default
    
    def can_set_recipe_privacy(self):
        """Check if user can control recipe privacy settings"""
        return self.can_access_feature('private_recipes')
    
    def can_view_private_recipes(self):
        """Check if user can view private recipes from other users"""
        # Paid users can see all recipes (public and private from free users)
        # Free users can only see public recipes and their own private recipes
        return self.current_plan != 'Free'
    
    def get_profile_image_url(self):
        """Get the URL for user's profile image or default avatar"""
        if self.profile_image:
            from recipe_app.utils.image_storage import ImageStorageManager
            return ImageStorageManager.get_image_url(self.profile_image, 'profiles')
        else:
            # Generate a default avatar using initials
            return self.get_default_avatar_url()
    
    def get_default_avatar_url(self):
        """Generate a default avatar URL based on user initials"""
        # Create a deterministic color based on username
        import hashlib
        hash_object = hashlib.md5(self.username.encode())
        color_value = int(hash_object.hexdigest()[:6], 16)
        colors = [
            '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
            '#1abc9c', '#e67e22', '#34495e', '#f1c40f', '#95a5a6'
        ]
        color = colors[color_value % len(colors)]
        
        # Get initials
        initials = self.get_display_initials()
        
        # Return a data URL for a simple SVG avatar
        return f"data:image/svg+xml;base64,{self._generate_avatar_svg(initials, color)}"
    
    def get_display_initials(self):
        """Get user initials for avatar display"""
        if self.display_name:
            name_parts = self.display_name.strip().split()
            if len(name_parts) >= 2:
                return f"{name_parts[0][0]}{name_parts[-1][0]}".upper()
            elif name_parts:
                return name_parts[0][:2].upper()
        
        # Fallback to username
        return self.username[:2].upper() if len(self.username) >= 2 else self.username.upper()
    
    def _generate_avatar_svg(self, initials, color):
        """Generate base64 encoded SVG for default avatar"""
        import base64
        svg = f'''<svg width="64" height="64" xmlns="http://www.w3.org/2000/svg">
            <circle cx="32" cy="32" r="32" fill="{color}"/>
            <text x="32" y="38" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-size="24" font-weight="bold">{initials}</text>
        </svg>'''
        return base64.b64encode(svg.encode()).decode()
    
    def get_display_name_or_username(self):
        """Get display name if set, otherwise username"""
        return self.display_name if self.display_name else self.username
    
    def get_author_stamp_html(self, size='sm'):
        """Generate HTML for author stamp (avatar + name)"""
        from flask import url_for
        
        sizes = {
            'xs': {'img': '20px', 'text': 'small'},
            'sm': {'img': '32px', 'text': 'small'},
            'md': {'img': '48px', 'text': ''},
            'lg': {'img': '64px', 'text': 'h6'}
        }
        
        size_config = sizes.get(size, sizes['sm'])
        
        return f'''
        <div class="d-flex align-items-center author-stamp">
            <img src="{self.get_profile_image_url()}" 
                 alt="{self.get_display_name_or_username()}" 
                 class="rounded-circle me-2" 
                 style="width: {size_config['img']}; height: {size_config['img']}; object-fit: cover;">
            <span class="{size_config['text']} mb-0">{self.get_display_name_or_username()}</span>
        </div>
        '''
    
    # ============================================================================
    # FAMILY-RELATED METHODS (Phase 3)
    # ============================================================================
    
    def get_family_account(self):
        """Get user's family account (either owned or member of)"""
        # Import here to avoid circular imports
        from recipe_app.models.family_models import FamilyAccount, FamilyMember
        
        # Check if user owns a family account
        owned_family = FamilyAccount.query.filter_by(primary_user_id=self.id).first()
        if owned_family:
            return owned_family
        
        # Check if user is a member of a family account
        family_membership = FamilyMember.query.filter_by(user_id=self.id).first()
        if family_membership:
            return family_membership.family
        
        return None
    
    def is_family_admin(self):
        """Check if user is family account administrator"""
        from recipe_app.models.family_models import FamilyAccount
        
        owned_family = FamilyAccount.query.filter_by(primary_user_id=self.id).first()
        return owned_family is not None
    
    def get_family_role(self):
        """Get user's role in family account"""
        from recipe_app.models.family_models import FamilyAccount, FamilyMember
        
        # Check if user owns the family account (admin)
        owned_family = FamilyAccount.query.filter_by(primary_user_id=self.id).first()
        if owned_family:
            return 'admin'
        
        # Check if user is a member
        family_membership = FamilyMember.query.filter_by(user_id=self.id).first()
        if family_membership:
            return family_membership.role
        
        return None
    
    def get_family_member_record(self):
        """Get user's FamilyMember record"""
        from recipe_app.models.family_models import FamilyMember
        
        return FamilyMember.query.filter_by(user_id=self.id).first()
    
    def can_manage_family_member(self, target_member):
        """Check if user can manage another family member"""
        family = self.get_family_account()
        if not family:
            return False
        
        current_role = self.get_family_role()
        if current_role == 'admin':
            return True
        
        if current_role == 'parent' and target_member.role == 'child':
            return True
        
        return False
    
    def has_parental_controls(self):
        """Check if user (child) has parental controls applied"""
        from recipe_app.models.family_models import ParentalControl
        
        current_member = self.get_family_member_record()
        if not current_member or current_member.role != 'child':
            return False
        
        parental_controls = ParentalControl.query.filter_by(
            child_id=current_member.id,
            is_active=True
        ).first()
        
        return parental_controls is not None
    
    def get_parental_controls(self):
        """Get active parental controls for user (if child)"""
        from recipe_app.models.family_models import ParentalControl
        
        current_member = self.get_family_member_record()
        if not current_member or current_member.role != 'child':
            return None
        
        return ParentalControl.query.filter_by(
            child_id=current_member.id,
            is_active=True
        ).first()
    

# Association tables
recipe_tags = db.Table('recipe_tags',
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

user_favourites = db.Table('user_favourites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True)
)

# Community feature association tables
recipe_collections = db.Table('recipe_collections',
    db.Column('collection_id', db.Integer, db.ForeignKey('recipe_collection.id'), primary_key=True),
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True)
)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.Text)
    ingredients = db.Column(db.Text, nullable=False)
    method = db.Column(db.Text, nullable=False)
    prep_time = db.Column(db.Integer)  # in minutes
    cook_time = db.Column(db.Integer)  # in minutes
    servings = db.Column(db.Integer, default=4)
    difficulty = db.Column(db.String(20), default='Medium')  # Easy, Medium, Hard
    country = db.Column(db.String(50))  # Country of origin
    cuisine_type = db.Column(db.String(50))  # Italian, Chinese, etc.
    image_file = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_private = db.Column(db.Boolean, default=False)  # True for private, False for public
    
    # Moderation fields
    is_approved = db.Column(db.Boolean, default=True)  # Auto-approve for now
    is_featured = db.Column(db.Boolean, default=False)
    featured_at = db.Column(db.DateTime, nullable=True)
    moderation_notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('recipes', lazy=True))
    tags = db.relationship('Tag', secondary=recipe_tags, lazy='subquery',
                           backref=db.backref('recipes', lazy=True))
    
    @property
    def total_time(self):
        """Calculate total cooking time"""
        return (self.prep_time or 0) + (self.cook_time or 0)
    
    def can_be_viewed_by(self, user):
        """Check if this recipe can be viewed by the given user"""
        # Recipe owner can always view their own recipes
        if self.user_id == user.id:
            return True
            
        # Public recipes can be viewed by anyone
        if not self.is_private:
            return True
            
        # Private recipes can only be viewed by paid users (and the owner)
        return user.can_view_private_recipes()
    
    def get_privacy_label(self):
        """Get a human-readable privacy label"""
        if self.is_private:
            # Check if this is a free user's recipe (always private)
            if self.user.current_plan == 'Free':
                return "Limited Access"
            return "Private"
        return "Public"
    
    # Backwards-compatible alias: some callers expect `instructions`
    @property
    def instructions(self):
        return self.method

    @instructions.setter
    def instructions(self, value):
        self.method = value
    
    def __repr__(self):
        return f'<Recipe {self.title}'

    def average_rating(self):
        """Calculate average rating for this recipe"""
        if not self.reviews:
            return 0
        return sum(review.rating for review in self.reviews) / len(self.reviews)
    
    def rating_count(self):
        """Get total number of ratings"""
        return len(self.reviews)
    
    def get_rating_distribution(self):
        """Get distribution of ratings (1-5 stars)"""
        if not self.reviews:
            return {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for review in self.reviews:
            distribution[review.rating] += 1
        return distribution
    
    def is_featured(self):
        """Check if recipe qualifies as featured (high rating, multiple reviews)"""
        return self.average_rating() >= 4.0 and self.rating_count() >= 3

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    color = db.Column(db.String(7), default='#007bff')  # Hex color for UI
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Tag {self.name}>'

class RecipeRating(db.Model):
    """Allow users to rate recipes"""
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    
    user = db.relationship('User', backref=db.backref('ratings', lazy=True))
    recipe = db.relationship('Recipe', backref=db.backref('ratings', lazy=True))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'recipe_id', name='unique_user_recipe_rating'),)

class RecipeReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=True)  # For moderation
    
    recipe = db.relationship('Recipe', backref=db.backref('reviews', lazy=True))
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))


class RecipeComment(db.Model):
    """Threaded comments on recipes"""
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_id = db.Column(db.Integer, db.ForeignKey('recipe_comment.id'), nullable=True)

    recipe = db.relationship('Recipe', backref=db.backref('comments', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('recipe_comments', lazy=True))
    replies = db.relationship('RecipeComment', backref=db.backref('parent', remote_side=[id]), lazy='joined')

class RecipePhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    caption = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    recipe = db.relationship('Recipe', backref=db.backref('photos', lazy=True))
    user = db.relationship('User', backref=db.backref('recipe_photos', lazy=True))

class RecipeCollection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('collections', lazy=True))
    recipes = db.relationship('Recipe', secondary=recipe_collections, lazy='subquery',
                             backref=db.backref('collections', lazy=True))


class Follow(db.Model):
    """User following system"""
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Prevent following yourself and duplicate follows
    __table_args__ = (
        db.UniqueConstraint('follower_id', 'followed_id', name='unique_follow'),
        db.CheckConstraint('follower_id != followed_id', name='no_self_follow')
    )
    
    # Relationships
    follower = db.relationship('User', foreign_keys=[follower_id], backref='following')
    followed = db.relationship('User', foreign_keys=[followed_id], backref='followers')


class RecipeConversion(db.Model):
    """Model to store converted recipes (serving adjustments and metric conversions)"""
    id = db.Column(db.Integer, primary_key=True)
    original_recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Conversion type and parameters
    conversion_type = db.Column(db.String(20), nullable=False)  # 'serving_adjust', 'metric', 'both'
    original_servings = db.Column(db.Integer, nullable=True)
    target_servings = db.Column(db.Integer, nullable=True)
    is_metric_converted = db.Column(db.Boolean, default=False)
    
    # Converted content
    converted_ingredients = db.Column(db.Text, nullable=False)
    converted_title = db.Column(db.String(200), nullable=False)  # e.g., "Original Recipe (6 servings, metric)"
    conversion_notes = db.Column(db.Text, nullable=True)  # Description of what was converted
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_saved = db.Column(db.Boolean, default=False)  # Whether user chose to save this conversion
    access_count = db.Column(db.Integer, default=0)  # How many times user accessed this conversion
    
    # Relationships
    original_recipe = db.relationship('Recipe', backref=db.backref('conversions', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('recipe_conversions', lazy=True))
    
    def __repr__(self):
        return f'<RecipeConversion {self.id}: {self.conversion_type} of Recipe {self.original_recipe_id}>'
    
    @property
    def display_title(self):
        """Generate a user-friendly title for the conversion"""
        base_title = self.original_recipe.title if self.original_recipe else "Recipe"
        
        parts = []
        if self.target_servings and self.target_servings != self.original_servings:
            parts.append(f"{self.target_servings} servings")
        if self.is_metric_converted:
            parts.append("metric")
            
        if parts:
            return f"{base_title} ({', '.join(parts)})"
        return base_title
    
    @property
    def conversion_summary(self):
        """Generate a summary of what was converted"""
        summary_parts = []
        
        if self.target_servings and self.target_servings != self.original_servings:
            multiplier = self.target_servings / self.original_servings if self.original_servings else 1
            summary_parts.append(f"Adjusted from {self.original_servings} to {self.target_servings} servings ({multiplier:.1f}x)")
            
        if self.is_metric_converted:
            summary_parts.append("Converted to metric measurements")
            
        return "; ".join(summary_parts) if summary_parts else "No conversions applied"


class ImageStorage(db.Model):
    """Model for storing images in database as BLOB data"""
    
    id = db.Column(db.String(32), primary_key=True)  # Unique identifier
    category = db.Column(db.String(20), nullable=False)  # 'profiles', 'recipes', etc.
    filename = db.Column(db.String(255), nullable=False)  # Original filename
    data = db.Column(db.Text, nullable=False)  # Base64 encoded image data
    mime_type = db.Column(db.String(50), nullable=False)  # MIME type of the image
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer, nullable=True)  # Size in bytes (for analytics)
    
    def __repr__(self):
        return f'<ImageStorage {self.id}: {self.category}/{self.filename}>'
    
    def get_data_url(self):
        """Get data URL for embedding in HTML"""
        return f"data:{self.mime_type};base64,{self.data}"
    
    def get_size_kb(self):
        """Get file size in KB"""
        if self.file_size:
            return round(self.file_size / 1024, 2)
        return 0


# ChatMessage model commented out - now using Tawk.to for live chat
# Uncomment if you need to preserve historical chat data or migrate to another system
#
# class ChatMessage(db.Model):
#     """Chat message model for live support chat"""
#     __tablename__ = 'chat_message'
#     
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
#     admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
#     message = db.Column(db.Text, nullable=False)
#     is_admin_message = db.Column(db.Boolean, default=False)
#     timestamp = db.Column(db.DateTime, default=datetime.utcnow)
#     session_id = db.Column(db.String(100), nullable=False)
#     is_read = db.Column(db.Boolean, default=False)
#     
#     # Relationships
#     user = db.relationship('User', foreign_keys=[user_id], backref='chat_messages')
#     admin = db.relationship('User', foreign_keys=[admin_id])
#     
#     def __repr__(self):
#         return f'<ChatMessage {self.id}: {self.user.username if self.user else "Unknown"} - {self.message[:50]}>'
    
    def to_dict(self):
        """Convert message to dictionary for JSON responses"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'admin_id': self.admin_id,
            'message': self.message,
            'is_admin_message': self.is_admin_message,
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'is_read': self.is_read,
            'username': self.admin.username if self.is_admin_message and self.admin else (self.user.username if self.user else 'Unknown')
        }


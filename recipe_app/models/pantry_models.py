"""
Pantry management models for inventory tracking
"""
from datetime import datetime, date, timedelta
from recipe_app.db import db
from sqlalchemy import func


class PantryCategory(db.Model):
    """Categories for organizing pantry items"""
    __tablename__ = 'pantry_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    icon = db.Column(db.String(50), default='fas fa-box')  # FontAwesome icon
    color = db.Column(db.String(20), default='#6c757d')  # Bootstrap color
    sort_order = db.Column(db.Integer, default=0)
    
    # Relationship
    items = db.relationship('PantryItem', backref='category', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PantryCategory {self.name}>'
    
    @staticmethod
    def get_default_categories():
        """Get default pantry categories"""
        return [
            {'name': 'Dairy & Eggs', 'icon': 'fas fa-cheese', 'color': '#ffc107'},
            {'name': 'Meat & Seafood', 'icon': 'fas fa-fish', 'color': '#dc3545'},
            {'name': 'Fresh Produce', 'icon': 'fas fa-apple-alt', 'color': '#28a745'},
            {'name': 'Pantry Staples', 'icon': 'fas fa-box', 'color': '#6f42c1'},
            {'name': 'Frozen Foods', 'icon': 'fas fa-snowflake', 'color': '#17a2b8'},
            {'name': 'Beverages', 'icon': 'fas fa-glass-whiskey', 'color': '#fd7e14'},
            {'name': 'Snacks', 'icon': 'fas fa-cookie-bite', 'color': '#e83e8c'},
            {'name': 'Spices & Herbs', 'icon': 'fas fa-pepper-hot', 'color': '#20c997'},
            {'name': 'Baking Supplies', 'icon': 'fas fa-birthday-cake', 'color': '#6f42c1'},
            {'name': 'Condiments', 'icon': 'fas fa-wine-bottle', 'color': '#6c757d'}
        ]


class PantryItem(db.Model):
    """Individual pantry items with quantities and expiry tracking"""
    __tablename__ = 'pantry_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Item details
    name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50))
    barcode = db.Column(db.String(50))  # For scanning integration
    
    # Quantity tracking
    current_quantity = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(20), nullable=False, default='units')  # units, kg, g, L, ml, etc.
    minimum_quantity = db.Column(db.Float, default=1.0)  # Alert threshold
    ideal_quantity = db.Column(db.Float, default=5.0)  # Recommended stock level
    
    # Location and organization
    category_id = db.Column(db.Integer, db.ForeignKey('pantry_categories.id'), nullable=True)
    storage_location = db.Column(db.String(50))  # Fridge, Freezer, Cupboard, etc.
    
    # Expiry and freshness
    expiry_date = db.Column(db.Date)
    days_until_expiry_alert = db.Column(db.Integer, default=7)  # Alert X days before expiry
    
    # Cost tracking (optional)
    cost_per_unit = db.Column(db.Float)
    total_cost = db.Column(db.Float)
    
    # Purchase tracking
    last_purchased = db.Column(db.Date)
    purchase_frequency_days = db.Column(db.Integer)  # How often this item is bought
    
    # Metadata
    notes = db.Column(db.Text)
    is_running_low = db.Column(db.Boolean, default=False, index=True)
    is_expired = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    usage_logs = db.relationship('PantryUsageLog', backref='item', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PantryItem {self.name} - {self.current_quantity} {self.unit}>'
    
    @property
    def is_low_stock(self):
        """Check if item is running low"""
        return self.current_quantity <= self.minimum_quantity
    
    @property
    def is_expiring_soon(self):
        """Check if item is expiring soon"""
        if not self.expiry_date:
            return False
        days_to_expiry = (self.expiry_date - date.today()).days
        return days_to_expiry <= self.days_until_expiry_alert
    
    @property
    def days_until_expiry(self):
        """Get days until expiry"""
        if not self.expiry_date:
            return None
        return (self.expiry_date - date.today()).days
    
    @property
    def stock_status(self):
        """Get stock status as string"""
        if self.current_quantity <= 0:
            return 'out_of_stock'
        elif self.is_low_stock:
            return 'low_stock'
        elif self.current_quantity >= self.ideal_quantity:
            return 'well_stocked'
        else:
            return 'adequate'
    
    def update_quantity(self, amount, operation='subtract', reason='used_in_recipe'):
        """Update item quantity and log the change"""
        old_quantity = self.current_quantity
        
        if operation == 'subtract':
            self.current_quantity = max(0, self.current_quantity - amount)
        elif operation == 'add':
            self.current_quantity += amount
        elif operation == 'set':
            self.current_quantity = amount
        
        # Update status flags
        self.is_running_low = self.is_low_stock
        
        # Create usage log
        log = PantryUsageLog(
            item_id=self.id,
            user_id=self.user_id,
            quantity_change=self.current_quantity - old_quantity,
            old_quantity=old_quantity,
            new_quantity=self.current_quantity,
            reason=reason,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'current_quantity': self.current_quantity,
            'unit': self.unit,
            'minimum_quantity': self.minimum_quantity,
            'ideal_quantity': self.ideal_quantity,
            'category': self.category.name if self.category else None,
            'storage_location': self.storage_location,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_low_stock': self.is_low_stock,
            'is_expiring_soon': self.is_expiring_soon,
            'days_until_expiry': self.days_until_expiry,
            'stock_status': self.stock_status,
            'last_purchased': self.last_purchased.isoformat() if self.last_purchased else None,
            'cost_per_unit': self.cost_per_unit,
            'notes': self.notes
        }


class PantryUsageLog(db.Model):
    """Log of pantry item usage for tracking and analytics"""
    __tablename__ = 'pantry_usage_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('pantry_items.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Change details
    quantity_change = db.Column(db.Float, nullable=False)  # Positive for additions, negative for usage
    old_quantity = db.Column(db.Float, nullable=False)
    new_quantity = db.Column(db.Float, nullable=False)
    
    # Context
    reason = db.Column(db.String(50), nullable=False)  # 'used_in_recipe', 'manual_adjustment', 'purchase', 'expired'
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=True)  # If used in a recipe
    meal_plan_entry_id = db.Column(db.Integer, nullable=True)  # If used from meal planning
    
    # Metadata
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f'<PantryUsageLog {self.item_id} - {self.quantity_change} at {self.timestamp}>'


class ShoppingListItem(db.Model):
    """Shopping list items generated from low stock and meal planning"""
    __tablename__ = 'shopping_list_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Item details
    item_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    quantity_needed = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    
    # Source tracking
    source = db.Column(db.String(30), nullable=False)  # 'low_stock', 'meal_plan', 'manual'
    pantry_item_id = db.Column(db.Integer, db.ForeignKey('pantry_items.id'), nullable=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=True)
    meal_plan_id = db.Column(db.Integer, nullable=True)
    
    # Shopping details
    is_purchased = db.Column(db.Boolean, default=False, index=True)
    estimated_cost = db.Column(db.Float)
    actual_cost = db.Column(db.Float)
    store_section = db.Column(db.String(50))  # Produce, Dairy, etc.
    
    # Priority and organization
    priority = db.Column(db.Integer, default=3)  # 1=urgent, 5=low priority
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    purchased_at = db.Column(db.DateTime)
    
    # Relationships
    pantry_item = db.relationship('PantryItem', backref='shopping_items')
    
    def __repr__(self):
        return f'<ShoppingListItem {self.item_name} - {self.quantity_needed} {self.unit}>'
    
    def mark_as_purchased(self, actual_cost=None):
        """Mark item as purchased and update pantry if linked"""
        self.is_purchased = True
        self.purchased_at = datetime.utcnow()
        if actual_cost:
            self.actual_cost = actual_cost
        
        # If linked to pantry item, update the pantry quantity
        if self.pantry_item_id:
            pantry_item = PantryItem.query.get(self.pantry_item_id)
            if pantry_item:
                pantry_item.update_quantity(
                    self.quantity_needed, 
                    operation='add', 
                    reason='purchased'
                )
                pantry_item.last_purchased = date.today()
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'item_name': self.item_name,
            'category': self.category,
            'quantity_needed': self.quantity_needed,
            'unit': self.unit,
            'source': self.source,
            'is_purchased': self.is_purchased,
            'priority': self.priority,
            'estimated_cost': self.estimated_cost,
            'actual_cost': self.actual_cost,
            'store_section': self.store_section,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'purchased_at': self.purchased_at.isoformat() if self.purchased_at else None
        }


class WeeklyShoppingList(db.Model):
    """Weekly shopping list for meal planning ahead"""
    __tablename__ = 'weekly_shopping_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Week details
    week_start_date = db.Column(db.Date, nullable=False, index=True)  # Monday of the week
    week_end_date = db.Column(db.Date, nullable=False)  # Sunday of the week
    week_label = db.Column(db.String(50))  # e.g., "Week of Dec 16-22, 2024"
    
    # Planning details
    status = db.Column(db.String(20), default='planning')  # planning, active, completed
    budget_target = db.Column(db.Float)
    total_estimated_cost = db.Column(db.Float, default=0.0)
    total_actual_cost = db.Column(db.Float, default=0.0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('WeeklyShoppingItem', backref='weekly_list', 
                           lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<WeeklyShoppingList {self.week_label} for user {self.user_id}>'
    
    @staticmethod
    def get_week_label(week_start):
        """Generate a readable week label"""
        week_end = week_start + timedelta(days=6)
        return f"Week of {week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
    
    def get_items_by_category(self):
        """Get items grouped by category"""
        items = self.items.filter_by(is_purchased=False).all()
        categories = {}
        for item in items:
            category = item.category or 'Other'
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        return categories
    
    def update_totals(self):
        """Update total costs based on items"""
        self.total_estimated_cost = sum(
            item.estimated_cost or 0 for item in self.items
        )
        self.total_actual_cost = sum(
            item.actual_cost or 0 for item in self.items if item.is_purchased
        )


class WeeklyShoppingItem(db.Model):
    """Items for weekly shopping lists"""
    __tablename__ = 'weekly_shopping_items'
    
    id = db.Column(db.Integer, primary_key=True)
    weekly_list_id = db.Column(db.Integer, db.ForeignKey('weekly_shopping_lists.id'), nullable=False)
    
    # Item details (similar to ShoppingListItem but for specific weeks)
    item_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    quantity_needed = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    
    # Source tracking
    source = db.Column(db.String(30), nullable=False)  # 'meal_plan', 'barcode_scan', 'manual'
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=True)
    meal_date = db.Column(db.Date)  # Which day in the week this is for
    
    # Shopping details
    is_purchased = db.Column(db.Boolean, default=False, index=True)
    estimated_cost = db.Column(db.Float)
    actual_cost = db.Column(db.Float)
    store_section = db.Column(db.String(50))
    
    # Priority and organization
    priority = db.Column(db.Integer, default=3)
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    purchased_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<WeeklyShoppingItem {self.item_name} for week {self.weekly_list_id}>'
    
    def mark_as_purchased(self, actual_cost=None):
        """Mark item as purchased"""
        self.is_purchased = True
        self.purchased_at = datetime.utcnow()
        if actual_cost:
            self.actual_cost = actual_cost
            
        # Update weekly list totals
        if self.weekly_list:
            self.weekly_list.update_totals()
    
    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'item_name': self.item_name,
            'category': self.category,
            'quantity_needed': self.quantity_needed,
            'unit': self.unit,
            'source': self.source,
            'meal_date': self.meal_date.isoformat() if self.meal_date else None,
            'is_purchased': self.is_purchased,
            'priority': self.priority,
            'estimated_cost': self.estimated_cost,
            'actual_cost': self.actual_cost,
            'store_section': self.store_section,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'purchased_at': self.purchased_at.isoformat() if self.purchased_at else None
        }

"""
User-Contributed Price Database Models
Legal and safe alternative to web scraping - community-driven pricing
"""
from datetime import datetime
from recipe_app.db import db
from sqlalchemy import Index

class UserContributedPrice(db.Model):
    """
    User-submitted price data - append-only for data integrity
    Users can add prices but cannot modify or delete existing entries
    """
    __tablename__ = 'user_contributed_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Product Information
    shop_name = db.Column(db.String(100), nullable=False, index=True)
    brand_name = db.Column(db.String(100), nullable=True)  # Optional, some items don't have brands
    item_name = db.Column(db.String(200), nullable=False, index=True)
    size = db.Column(db.String(50), nullable=True)  # e.g., "500g", "1L", "6 pack"
    
    # Price Information
    price = db.Column(db.Numeric(10, 2), nullable=False)
    price_per_unit = db.Column(db.Numeric(10, 2), nullable=True)  # Calculated price per kg/L etc
    
    # Location Information
    shop_location = db.Column(db.String(200), nullable=False)  # User-entered location
    postcode = db.Column(db.String(10), nullable=True, index=True)  # Auto-populated via API
    postcode_area = db.Column(db.String(4), nullable=True, index=True)  # First part of postcode
    
    # Metadata
    submitted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Validation and Quality Control
    is_verified = db.Column(db.Boolean, default=False, index=True)
    verification_count = db.Column(db.Integer, default=0)  # How many users have confirmed this price
    is_flagged = db.Column(db.Boolean, default=False)  # Flagged for review
    flag_reason = db.Column(db.String(100), nullable=True)
    
    # Data Sanitization
    normalized_item_name = db.Column(db.String(200), nullable=False, index=True)  # Cleaned for searching
    normalized_shop_name = db.Column(db.String(100), nullable=False, index=True)  # Standardized shop names
    
    # Relationships
    submitter = db.relationship('User', backref=db.backref('submitted_prices', lazy='dynamic'))
    
    # Composite indexes for efficient querying
    __table_args__ = (
        Index('idx_item_shop_location', 'normalized_item_name', 'normalized_shop_name', 'postcode_area'),
        Index('idx_recent_verified', 'submitted_at', 'is_verified'),
        Index('idx_location_item', 'postcode_area', 'normalized_item_name'),
    )
    
    def __repr__(self):
        return f'<UserContributedPrice {self.item_name} at {self.shop_name}: £{self.price}>'

class PriceVerification(db.Model):
    """
    Track user verifications of submitted prices
    Helps build confidence in price accuracy
    """
    __tablename__ = 'price_verifications'
    
    id = db.Column(db.Integer, primary_key=True)
    price_id = db.Column(db.Integer, db.ForeignKey('user_contributed_prices.id'), nullable=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    verified_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Verification details
    is_accurate = db.Column(db.Boolean, nullable=False)  # True if price is confirmed accurate
    comment = db.Column(db.String(200), nullable=True)  # Optional comment
    
    # Relationships
    price = db.relationship('UserContributedPrice', backref=db.backref('verifications', lazy='dynamic'))
    verifier = db.relationship('User', backref=db.backref('price_verifications', lazy='dynamic'))
    
    # Ensure users can only verify each price once
    __table_args__ = (
        db.UniqueConstraint('price_id', 'verified_by', name='unique_user_verification'),
    )

class ShopLocation(db.Model):
    """
    Standardized shop locations with postcode data
    Auto-populated via postcode lookup API
    """
    __tablename__ = 'shop_locations'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Location Details
    shop_name = db.Column(db.String(100), nullable=False)
    normalized_shop_name = db.Column(db.String(100), nullable=False, index=True)
    
    # Address Information
    address_line = db.Column(db.String(200), nullable=False)
    postcode = db.Column(db.String(10), nullable=False, index=True)
    postcode_area = db.Column(db.String(4), nullable=False, index=True)
    
    # Geographic Data (from API)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Administrative Areas
    town = db.Column(db.String(100), nullable=True)
    county = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    verified = db.Column(db.Boolean, default=False)  # Whether location data is verified
    
    # Chain information
    chain_name = db.Column(db.String(100), nullable=True)  # e.g., "Tesco", "Sainsbury's"
    store_type = db.Column(db.String(50), nullable=True)   # e.g., "Express", "Extra", "Local"
    
    def __repr__(self):
        return f'<ShopLocation {self.shop_name} - {self.postcode}>'

class PriceDataSanitizer:
    """
    Utility class for sanitizing and normalizing user-submitted price data
    """
    
    # Standardized shop name mappings
    SHOP_NAME_MAPPINGS = {
        'tesco': 'Tesco',
        'tesco express': 'Tesco Express',
        'tesco extra': 'Tesco Extra',
        'tesco metro': 'Tesco Metro',
        'sainsburys': "Sainsbury's",
        'sainsbury\'s': "Sainsbury's",
        'sainsburys local': "Sainsbury's Local",
        'asda': 'ASDA',
        'morrisons': 'Morrisons',
        'aldi': 'ALDI',
        'lidl': 'Lidl',
        'co-op': 'Co-op',
        'coop': 'Co-op',
        'waitrose': 'Waitrose',
        'marks and spencer': 'M&S',
        'm&s': 'M&S',
        'iceland': 'Iceland',
        'farmfoods': 'Farmfoods',
        'spar': 'SPAR',
        'costco': 'Costco',
    }
    
    @staticmethod
    def normalize_shop_name(shop_name: str) -> str:
        """Standardize shop name"""
        if not shop_name:
            return ""
        
        # Clean and lowercase
        normalized = shop_name.strip().lower()
        
        # Apply mappings
        return PriceDataSanitizer.SHOP_NAME_MAPPINGS.get(normalized, shop_name.strip().title())
    
    @staticmethod
    def normalize_item_name(item_name: str) -> str:
        """Standardize item name for consistent searching"""
        if not item_name:
            return ""
        
        # Clean up the name
        normalized = item_name.strip().lower()
        
        # Remove common prefixes/suffixes that don't affect the core product
        prefixes_to_remove = ['own brand', 'store brand', 'value', 'basic', 'finest', 'taste the difference']
        suffixes_to_remove = ['pack', 'multipack', 'bundle']
        
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix + ' '):
                normalized = normalized[len(prefix + ' '):]
        
        for suffix in suffixes_to_remove:
            if normalized.endswith(' ' + suffix):
                normalized = normalized[:-len(' ' + suffix)]
        
        # Standardize common variations
        replacements = {
            'semi skimmed milk': 'semi-skimmed milk',
            'whole milk': 'whole milk',
            'chicken breast': 'chicken breast',
            'beef mince': 'beef mince',
            'potatoes': 'potatoes',
            'potato': 'potatoes',
            'onions': 'onions',
            'onion': 'onions',
        }
        
        for old, new in replacements.items():
            if old in normalized:
                normalized = normalized.replace(old, new)
        
        return normalized.strip()
    
    @staticmethod
    def extract_postcode_area(postcode: str) -> str:
        """Extract postcode area (first 1-2 letters) for regional grouping"""
        if not postcode:
            return ""
        
        # Remove spaces and convert to uppercase
        clean_postcode = postcode.replace(' ', '').upper()
        
        # Extract area (first 1-2 letters)
        import re
        area_match = re.match(r'^([A-Z]{1,2})', clean_postcode)
        if area_match:
            return area_match.group(1)
        
        return ""
    
    @staticmethod
    def validate_price(price_str: str) -> float:
        """Validate and convert price string to float"""
        if not price_str:
            raise ValueError("Price cannot be empty")
        
        # Remove currency symbols and clean
        clean_price = price_str.replace('£', '').replace(',', '').strip()
        
        try:
            price = float(clean_price)
            
            # Reasonable bounds checking
            if price <= 0:
                raise ValueError("Price must be positive")
            if price > 1000:  # £1000 seems like a reasonable upper limit for grocery items
                raise ValueError("Price seems unreasonably high")
            
            return round(price, 2)
            
        except ValueError as e:
            raise ValueError(f"Invalid price format: {e}")
    
    @staticmethod
    def calculate_price_per_unit(price: float, size: str) -> float:
        """Calculate price per standard unit (kg, L, etc.)"""
        if not size:
            return None
        
        # Extract numeric value and unit from size string
        import re
        
        # Pattern to match number + unit
        pattern = r'(\d+(?:\.\d+)?)\s*(g|kg|ml|l|litre|liter|oz|lb|pack|each|count)'
        match = re.search(pattern, size.lower())
        
        if not match:
            return None
        
        amount = float(match.group(1))
        unit = match.group(2)
        
        # Convert to standard units (per kg or per litre)
        conversions = {
            'g': 1000,      # 1000g = 1kg
            'kg': 1,        # already in kg
            'ml': 1000,     # 1000ml = 1L
            'l': 1,         # already in L
            'litre': 1,     # already in L
            'liter': 1,     # already in L
            'oz': 35.274,   # ~35.274 oz = 1kg
            'lb': 2.205,    # ~2.205 lb = 1kg
        }
        
        if unit in conversions:
            standard_amount = amount / conversions[unit]
            return round(price / standard_amount, 2)
        
        return None

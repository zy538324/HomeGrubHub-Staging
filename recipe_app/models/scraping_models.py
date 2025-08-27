"""
Database models for storing scraped supermarket price data
"""
from recipe_app.db import db
from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON

class ScrapedProduct(db.Model):
    """Model for storing scraped product information"""
    __tablename__ = 'scraped_products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    normalized_name = db.Column(db.String(200), nullable=False, index=True)  # For matching
    category = db.Column(db.String(50), index=True)
    brand = db.Column(db.String(100))
    description = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    prices = db.relationship('ScrapedPrice', backref='product', lazy='dynamic', 
                           cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ScrapedProduct {self.name}>'
    
    def get_latest_prices(self):
        """Get the most recent prices from all stores"""
        from sqlalchemy import func
        
        # Get the latest price for each store
        latest_prices = db.session.query(ScrapedPrice)\
            .filter(ScrapedPrice.product_id == self.id)\
            .group_by(ScrapedPrice.store)\
            .having(ScrapedPrice.scraped_at == func.max(ScrapedPrice.scraped_at))\
            .all()
        
        return latest_prices
    
    def get_price_history(self, days=30):
        """Get price history for the last N days"""
        from datetime import timedelta
        
        since_date = datetime.utcnow() - timedelta(days=days)
        return self.prices.filter(ScrapedPrice.scraped_at >= since_date)\
                         .order_by(ScrapedPrice.scraped_at.desc()).all()
    
    def get_average_price(self, store=None):
        """Get average price across stores or for specific store"""
        query = self.prices
        
        if store:
            query = query.filter(ScrapedPrice.store == store)
        
        prices = query.filter(ScrapedPrice.price.isnot(None)).all()
        
        if not prices:
            return None
        
        return sum(p.price for p in prices) / len(prices)


class ScrapedPrice(db.Model):
    """Model for storing individual price records"""
    __tablename__ = 'scraped_prices'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('scraped_products.id'), nullable=False)
    
    # Store information
    store = db.Column(db.String(50), nullable=False, index=True)
    store_location = db.Column(db.String(100))  # For regional pricing
    
    # Price information
    price = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    price_per_unit = db.Column(db.Numeric(10, 2))  # Standardized price per kg/litre
    
    # Promotion information
    original_price = db.Column(db.Numeric(10, 2))  # Price before discount
    promotion_text = db.Column(db.String(200))
    is_on_promotion = db.Column(db.Boolean, default=False, index=True)
    
    # Availability
    availability = db.Column(db.String(20), default='in_stock')  # in_stock, out_of_stock, limited
    
    # Metadata
    product_url = db.Column(db.String(500))
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    scraper_version = db.Column(db.String(20), default='1.0')
    
    # Additional product data (JSON field for flexibility)
    extra_data = db.Column(JSON)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_store_scraped_at', 'store', 'scraped_at'),
        db.Index('idx_product_store_scraped_at', 'product_id', 'store', 'scraped_at'),
    )
    
    def __repr__(self):
        return f'<ScrapedPrice {self.store}: £{self.price}>'
    
    @property
    def savings_amount(self):
        """Calculate savings if on promotion"""
        if self.is_on_promotion and self.original_price:
            return float(self.original_price - self.price)
        return 0.0
    
    @property
    def savings_percentage(self):
        """Calculate savings percentage if on promotion"""
        if self.is_on_promotion and self.original_price and self.original_price > 0:
            return ((self.original_price - self.price) / self.original_price) * 100
        return 0.0


class ScrapingLog(db.Model):
    """Model for tracking scraping activities and performance"""
    __tablename__ = 'scraping_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Scraping session info
    session_id = db.Column(db.String(50), nullable=False, index=True)
    store = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50))
    search_term = db.Column(db.String(200))
    
    # Results
    products_found = db.Column(db.Integer, default=0)
    products_saved = db.Column(db.Integer, default=0)
    errors_count = db.Column(db.Integer, default=0)
    
    # Performance metrics
    duration_seconds = db.Column(db.Float)
    pages_scraped = db.Column(db.Integer, default=0)
    requests_made = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    error_message = db.Column(db.Text)
    
    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<ScrapingLog {self.store} - {self.status}>'


class PriceAlert(db.Model):
    """Model for user price alerts"""
    __tablename__ = 'price_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('scraped_products.id'), nullable=False)
    
    # Alert conditions
    target_price = db.Column(db.Numeric(10, 2), nullable=False)
    store_preference = db.Column(db.String(50))  # Specific store or 'any'
    alert_type = db.Column(db.String(20), default='price_drop')  # price_drop, back_in_stock
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    last_triggered = db.Column(db.DateTime)
    times_triggered = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='price_alerts')
    product = db.relationship('ScrapedProduct', backref='alerts')
    
    def __repr__(self):
        return f'<PriceAlert {self.product.name} <= £{self.target_price}>'


# Helper functions for database operations

def normalize_product_name(name: str) -> str:
    """Normalize product name for matching"""
    import re
    
    # Convert to lowercase
    normalized = name.lower()
    
    # Remove brand names and common qualifiers
    remove_terms = [
        r'\b(organic|free range|fresh|frozen|tinned|canned)\b',
        r'\b(large|medium|small|extra)\b',
        r'\b(pack|multipack|value|own brand)\b',
        r'\([^)]*\)',  # Remove text in parentheses
        r'\d+\s*(g|kg|ml|l|litre|gram|grams)\b',  # Remove weights
    ]
    
    for term in remove_terms:
        normalized = re.sub(term, '', normalized)
    
    # Clean up spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def find_or_create_product(name: str, category: str = None) -> ScrapedProduct:
    """Find existing product or create new one"""
    normalized_name = normalize_product_name(name)
    
    # Try to find existing product
    product = ScrapedProduct.query.filter_by(normalized_name=normalized_name).first()
    
    if not product:
        product = ScrapedProduct(
            name=name,
            normalized_name=normalized_name,
            category=category
        )
        db.session.add(product)
        db.session.flush()  # Get ID without committing
    
    return product


def save_scraped_price(product_price, category: str = None) -> ScrapedPrice:
    """Save a scraped price to the database"""
    from recipe_app.utils.supermarket_scraper import ProductPrice
    
    # Find or create product
    product = find_or_create_product(product_price.name, category)
    
    # Create price record
    price_record = ScrapedPrice(
        product_id=product.id,
        store=product_price.store,
        price=product_price.price,
        unit=product_price.unit,
        promotion_text=product_price.promotion,
        is_on_promotion=bool(product_price.promotion),
        original_price=product_price.original_price,
        availability=product_price.availability,
        product_url=product_price.url,
        scraped_at=product_price.scraped_at
    )
    
    db.session.add(price_record)
    return price_record

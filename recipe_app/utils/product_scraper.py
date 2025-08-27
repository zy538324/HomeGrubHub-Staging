"""
Product price checking service
Integrates with the scraping system to provide current price data
"""
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from recipe_app.db import db
from recipe_app.models.scraping_models import ScrapedProduct, ScrapedPrice

@dataclass
class ProductPrice:
    """Product price data"""
    name: str
    price: float
    store: str
    scraped_at: datetime = None

def check_product_prices(product_name: str, max_age_hours: int = 24) -> List[ProductPrice]:
    """
    Check current prices for a product across all stores
    
    Args:
        product_name: Name of the product to search for
        max_age_hours: Maximum age of price data to consider (default 24 hours)
    
    Returns:
        List of ProductPrice objects with current pricing data
    """
    try:
        # Normalize product name for searching
        normalized_name = product_name.lower().strip()
        
        # Find matching products in our database
        # Try exact match first, then partial matches
        products = ScrapedProduct.query.filter(
            db.func.lower(ScrapedProduct.name).like(f'%{normalized_name}%')
        ).limit(10).all()
        
        if not products:
            # If no products found, return empty list
            # In a real implementation, this could trigger new scraping
            return []
        
        # Get recent prices for matching products
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        all_prices = []
        
        for product in products:
            recent_prices = ScrapedPrice.query.filter(
                ScrapedPrice.product_id == product.id,
                ScrapedPrice.scraped_at >= cutoff_time
            ).order_by(ScrapedPrice.scraped_at.desc()).all()
            
            # Group by store and get latest price for each store
            store_prices = {}
            for price in recent_prices:
                if price.store not in store_prices:
                    store_prices[price.store] = price
                elif price.scraped_at > store_prices[price.store].scraped_at:
                    store_prices[price.store] = price
            
            # Convert to ProductPrice objects
            for store, price_record in store_prices.items():
                all_prices.append(ProductPrice(
                    name=product.name,
                    price=float(price_record.price),
                    store=store,
                    scraped_at=price_record.scraped_at
                ))
        
        # Sort by price (cheapest first)
        all_prices.sort(key=lambda x: x.price)
        
        return all_prices
        
    except Exception as e:
        print(f"Error checking prices for {product_name}: {e}")
        return []

def get_cheapest_price(product_name: str) -> Optional[ProductPrice]:
    """Get the cheapest current price for a product"""
    prices = check_product_prices(product_name)
    return prices[0] if prices else None

def get_store_price(product_name: str, store: str) -> Optional[ProductPrice]:
    """Get the current price for a product at a specific store"""
    prices = check_product_prices(product_name)
    store_prices = [p for p in prices if p.store.lower() == store.lower()]
    return store_prices[0] if store_prices else None

def compare_prices(product_name: str) -> dict:
    """Get a comprehensive price comparison for a product"""
    prices = check_product_prices(product_name)
    
    if not prices:
        return {
            'product': product_name,
            'found': False,
            'message': 'No prices found for this product'
        }
    
    # Calculate statistics
    price_values = [p.price for p in prices]
    cheapest = min(prices, key=lambda x: x.price)
    most_expensive = max(prices, key=lambda x: x.price)
    average_price = sum(price_values) / len(price_values)
    
    # Group by store
    by_store = {}
    for price in prices:
        by_store[price.store] = {
            'price': price.price,
            'product_name': price.name,
            'last_updated': price.scraped_at.strftime('%Y-%m-%d %H:%M') if price.scraped_at else 'Recent'
        }
    
    return {
        'product': product_name,
        'found': True,
        'total_prices': len(prices),
        'cheapest': {
            'store': cheapest.store,
            'price': cheapest.price,
            'product_name': cheapest.name
        },
        'most_expensive': {
            'store': most_expensive.store,
            'price': most_expensive.price,
            'product_name': most_expensive.name
        },
        'average_price': round(average_price, 2),
        'price_range': round(most_expensive.price - cheapest.price, 2),
        'stores': by_store,
        'all_prices': [
            {
                'store': p.store,
                'price': p.price,
                'product_name': p.name,
                'last_updated': p.scraped_at.strftime('%Y-%m-%d %H:%M') if p.scraped_at else 'Recent'
            } for p in prices
        ]
    }

def search_products(query: str, limit: int = 20) -> List[dict]:
    """Search for products in the database"""
    try:
        normalized_query = query.lower().strip()
        
        products = ScrapedProduct.query.filter(
            db.func.lower(ScrapedProduct.name).like(f'%{normalized_query}%')
        ).limit(limit).all()
        
        results = []
        for product in products:
            # Get latest price info
            latest_price = ScrapedPrice.query.filter_by(
                product_id=product.id
            ).order_by(ScrapedPrice.scraped_at.desc()).first()
            
            results.append({
                'id': product.id,
                'name': product.name,
                'category': product.category,
                'brand': product.brand,
                'latest_price': float(latest_price.price) if latest_price else None,
                'latest_store': latest_price.store if latest_price else None,
                'last_updated': latest_price.scraped_at.strftime('%Y-%m-%d') if latest_price else None
            })
        
        return results
        
    except Exception as e:
        print(f"Error searching products: {e}")
        return []

def estimate_product_price(item) -> None:
    """Estimate and set the product's price using the cheapest available option"""
    try:
        cheapest = get_cheapest_price(item.name)
        if cheapest:
            item.estimated_price = float(cheapest.price)
    except Exception as e:
        print(f"Error estimating price for {item.name}: {e}")

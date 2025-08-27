"""
Dynamic Price Service
Scrapes prices on-demand based on user requests and location
"""
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from recipe_app.db import db
from recipe_app.models.scraping_models import ScrapedProduct, ScrapedPrice
from recipe_app.utils.supermarket_scraper import TescoScraper, SainsburysScraper
from recipe_app.utils.store_locator import store_locator
from recipe_app.utils.product_scraper import ProductPrice

class DynamicPriceService:
    """On-demand price scraping service"""
    
    def __init__(self):
        self.scrapers = {
            'tesco': TescoScraper(),
            'sainsburys': SainsburysScraper(),
        }
        self.cache_duration_hours = 24
    
    def get_cached_prices(self, product_name: str, max_age_hours: int = 24) -> List[ProductPrice]:
        """Check if we have recent cached prices"""
        from recipe_app.utils.product_scraper import check_product_prices
        return check_product_prices(product_name, max_age_hours)
    
    def scrape_fresh_prices(self, product_name: str, user_postcode: str) -> List[ProductPrice]:
        """Scrape fresh prices for a product based on user location"""
        # Get stores that deliver to user's postcode
        available_stores = store_locator.get_priority_stores(user_postcode)
        
        all_prices = []
        
        for store in available_stores[:2]:  # Limit to top 2 stores for speed
            if store in self.scrapers:
                try:
                    print(f"Scraping {store} for {product_name}...")
                    
                    scraper = self.scrapers[store]
                    products = scraper.search_products(product_name, limit=5)
                    
                    # Save to database and convert to ProductPrice
                    for product in products:
                        # Save to database
                        db_product = self.save_scraped_product(product)
                        
                        # Convert to ProductPrice format
                        price_obj = ProductPrice(
                            name=product.name,
                            price=product.price,
                            store=product.store,
                            scraped_at=product.scraped_at
                        )
                        all_prices.append(price_obj)
                    
                    # Be respectful - small delay between stores
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Error scraping {store}: {e}")
                    continue
        
        return all_prices
    
    def save_scraped_product(self, product_data) -> ScrapedProduct:
        """Save scraped product to database"""
        try:
            # Find or create product
            normalized_name = product_data.name.lower().strip()
            
            product = ScrapedProduct.query.filter(
                db.func.lower(ScrapedProduct.name) == normalized_name
            ).first()
            
            if not product:
                product = ScrapedProduct(
                    name=product_data.name,
                    normalized_name=normalized_name,
                    category=getattr(product_data, 'category', 'general')
                )
                db.session.add(product)
                db.session.flush()  # Get ID
            
            # Add price record
            price_record = ScrapedPrice(
                product_id=product.id,
                store=product_data.store,
                price=product_data.price,
                unit=product_data.unit,
                scraped_at=product_data.scraped_at,
                promotion_text=getattr(product_data, 'promotion', None),
                is_on_promotion=bool(getattr(product_data, 'promotion', None)),
                product_url=getattr(product_data, 'url', '')
            )
            
            db.session.add(price_record)
            db.session.commit()
            
            return product
            
        except Exception as e:
            print(f"Error saving product {product_data.name}: {e}")
            db.session.rollback()
            return None
    
    def get_prices_with_fallback(self, product_name: str, user_postcode: str = None) -> List[ProductPrice]:
        """Get prices with smart caching and fallback"""
        # 1. Check cache first
        cached_prices = self.get_cached_prices(product_name, max_age_hours=self.cache_duration_hours)
        
        if cached_prices:
            print(f"Using cached prices for {product_name}")
            return cached_prices
        
        # 2. If no cached prices and user has postcode, scrape fresh
        if user_postcode:
            print(f"Scraping fresh prices for {product_name} near {user_postcode}")
            fresh_prices = self.scrape_fresh_prices(product_name, user_postcode)
            
            if fresh_prices:
                return fresh_prices
        
        # 3. Fallback to UK price estimates
        print(f"Using fallback pricing for {product_name}")
        return self.get_fallback_prices(product_name)
    
    def get_fallback_prices(self, product_name: str) -> List[ProductPrice]:
        """Generate fallback prices using UK averages"""
        from recipe_app.utils.uk_price_service import UKPriceService
        
        uk_service = UKPriceService()
        estimated_price = uk_service.estimate_uk_price(product_name)
        
        if estimated_price:
            # Create synthetic price data for major stores
            stores = ['Tesco', 'Sainsburys', 'ASDA']
            fallback_prices = []
            
            for i, store in enumerate(stores):
                # Add small variation to base price
                price_variation = 1.0 + (i * 0.05)  # 0%, 5%, 10% variation
                
                fallback_prices.append(ProductPrice(
                    name=product_name,
                    price=round(estimated_price * price_variation, 2),
                    store=store,
                    scraped_at=datetime.now()
                ))
            
            return fallback_prices
        
        return []

# Global instance
dynamic_price_service = DynamicPriceService()

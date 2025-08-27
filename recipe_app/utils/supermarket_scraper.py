"""
UK Supermarket Price Scraping Service
Comprehensive web scraping for major UK grocery retailers
"""
import requests
import time
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, quote
import logging
from dataclasses import dataclass
from recipe_app.db import db

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProductPrice:
    """Data class for scraped product prices"""
    name: str
    price: float
    unit: str
    store: str
    url: str
    scraped_at: datetime
    promotion: Optional[str] = None
    original_price: Optional[float] = None
    availability: str = "in_stock"
    category: Optional[str] = None

class BaseScraper:
    """Base class for all supermarket scrapers"""
    
    def __init__(self):
        # Use a simple user agent instead of fake_useragent to avoid dependency issues
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agents[0],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.delay_range = (1, 3)  # Random delay between requests
        self.max_retries = 3
        
    def get_page(self, url: str, params: Dict = None) -> Optional[BeautifulSoup]:
        """Get and parse a web page with error handling"""
        for attempt in range(self.max_retries):
            try:
                # Random delay to be respectful
                time.sleep(self.delay_range[0] + (self.delay_range[1] - self.delay_range[0]) * 0.5)
                
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'lxml')
                logger.info(f"Successfully scraped: {url}")
                return soup
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                
        logger.error(f"Failed to scrape {url} after {self.max_retries} attempts")
        return None
    
    def clean_price(self, price_text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if not price_text:
            return None
        
        # Remove currency symbols and extract numbers
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group().replace(',', ''))
            except ValueError:
                return None
        return None
    
    def clean_product_name(self, name: str) -> str:
        """Clean and standardize product names"""
        if not name:
            return ""
        
        # Remove extra whitespace and normalize
        name = re.sub(r'\s+', ' ', name.strip())
        
        # Remove promotional text
        promotional_terms = [
            r'\bOFFER\b', r'\bSPECIAL\b', r'\bNEW\b', r'\bLIMITED\b',
            r'\bEXCLUSIVE\b', r'\bSAVE\b', r'\bFREE\b'
        ]
        
        for term in promotional_terms:
            name = re.sub(term, '', name, flags=re.IGNORECASE)
        
        return name.strip()


class TescoScraper(BaseScraper):
    """Scraper for Tesco groceries"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.tesco.com"
        self.groceries_url = "https://www.tesco.com/groceries"
        
    def search_products(self, query: str, limit: int = 20) -> List[ProductPrice]:
        """Search for products on Tesco"""
        products = []
        
        search_url = f"{self.groceries_url}/en-GB/search"
        params = {
            'query': query,
            'count': min(limit, 48)  # Tesco's page size limit
        }
        
        soup = self.get_page(search_url, params)
        if not soup:
            return products
        
        # Tesco product tiles
        product_tiles = soup.find_all('div', class_='product-tile')
        
        for tile in product_tiles[:limit]:
            try:
                # Product name
                name_elem = tile.find('h3', class_='product-tile__title')
                if not name_elem:
                    continue
                
                product_name = self.clean_product_name(name_elem.get_text())
                
                # Price
                price_elem = tile.find('span', class_='price')
                if not price_elem:
                    continue
                
                price = self.clean_price(price_elem.get_text())
                if not price:
                    continue
                
                # Unit (if available)
                unit_elem = tile.find('span', class_='product-tile__unit')
                unit = unit_elem.get_text().strip() if unit_elem else 'each'
                
                # Product URL
                link_elem = tile.find('a', href=True)
                product_url = urljoin(self.base_url, link_elem['href']) if link_elem else ""
                
                # Check for promotions
                promotion = None
                promo_elem = tile.find('div', class_='offer-text')
                if promo_elem:
                    promotion = promo_elem.get_text().strip()
                
                product = ProductPrice(
                    name=product_name,
                    price=price,
                    unit=unit,
                    store="Tesco",
                    url=product_url,
                    scraped_at=datetime.now(),
                    promotion=promotion
                )
                
                products.append(product)
                
            except Exception as e:
                logger.warning(f"Error parsing Tesco product: {e}")
                continue
        
        logger.info(f"Scraped {len(products)} products from Tesco for query: {query}")
        return products


class SainsburysScraper(BaseScraper):
    """Scraper for Sainsbury's groceries"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.sainsburys.co.uk"
        self.groceries_url = "https://www.sainsburys.co.uk/gol-ui/groceries"
        
    def search_products(self, query: str, limit: int = 20) -> List[ProductPrice]:
        """Search for products on Sainsbury's"""
        products = []
        
        search_url = f"{self.groceries_url}/search"
        params = {
            'entry': query,
            'pageSize': min(limit, 36)
        }
        
        soup = self.get_page(search_url, params)
        if not soup:
            return products
        
        # Sainsbury's product cards
        product_cards = soup.find_all('div', class_='product-card')
        
        for card in product_cards[:limit]:
            try:
                # Product name
                name_elem = card.find('h3', class_='product-card__name') or card.find('a', class_='product-card__name-link')
                if not name_elem:
                    continue
                
                product_name = self.clean_product_name(name_elem.get_text())
                
                # Price
                price_elem = card.find('span', class_='product-card__price')
                if not price_elem:
                    continue
                
                price = self.clean_price(price_elem.get_text())
                if not price:
                    continue
                
                # Unit
                unit_elem = card.find('span', class_='product-card__unit')
                unit = unit_elem.get_text().strip() if unit_elem else 'each'
                
                # Product URL
                link_elem = card.find('a', href=True)
                product_url = urljoin(self.base_url, link_elem['href']) if link_elem else ""
                
                # Check for offers
                promotion = None
                offer_elem = card.find('div', class_='offer-badge') or card.find('span', class_='offer-text')
                if offer_elem:
                    promotion = offer_elem.get_text().strip()
                
                product = ProductPrice(
                    name=product_name,
                    price=price,
                    unit=unit,
                    store="Sainsbury's",
                    url=product_url,
                    scraped_at=datetime.now(),
                    promotion=promotion
                )
                
                products.append(product)
                
            except Exception as e:
                logger.warning(f"Error parsing Sainsbury's product: {e}")
                continue
        
        logger.info(f"Scraped {len(products)} products from Sainsbury's for query: {query}")
        return products


class AsdaScraper(BaseScraper):
    """Scraper for ASDA groceries"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://groceries.asda.com"
        
    def search_products(self, query: str, limit: int = 20) -> List[ProductPrice]:
        """Search for products on ASDA"""
        products = []
        
        search_url = f"{self.base_url}/search/{quote(query)}"
        
        soup = self.get_page(search_url)
        if not soup:
            return products
        
        # ASDA product items
        product_items = soup.find_all('div', class_='co-product') or soup.find_all('article', class_='product-item')
        
        for item in product_items[:limit]:
            try:
                # Product name
                name_elem = item.find('h3', class_='co-product__title') or item.find('a', class_='co-product__anchor')
                if not name_elem:
                    continue
                
                product_name = self.clean_product_name(name_elem.get_text())
                
                # Price
                price_elem = item.find('strong', class_='co-product__price') or item.find('span', class_='price')
                if not price_elem:
                    continue
                
                price = self.clean_price(price_elem.get_text())
                if not price:
                    continue
                
                # Unit
                unit_elem = item.find('span', class_='co-product__price-per-uom')
                unit = 'each'
                if unit_elem:
                    unit_text = unit_elem.get_text()
                    if 'per kg' in unit_text:
                        unit = 'kg'
                    elif 'per litre' in unit_text:
                        unit = 'litre'
                
                # Product URL
                link_elem = item.find('a', href=True)
                product_url = urljoin(self.base_url, link_elem['href']) if link_elem else ""
                
                # Check for promotions
                promotion = None
                promo_elem = item.find('span', class_='co-product__offer-text')
                if promo_elem:
                    promotion = promo_elem.get_text().strip()
                
                product = ProductPrice(
                    name=product_name,
                    price=price,
                    unit=unit,
                    store="ASDA",
                    url=product_url,
                    scraped_at=datetime.now(),
                    promotion=promotion
                )
                
                products.append(product)
                
            except Exception as e:
                logger.warning(f"Error parsing ASDA product: {e}")
                continue
        
        logger.info(f"Scraped {len(products)} products from ASDA for query: {query}")
        return products


class MorrisonsScraper(BaseScraper):
    """Scraper for Morrisons groceries"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://groceries.morrisons.com"
        
    def search_products(self, query: str, limit: int = 20) -> List[ProductPrice]:
        """Search for products on Morrisons"""
        products = []
        
        search_url = f"{self.base_url}/search"
        params = {'entry': query}
        
        soup = self.get_page(search_url, params)
        if not soup:
            return products
        
        # Morrisons product tiles
        product_tiles = soup.find_all('div', class_='fops-item') or soup.find_all('article', class_='product-item')
        
        for tile in product_tiles[:limit]:
            try:
                # Product name
                name_elem = tile.find('h4', class_='fops-title') or tile.find('h3')
                if not name_elem:
                    continue
                
                product_name = self.clean_product_name(name_elem.get_text())
                
                # Price
                price_elem = tile.find('span', class_='fops-price') or tile.find('span', class_='price')
                if not price_elem:
                    continue
                
                price = self.clean_price(price_elem.get_text())
                if not price:
                    continue
                
                # Unit
                unit = 'each'  # Default for Morrisons
                
                # Product URL
                link_elem = tile.find('a', href=True)
                product_url = urljoin(self.base_url, link_elem['href']) if link_elem else ""
                
                product = ProductPrice(
                    name=product_name,
                    price=price,
                    unit=unit,
                    store="Morrisons",
                    url=product_url,
                    scraped_at=datetime.now()
                )
                
                products.append(product)
                
            except Exception as e:
                logger.warning(f"Error parsing Morrisons product: {e}")
                continue
        
        logger.info(f"Scraped {len(products)} products from Morrisons for query: {query}")
        return products


class SupermarketScrapingService:
    """Main service to coordinate all supermarket scrapers"""
    
    def __init__(self):
        self.scrapers = {
            'tesco': TescoScraper(),
            'sainsburys': SainsburysScraper(),
            'asda': AsdaScraper(),
            'morrisons': MorrisonsScraper()
        }
        
        # Common search terms for grocery categories
        self.category_terms = {
            'dairy': ['milk', 'cheese', 'butter', 'yogurt', 'cream'],
            'meat': ['chicken', 'beef', 'pork', 'lamb', 'fish', 'salmon'],
            'vegetables': ['potato', 'onion', 'carrot', 'tomato', 'lettuce', 'broccoli'],
            'fruits': ['apple', 'banana', 'orange', 'strawberry', 'grapes'],
            'pantry': ['bread', 'rice', 'pasta', 'flour', 'oil', 'sugar'],
            'frozen': ['frozen peas', 'frozen chips', 'ice cream'],
            'beverages': ['orange juice', 'coffee', 'tea', 'water']
        }
    
    def scrape_product(self, product_name: str, stores: List[str] = None) -> Dict[str, List[ProductPrice]]:
        """Scrape a specific product across multiple stores"""
        if stores is None:
            stores = list(self.scrapers.keys())
        
        results = {}
        
        for store in stores:
            if store in self.scrapers:
                try:
                    products = self.scrapers[store].search_products(product_name, limit=5)
                    results[store] = products
                    time.sleep(2)  # Be respectful between stores
                except Exception as e:
                    logger.error(f"Error scraping {store} for {product_name}: {e}")
                    results[store] = []
        
        return results
    
    def scrape_category(self, category: str, stores: List[str] = None) -> Dict[str, Dict[str, List[ProductPrice]]]:
        """Scrape all products in a category across stores"""
        if category not in self.category_terms:
            logger.error(f"Unknown category: {category}")
            return {}
        
        if stores is None:
            stores = list(self.scrapers.keys())
        
        results = {}
        
        for store in stores:
            results[store] = {}
            for product in self.category_terms[category]:
                try:
                    products = self.scrapers[store].search_products(product, limit=3)
                    results[store][product] = products
                    time.sleep(3)  # Longer delay for category scraping
                except Exception as e:
                    logger.error(f"Error scraping {store} for {product}: {e}")
                    results[store][product] = []
        
        return results
    
    def get_price_comparison(self, product_name: str) -> Dict[str, float]:
        """Get price comparison for a product across all stores"""
        results = self.scrape_product(product_name)
        comparison = {}
        
        for store, products in results.items():
            if products:
                # Get average price for the store
                prices = [p.price for p in products if p.price]
                if prices:
                    comparison[store] = sum(prices) / len(prices)
        
        return comparison


# Global instance
supermarket_scraper = SupermarketScrapingService()

"""
Multi-Store Price Comparison Service for Pro-tier users
Compares prices across multiple UK supermarkets for optimal shopping
"""

import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from recipe_app.db import db
from recipe_app.models.pantry_models import ShoppingListItem
from recipe_app.models.advanced_models import ScannedProduct

@dataclass
class StorePrice:
    """Price information for a single store"""
    store_name: str
    price: float
    size: str
    unit_price: float  # price per standard unit (e.g., per 100g, per litre)
    availability: bool
    special_offer: Optional[str] = None
    store_location: Optional[str] = None
    last_updated: datetime = None

@dataclass
class PriceComparison:
    """Complete price comparison for an item"""
    item_name: str
    store_prices: List[StorePrice]
    cheapest_store: StorePrice
    savings_potential: float
    best_value_store: StorePrice  # best price per unit
    average_price: float
    comparison_date: datetime

class MultiStorePriceService:
    """
    Advanced price comparison service for Pro-tier users
    Compares prices across multiple UK supermarkets
    """
    
    def __init__(self):
        # Major UK supermarket chains with their typical price positioning
        self.supported_stores = {
            'tesco': {
                'name': 'Tesco',
                'price_modifier': 1.0,  # baseline
                'specialty': 'general',
                'api_available': False
            },
            'sainsburys': {
                'name': "Sainsbury's",
                'price_modifier': 1.05,  # slightly premium
                'specialty': 'quality',
                'api_available': False
            },
            'asda': {
                'name': 'ASDA',
                'price_modifier': 0.95,  # value focused
                'specialty': 'value',
                'api_available': False
            },
            'morrisons': {
                'name': 'Morrisons',
                'price_modifier': 0.98,  # competitive
                'specialty': 'fresh',
                'api_available': False
            },
            'lidl': {
                'name': 'Lidl',
                'price_modifier': 0.85,  # discount
                'specialty': 'discount',
                'api_available': False
            },
            'aldi': {
                'name': 'Aldi',
                'price_modifier': 0.87,  # discount
                'specialty': 'discount',
                'api_available': False
            },
            'waitrose': {
                'name': 'Waitrose',
                'price_modifier': 1.25,  # premium
                'specialty': 'premium',
                'api_available': False
            }
        }
        
        # Base price categories (in pence)
        self.base_prices = {
            'dairy': {
                'milk_1l': 138,
                'cheese_cheddar_200g': 160,
                'butter_250g': 163,
                'eggs_12pack': 250,
                'yogurt_500g': 175
            },
            'meat': {
                'chicken_breast_500g': 275,
                'minced_beef_500g': 350,
                'bacon_250g': 200,
                'salmon_fillet_200g': 300
            },
            'vegetables': {
                'potatoes_2kg': 240,
                'onions_1kg': 110,
                'carrots_1kg': 90,
                'broccoli_500g': 140,
                'tomatoes_500g': 140
            },
            'fruits': {
                'bananas_1kg': 120,
                'apples_1kg': 220,
                'oranges_1kg': 200,
                'strawberries_400g': 250
            },
            'pantry': {
                'bread_loaf': 120,
                'rice_1kg': 180,
                'pasta_500g': 60,
                'olive_oil_500ml': 350,
                'flour_1kg': 65
            }
        }
        
        # Weekly special offers simulation (would be API-driven in production)
        self.current_offers = self._generate_weekly_offers()
    
    def compare_item_prices(self, item_name: str, quantity: str = "1") -> PriceComparison:
        """
        Compare prices for a specific item across all supported stores
        """
        normalized_item = self._normalize_item_name(item_name)
        base_price = self._get_base_price(normalized_item)
        
        if not base_price:
            # Fallback for unknown items
            base_price = 200  # £2.00 default
        
        store_prices = []
        
        for store_code, store_info in self.supported_stores.items():
            # Calculate store-specific price
            store_price = base_price * store_info['price_modifier']
            
            # Apply random variation (±15%)
            import random
            variation = random.uniform(0.85, 1.15)
            final_price = store_price * variation
            
            # Check for special offers
            special_offer = self._get_special_offer(store_code, normalized_item)
            if special_offer:
                final_price *= special_offer['discount_multiplier']
            
            store_prices.append(StorePrice(
                store_name=store_info['name'],
                price=round(final_price, 2),
                size=quantity,
                unit_price=round(final_price, 2),  # Simplified - would calculate per unit
                availability=True,
                special_offer=special_offer['description'] if special_offer else None,
                last_updated=datetime.now()
            ))
        
        # Sort by price
        store_prices.sort(key=lambda x: x.price)
        
        # Calculate comparison metrics
        cheapest = store_prices[0]
        most_expensive = store_prices[-1]
        savings_potential = most_expensive.price - cheapest.price
        average_price = sum(sp.price for sp in store_prices) / len(store_prices)
        
        # Best value (lowest unit price)
        best_value = min(store_prices, key=lambda x: x.unit_price)
        
        return PriceComparison(
            item_name=item_name,
            store_prices=store_prices,
            cheapest_store=cheapest,
            savings_potential=round(savings_potential, 2),
            best_value_store=best_value,
            average_price=round(average_price, 2),
            comparison_date=datetime.now()
        )
    
    def compare_shopping_list(self, shopping_list_items: List[ShoppingListItem]) -> Dict:
        """
        Compare entire shopping list across stores to find optimal shopping strategy
        """
        comparisons = []
        store_totals = {store: 0.0 for store in self.supported_stores.keys()}
        
        for item in shopping_list_items:
            comparison = self.compare_item_prices(item.ingredient_name, item.quantity)
            comparisons.append(comparison)
            
            # Add prices to store totals
            for store_price in comparison.store_prices:
                store_key = self._get_store_key(store_price.store_name)
                if store_key:
                    store_totals[store_key] += store_price.price
        
        # Find optimal shopping strategies
        cheapest_store = min(store_totals, key=store_totals.get)
        total_savings_potential = sum(comp.savings_potential for comp in comparisons)
        
        # Mixed shopping strategy (best price for each item from different stores)
        mixed_total = sum(comp.cheapest_store.price for comp in comparisons)
        
        return {
            'individual_comparisons': comparisons,
            'store_totals': {
                self.supported_stores[k]['name']: round(v, 2) 
                for k, v in store_totals.items()
            },
            'recommendations': {
                'single_store_best': {
                    'store': self.supported_stores[cheapest_store]['name'],
                    'total': round(store_totals[cheapest_store], 2)
                },
                'mixed_shopping': {
                    'total': round(mixed_total, 2),
                    'savings_vs_single': round(store_totals[cheapest_store] - mixed_total, 2)
                }
            },
            'total_savings_potential': round(total_savings_potential, 2),
            'analysis_date': datetime.now().isoformat()
        }
    
    def get_store_recommendations(self, user_preferences: Dict = None) -> Dict:
        """
        Recommend stores based on user preferences and shopping patterns
        """
        recommendations = {
            'value_focused': ['Lidl', 'Aldi', 'ASDA'],
            'quality_focused': ['Waitrose', "Sainsbury's", 'Morrisons'],
            'convenience_focused': ['Tesco', "Sainsbury's", 'ASDA'],
            'fresh_produce': ['Morrisons', 'Waitrose', 'Tesco']
        }
        
        if user_preferences:
            # Customize based on preferences
            if user_preferences.get('budget_conscious', False):
                return recommendations['value_focused']
            elif user_preferences.get('quality_important', False):
                return recommendations['quality_focused']
        
        return recommendations
    
    def get_price_trends(self, item_name: str, days: int = 30) -> Dict:
        """
        Get price trends for an item over time (simulated data for MVP)
        """
        # This would query historical price data in production
        base_price = self._get_base_price(self._normalize_item_name(item_name)) or 200
        
        trends = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            # Simulate price variation
            import random
            daily_variation = random.uniform(0.95, 1.05)
            trends.append({
                'date': date.isoformat(),
                'average_price': round(base_price * daily_variation, 2),
                'lowest_price': round(base_price * daily_variation * 0.9, 2),
                'highest_price': round(base_price * daily_variation * 1.1, 2)
            })
        
        return {
            'item_name': item_name,
            'trends': trends,
            'analysis': self._analyze_price_trends(trends)
        }
    
    def _normalize_item_name(self, item_name: str) -> str:
        """Normalize item name for price lookup"""
        normalized = item_name.lower().strip()
        
        # Common mappings
        mappings = {
            'chicken breast': 'chicken_breast_500g',
            'minced beef': 'minced_beef_500g',
            'cheddar cheese': 'cheese_cheddar_200g',
            'whole milk': 'milk_1l',
            'white bread': 'bread_loaf'
        }
        
        return mappings.get(normalized, normalized)
    
    def _get_base_price(self, item_name: str) -> Optional[float]:
        """Get base price for an item"""
        for category, items in self.base_prices.items():
            if item_name in items:
                return items[item_name]
        return None
    
    def _get_store_key(self, store_name: str) -> Optional[str]:
        """Get store key from store name"""
        for key, info in self.supported_stores.items():
            if info['name'] == store_name:
                return key
        return None
    
    def _generate_weekly_offers(self) -> Dict:
        """Generate simulated weekly special offers"""
        import random
        
        offers = {}
        
        # Randomly assign offers to stores and items
        for store_code in list(self.supported_stores.keys())[:3]:  # Only some stores have offers
            store_offers = {}
            
            # Pick random items for offers
            all_items = []
            for category_items in self.base_prices.values():
                all_items.extend(category_items.keys())
            
            offer_items = random.sample(all_items, min(3, len(all_items)))
            
            for item in offer_items:
                store_offers[item] = {
                    'description': random.choice([
                        'Buy 2 Get 1 Free',
                        '25% Off',
                        '£1 Off',
                        'Half Price'
                    ]),
                    'discount_multiplier': random.uniform(0.5, 0.8)
                }
            
            offers[store_code] = store_offers
        
        return offers
    
    def _get_special_offer(self, store_code: str, item_name: str) -> Optional[Dict]:
        """Check if item has special offer at store"""
        store_offers = self.current_offers.get(store_code, {})
        return store_offers.get(item_name)
    
    def _analyze_price_trends(self, trends: List[Dict]) -> Dict:
        """Analyze price trend patterns"""
        prices = [t['average_price'] for t in trends]
        
        if len(prices) < 2:
            return {'trend': 'insufficient_data'}
        
        recent_avg = sum(prices[:7]) / min(7, len(prices))
        older_avg = sum(prices[-7:]) / min(7, len(prices))
        
        if recent_avg > older_avg * 1.05:
            trend = 'increasing'
            recommendation = 'Prices trending up - consider buying soon'
        elif recent_avg < older_avg * 0.95:
            trend = 'decreasing'
            recommendation = 'Prices trending down - wait for better deals'
        else:
            trend = 'stable'
            recommendation = 'Prices stable - buy when convenient'
        
        return {
            'trend': trend,
            'recommendation': recommendation,
            'price_change_percent': round(((recent_avg - older_avg) / older_avg) * 100, 1)
        }
    
    def get_bulk_buying_recommendations(self, shopping_list: List[ShoppingListItem]) -> Dict:
        """
        Recommend bulk buying opportunities for Pro users
        """
        recommendations = {
            'bulk_opportunities': [],
            'potential_savings': 0.0,
            'storage_considerations': []
        }
        
        for item in shopping_list:
            # Check if item benefits from bulk buying
            normalized_item = self._normalize_item_name(item.ingredient_name)
            
            # Items that are good for bulk buying
            bulk_friendly_categories = ['pantry', 'cleaning', 'frozen']
            
            if any(cat in normalized_item for cat in bulk_friendly_categories):
                bulk_price = self._calculate_bulk_price(item.ingredient_name, item.quantity)
                regular_price = self._get_base_price(normalized_item) or 200
                
                if bulk_price and bulk_price < regular_price * 0.85:  # 15%+ savings
                    savings = regular_price - bulk_price
                    recommendations['bulk_opportunities'].append({
                        'item': item.ingredient_name,
                        'regular_price': regular_price,
                        'bulk_price': bulk_price,
                        'savings': round(savings, 2),
                        'bulk_size': f"{item.quantity} x3"  # Simplified
                    })
                    recommendations['potential_savings'] += savings
        
        return recommendations
    
    def _calculate_bulk_price(self, item_name: str, quantity: str) -> Optional[float]:
        """Calculate bulk price for an item"""
        base_price = self._get_base_price(self._normalize_item_name(item_name))
        if base_price:
            # Bulk typically 15-25% cheaper per unit
            import random
            bulk_discount = random.uniform(0.75, 0.85)
            return base_price * bulk_discount
        return None

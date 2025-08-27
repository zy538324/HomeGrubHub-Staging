"""
UK-focused price estimation service with fallback pricing data
Combines Open Food Facts UK data with estimated store pricing
"""
import requests
import json
from datetime import datetime, timedelta
from recipe_app.db import db
from recipe_app.models.pantry_models import PantryItem, ShoppingListItem

class UKPriceService:
    """Service to estimate UK supermarket prices for shopping list items"""
    
    def __init__(self):
        self.open_food_facts_uk_url = "https://uk.openfoodfacts.org/api/v0"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Flavorio-App/1.0 (contact@flavorio.com)'
        })
        
        # UK average price estimates by category (pence per standard unit)
        self.uk_price_estimates = {
            'dairy': {
                'milk': {'price_per_litre': 138, 'common_sizes': [1000, 2000, 4000]},
                'cheese': {'price_per_kg': 800, 'common_sizes': [200, 400, 500]},
                'butter': {'price_per_kg': 650, 'common_sizes': [250, 500]},
                'yogurt': {'price_per_kg': 350, 'common_sizes': [150, 500, 1000]},
            },
            'meat': {
                'chicken': {'price_per_kg': 550, 'common_sizes': [500, 1000, 1500]},
                'beef': {'price_per_kg': 1200, 'common_sizes': [500, 1000]},
                'pork': {'price_per_kg': 700, 'common_sizes': [500, 1000]},
                'fish': {'price_per_kg': 1500, 'common_sizes': [200, 400, 500]},
            },
            'vegetables': {
                'potato': {'price_per_kg': 120, 'common_sizes': [1000, 2500, 5000]},
                'onion': {'price_per_kg': 110, 'common_sizes': [500, 1000, 2000]},
                'carrot': {'price_per_kg': 90, 'common_sizes': [500, 1000]},
                'tomato': {'price_per_kg': 280, 'common_sizes': [400, 500, 1000]},
            },
            'fruits': {
                'apple': {'price_per_kg': 220, 'common_sizes': [500, 1000, 2000]},
                'banana': {'price_per_kg': 120, 'common_sizes': [1000, 1500]},
                'orange': {'price_per_kg': 200, 'common_sizes': [1000, 2000]},
            },
            'pantry': {
                'rice': {'price_per_kg': 180, 'common_sizes': [500, 1000, 2000]},
                'pasta': {'price_per_kg': 120, 'common_sizes': [500, 1000]},
                'bread': {'price_per_loaf': 120, 'common_sizes': [400, 800]},
                'flour': {'price_per_kg': 65, 'common_sizes': [1000, 1500]},
            }
        }
    
    def search_product_by_name(self, product_name):
        """Search Open Food Facts UK for product information"""
        try:
            search_url = f"{self.open_food_facts_uk_url}/cgi/search.pl"
            params = {
                'search_terms': product_name,
                'search_simple': 1,
                'action': 'process',
                'json': 1,
                'page_size': 5,
                'countries': 'United Kingdom'
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('products', [])
        except Exception as e:
            print(f"Error searching Open Food Facts: {e}")
        
        return []
    
    def get_product_by_barcode(self, barcode):
        """Get specific product by barcode from Open Food Facts UK"""
        try:
            product_url = f"{self.open_food_facts_uk_url}/product/{barcode}.json"
            response = self.session.get(product_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    return data.get('product', {})
        except Exception as e:
            print(f"Error fetching product by barcode: {e}")
        
        return {}
    
    def estimate_uk_price(self, item_name, quantity=1, unit='item'):
        """Estimate UK price based on item name and historical data"""
        item_name_lower = item_name.lower()
        estimated_price = None
        
        # Check our UK price database
        for category, products in self.uk_price_estimates.items():
            for product, price_info in products.items():
                if product in item_name_lower:
                    # Get price per unit
                    if 'price_per_kg' in price_info and unit in ['kg', 'g', 'gram', 'grams']:
                        price_per_g = price_info['price_per_kg'] / 1000  # Convert to pence per gram
                        if unit == 'kg':
                            estimated_price = (price_info['price_per_kg'] * quantity) / 100  # Convert to pounds
                        else:  # grams
                            estimated_price = (price_per_g * quantity) / 100
                    
                    elif 'price_per_litre' in price_info and unit in ['l', 'litre', 'ml', 'millilitre']:
                        price_per_ml = price_info['price_per_litre'] / 1000
                        if unit in ['l', 'litre']:
                            estimated_price = (price_info['price_per_litre'] * quantity) / 100
                        else:  # ml
                            estimated_price = (price_per_ml * quantity) / 100
                    
                    elif 'price_per_loaf' in price_info:
                        estimated_price = (price_info['price_per_loaf'] * quantity) / 100
                    
                    break
            
            if estimated_price:
                break
        
        # Fallback: use historical purchase data from user's app
        if not estimated_price:
            estimated_price = self.get_historical_price_estimate(item_name)
        
        # Final fallback: generic estimates
        if not estimated_price:
            estimated_price = self.get_generic_uk_estimate(quantity, unit)
        
        return round(estimated_price, 2) if estimated_price else None
    
    def get_historical_price_estimate(self, item_name):
        """Get price estimate from user's previous purchases"""
        try:
            # Find recent purchases of similar items
            recent_purchases = ShoppingListItem.query.filter(
                ShoppingListItem.item_name.ilike(f'%{item_name}%'),
                ShoppingListItem.is_purchased == True,
                ShoppingListItem.actual_cost.isnot(None),
                ShoppingListItem.purchased_at >= datetime.utcnow() - timedelta(days=90)
            ).limit(10).all()
            
            if recent_purchases:
                # Calculate average cost per unit
                total_cost = sum(item.actual_cost for item in recent_purchases)
                total_quantity = sum(item.quantity_needed for item in recent_purchases)
                
                if total_quantity > 0:
                    avg_cost_per_unit = total_cost / total_quantity
                    return avg_cost_per_unit
        
        except Exception as e:
            print(f"Error getting historical price: {e}")
        
        return None
    
    def get_generic_uk_estimate(self, quantity, unit):
        """Generic UK price estimates when no specific data available"""
        base_estimates = {
            'item': 1.50,     # £1.50 per item
            'g': 0.005,       # £0.005 per gram (£5/kg)
            'kg': 5.00,       # £5 per kg
            'ml': 0.002,      # £0.002 per ml (£2/litre)
            'l': 2.00,        # £2 per litre
            'piece': 0.75,    # £0.75 per piece
            'pack': 2.50,     # £2.50 per pack
        }
        
        unit_price = base_estimates.get(unit.lower(), base_estimates['item'])
        return unit_price * quantity
    
    def enrich_shopping_list_with_prices(self, shopping_list_items):
        """Add price estimates to shopping list items"""
        enriched_items = []
        
        for item in shopping_list_items:
            # Skip if already has estimated cost
            if item.estimated_cost:
                enriched_items.append(item)
                continue
            
            # Get price estimate
            estimated_price = self.estimate_uk_price(
                item.item_name, 
                item.quantity_needed, 
                item.unit
            )
            
            if estimated_price:
                item.estimated_cost = estimated_price
                
                # Try to find store section suggestion
                item.store_section = self.suggest_store_section(item.item_name)
            
            enriched_items.append(item)
        
        return enriched_items
    
    def suggest_store_section(self, item_name):
        """Suggest which section of the store to find the item"""
        item_name_lower = item_name.lower()
        
        sections = {
            'Fresh Produce': ['apple', 'banana', 'orange', 'carrot', 'potato', 'onion', 'lettuce', 'tomato'],
            'Dairy & Eggs': ['milk', 'cheese', 'butter', 'yogurt', 'cream', 'eggs'],
            'Meat & Fish': ['chicken', 'beef', 'pork', 'fish', 'salmon', 'tuna'],
            'Bakery': ['bread', 'rolls', 'cake', 'pastry'],
            'Frozen': ['frozen', 'ice cream', 'pizza'],
            'Pantry': ['rice', 'pasta', 'flour', 'sugar', 'oil', 'vinegar', 'sauce'],
            'Household': ['washing', 'cleaning', 'toilet paper'],
        }
        
        for section, keywords in sections.items():
            if any(keyword in item_name_lower for keyword in keywords):
                return section
        
        return 'General'
    
    def get_supermarket_comparison(self, item_name):
        """Get price comparison across major UK supermarkets (placeholder)"""
        # This would integrate with supermarket APIs when available
        # For now, return estimated ranges based on known supermarket positioning
        
        base_price = self.estimate_uk_price(item_name, 1, 'item')
        if not base_price:
            return None
        
        return {
            'tesco': {'price_per_unit': round(base_price * 1.0, 2), 'unit': 'item'},      # Base price
            'sainsburys': {'price_per_unit': round(base_price * 1.05, 2), 'unit': 'item'}, # Slightly higher
            'asda': {'price_per_unit': round(base_price * 0.95, 2), 'unit': 'item'},      # Slightly lower
            'morrisons': {'price_per_unit': round(base_price * 0.98, 2), 'unit': 'item'}, # Slightly lower
            'aldi': {'price_per_unit': round(base_price * 0.85, 2), 'unit': 'item'},      # Significantly lower
            'lidl': {'price_per_unit': round(base_price * 0.87, 2), 'unit': 'item'},      # Significantly lower
        }
    
    def get_location_specific_prices(self, item_name, quantity, unit, postcode):
        """Get location-specific prices using fallback estimates"""
        base_price = self.estimate_uk_price(item_name, quantity, unit)
        if not base_price:
            base_price = 2.0  # Default fallback
        
        # Generate estimated store-specific pricing using fallback logic
        store_variations = {
            'tesco': 1.0,
            'sainsburys': 1.05,
            'asda': 0.95,
            'morrisons': 0.98,
            'aldi': 0.85,
            'lidl': 0.87,
            'iceland': 0.92
        }
        
        stores = []
        for store_name, multiplier in store_variations.items():
            stores.append({
                'store_name': store_name.title(),
                'price': round(base_price * multiplier, 2),
                'distance_km': 2.5,  # Estimate
                'availability': 'In Stock'
            })
        
        # Sort by price
        stores.sort(key=lambda x: x['price'])
        
        return {
            'base_estimate': base_price,
            'cheapest_price': stores[0]['price'],
            'most_expensive_price': stores[-1]['price'],
            'potential_savings': round(stores[-1]['price'] - stores[0]['price'], 2),
            'stores': stores,
            'postcode': postcode,
            'message': 'Using estimated pricing data'
        }
    
    def get_shopping_list_location_comparison(self, shopping_items, postcode):
        """Get location-specific comparison for entire shopping list using fallback estimates"""
        store_totals = {
            'tesco': 0,
            'sainsburys': 0,
            'asda': 0,
            'morrisons': 0,
            'aldi': 0,
            'lidl': 0,
            'iceland': 0
        }
        
        item_details = []
        
        for item in shopping_items:
            base_price = self.estimate_uk_price(item.item_name, item.quantity_needed, item.unit)
            if not base_price:
                base_price = 2.0
            
            item_prices = {}
            for store in store_totals.keys():
                multiplier = {'tesco': 1.0, 'sainsburys': 1.05, 'asda': 0.95, 
                             'morrisons': 0.98, 'aldi': 0.85, 'lidl': 0.87, 'iceland': 0.92}[store]
                price = round(base_price * multiplier, 2)
                item_prices[store] = price
                store_totals[store] += price
            
            item_details.append({
                'item_name': item.item_name,
                'quantity': item.quantity_needed,
                'unit': item.unit,
                'store_prices': item_prices
            })
        
        # Format results
        comparison = []
        for store, total in store_totals.items():
            comparison.append({
                'store_name': store.title(),
                'total_cost': round(total, 2),
                'estimated_items': len(shopping_items),
                'distance_km': 2.5,
                'delivery_available': True
            })
        
        comparison.sort(key=lambda x: x['total_cost'])
        
        return {
            'stores': comparison,
            'item_breakdown': item_details,
            'cheapest_store': comparison[0]['store_name'],
            'most_expensive_store': comparison[-1]['store_name'],
            'potential_savings': round(comparison[-1]['total_cost'] - comparison[0]['total_cost'], 2),
            'postcode': postcode,
            'message': 'Using estimated pricing data'
        }
    
    def get_store_recommendations(self, postcode, preferences=None):
        """Get store recommendations based on location using fallback data"""
        # Generate estimated store recommendations
        stores = [
            {
                'name': 'Tesco Superstore',
                'distance_km': 1.8,
                'price_rating': 'Medium',
                'quality_rating': 'Good',
                'parking': True,
                'delivery': True,
                'opening_hours': '7:00 - 22:00'
            },
            {
                'name': 'Aldi',
                'distance_km': 2.1,
                'price_rating': 'Low',
                'quality_rating': 'Good',
                'parking': True,
                'delivery': False,
                'opening_hours': '8:00 - 20:00'
            },
            {
                'name': 'Sainsburys Local',
                'distance_km': 0.9,
                'price_rating': 'High',
                'quality_rating': 'Excellent',
                'parking': False,
                'delivery': True,
                'opening_hours': '7:00 - 23:00'
            },
            {
                'name': 'Asda Supercentre',
                'distance_km': 3.2,
                'price_rating': 'Low',
                'quality_rating': 'Good',
                'parking': True,
                'delivery': True,
                'opening_hours': '6:00 - 24:00'
            }
        ]
        
        return {
            'stores': stores,
            'postcode': postcode,
            'message': 'Using estimated store locations and data'
        }
    
    def enrich_shopping_list_with_location_prices(self, shopping_items, postcode):
        """Enrich shopping list with location-specific pricing"""
        if not postcode:
            return self.enrich_shopping_list_with_prices(shopping_items)
        
        enriched_items = []
        for item in shopping_items:
            # Get base price estimate
            base_price = self.estimate_uk_price(item.item_name, item.quantity_needed, item.unit)
            
            # Get location-specific pricing
            location_pricing = self.get_location_specific_prices(
                item.item_name, item.quantity_needed, item.unit, postcode
            )
            
            # Update item with pricing information
            item.estimated_cost = location_pricing.get('cheapest_price', base_price)
            item.base_estimated_cost = location_pricing.get('base_estimate', base_price)
            item.potential_savings = location_pricing.get('potential_savings', 0)
            item.store_options = location_pricing.get('stores', [])[:3]  # Top 3 cheapest stores
            
            # Set store section based on item name
            item.store_section = self.suggest_store_section(item.item_name)
            
            enriched_items.append(item)
        
        return enriched_items


# Global instance
uk_price_service = UKPriceService()

"""
Safe Price Estimation Service
Legal alternative to web scraping - uses statistical estimates and open data
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

from recipe_app.db import db

logger = logging.getLogger(__name__)

@dataclass
class PriceEstimate:
    """Data class for price estimates"""
    item_name: str
    estimated_price: float
    confidence: str  # 'high', 'medium', 'low'
    data_source: str
    postcode_area: str
    estimated_at: datetime
    price_range_min: Optional[float] = None
    price_range_max: Optional[float] = None
    regional_factor: float = 1.0

class SafePriceEstimationService:
    """
    Legally compliant price estimation service
    Uses statistical averages, open data, and user-contributed information
    """
    
    def __init__(self):
        # UK average price database based on ONS retail price indices
        # These are approximate estimates based on publicly available statistics
        self.base_price_estimates = {
            # Basic ingredients (prices per kg/unit where appropriate)
            'rice': {'price': 2.50, 'unit': 'kg', 'confidence': 'high'},
            'pasta': {'price': 1.80, 'unit': 'kg', 'confidence': 'high'},
            'bread': {'price': 1.20, 'unit': 'loaf', 'confidence': 'high'},
            'milk': {'price': 1.45, 'unit': 'litre', 'confidence': 'high'},
            'eggs': {'price': 2.80, 'unit': 'dozen', 'confidence': 'high'},
            'chicken breast': {'price': 8.50, 'unit': 'kg', 'confidence': 'medium'},
            'beef mince': {'price': 7.20, 'unit': 'kg', 'confidence': 'medium'},
            'potatoes': {'price': 1.20, 'unit': 'kg', 'confidence': 'high'},
            'onions': {'price': 1.50, 'unit': 'kg', 'confidence': 'high'},
            'carrots': {'price': 1.30, 'unit': 'kg', 'confidence': 'high'},
            'tomatoes': {'price': 3.50, 'unit': 'kg', 'confidence': 'medium'},
            'bananas': {'price': 1.20, 'unit': 'kg', 'confidence': 'high'},
            'apples': {'price': 2.80, 'unit': 'kg', 'confidence': 'medium'},
            'cheese': {'price': 12.50, 'unit': 'kg', 'confidence': 'medium'},
            'butter': {'price': 8.50, 'unit': 'kg', 'confidence': 'medium'},
            'olive oil': {'price': 6.50, 'unit': 'litre', 'confidence': 'medium'},
            'flour': {'price': 1.20, 'unit': 'kg', 'confidence': 'high'},
            'sugar': {'price': 1.50, 'unit': 'kg', 'confidence': 'high'},
            'salt': {'price': 2.50, 'unit': 'kg', 'confidence': 'high'},
            'black pepper': {'price': 25.00, 'unit': 'kg', 'confidence': 'low'},
        }
        
        # Regional price variation factors (based on UK cost of living data)
        self.regional_factors = {
            # London and South East - higher prices
            'sw': 1.25, 'se': 1.20, 'w': 1.30, 'wc': 1.35, 'ec': 1.30, 'e': 1.15, 'n': 1.15, 'nw': 1.20,
            # Southern England - above average
            'rh': 1.15, 'tn': 1.15, 'me': 1.15, 'ct': 1.15, 'bn': 1.15, 'po': 1.10, 'so': 1.10,
            # Midlands - average
            'b': 1.05, 'cv': 1.05, 'le': 1.05, 'nn': 1.05, 'mk': 1.05, 'ox': 1.15,
            # Northern England - below average
            'm': 0.95, 'l': 0.95, 's': 0.95, 'hd': 0.95, 'ls': 0.95, 'yo': 0.95,
            # Scotland - varies
            'g': 1.00, 'eh': 1.05, 'ab': 1.10, 'dd': 0.95,
            # Wales - below average
            'cf': 0.95, 'sa': 0.90, 'll': 0.90, 'sy': 0.90,
            # Northern Ireland - below average
            'bt': 0.90,
        }
    
    def normalize_postcode(self, postcode: str) -> str:
        """Extract postcode area from full postcode"""
        if not postcode:
            return 'uk'  # Default to UK average
        
        # Remove spaces and convert to lowercase
        postcode = postcode.replace(' ', '').lower()
        
        # Extract area (first 1-2 letters)
        area_match = re.match(r'^([a-z]{1,2})', postcode)
        if area_match:
            return area_match.group(1)
        
        return 'uk'
    
    def get_regional_factor(self, postcode: str) -> float:
        """Get regional price factor for postcode area"""
        area = self.normalize_postcode(postcode)
        return self.regional_factors.get(area, 1.0)  # Default to UK average
    
    def estimate_price(self, item_name: str, postcode: str = '') -> PriceEstimate:
        """
        Estimate price for an item based on statistical averages
        """
        # Normalize item name for lookup
        normalized_name = item_name.lower().strip()
        
        # Try to find exact match first
        price_data = self.base_price_estimates.get(normalized_name)
        
        if not price_data:
            # Try partial matching for common variations
            price_data = self._find_similar_item(normalized_name)
        
        if not price_data:
            # Fallback: estimate based on item category
            price_data = self._estimate_by_category(normalized_name)
        
        # Apply regional pricing factor
        regional_factor = self.get_regional_factor(postcode)
        estimated_price = price_data['price'] * regional_factor
        
        # Calculate price range (±20% for uncertainty)
        price_range_min = estimated_price * 0.8
        price_range_max = estimated_price * 1.2
        
        return PriceEstimate(
            item_name=item_name,
            estimated_price=round(estimated_price, 2),
            confidence=price_data['confidence'],
            data_source="UK Statistical Averages",
            postcode_area=self.normalize_postcode(postcode),
            estimated_at=datetime.now(),
            price_range_min=round(price_range_min, 2),
            price_range_max=round(price_range_max, 2),
            regional_factor=regional_factor
        )
    
    def _find_similar_item(self, item_name: str) -> Optional[Dict]:
        """Find similar items in the price database"""
        # Common variations and synonyms
        variations = {
            'chicken': 'chicken breast',
            'beef': 'beef mince',
            'mince': 'beef mince',
            'potato': 'potatoes',
            'onion': 'onions',
            'carrot': 'carrots',
            'tomato': 'tomatoes',
            'banana': 'bananas',
            'apple': 'apples',
        }
        
        # Check variations
        for variation, canonical in variations.items():
            if variation in item_name:
                return self.base_price_estimates.get(canonical)
        
        # Check if any known item is contained in the query
        for known_item in self.base_price_estimates:
            if known_item in item_name or item_name in known_item:
                return self.base_price_estimates[known_item]
        
        return None
    
    def _estimate_by_category(self, item_name: str) -> Dict:
        """Estimate price based on item category"""
        # Category-based estimates for unknown items
        if any(word in item_name for word in ['meat', 'beef', 'pork', 'lamb']):
            return {'price': 8.50, 'confidence': 'low'}
        elif any(word in item_name for word in ['chicken', 'poultry']):
            return {'price': 7.50, 'confidence': 'low'}
        elif any(word in item_name for word in ['fish', 'salmon', 'tuna', 'cod']):
            return {'price': 12.00, 'confidence': 'low'}
        elif any(word in item_name for word in ['fruit', 'apple', 'orange', 'berry']):
            return {'price': 3.50, 'confidence': 'low'}
        elif any(word in item_name for word in ['vegetable', 'veg', 'salad']):
            return {'price': 2.50, 'confidence': 'low'}
        elif any(word in item_name for word in ['dairy', 'milk', 'cream', 'yogurt']):
            return {'price': 2.50, 'confidence': 'low'}
        elif any(word in item_name for word in ['bread', 'bakery', 'roll']):
            return {'price': 1.50, 'confidence': 'low'}
        elif any(word in item_name for word in ['spice', 'herb', 'seasoning']):
            return {'price': 15.00, 'confidence': 'low'}
        else:
            # Generic food item estimate
            return {'price': 3.00, 'confidence': 'low'}
    
    def get_multiple_estimates(self, items: List[str], postcode: str = '') -> List[PriceEstimate]:
        """Get price estimates for multiple items"""
        estimates = []
        for item in items:
            try:
                estimate = self.estimate_price(item, postcode)
                estimates.append(estimate)
            except Exception as e:
                logger.error(f"Error estimating price for {item}: {e}")
                # Create fallback estimate
                estimates.append(PriceEstimate(
                    item_name=item,
                    estimated_price=3.00,
                    confidence='low',
                    data_source="Fallback Estimate",
                    postcode_area=self.normalize_postcode(postcode),
                    estimated_at=datetime.now()
                ))
        
        return estimates
    
    def get_store_comparison(self, item_name: str, postcode: str = '') -> List[Dict]:
        """
        Generate store comparison with estimated price variations
        This provides value to users without scraping
        """
        base_estimate = self.estimate_price(item_name, postcode)
        
        # Simulate typical store price variations based on market positioning
        store_variations = {
            'Budget Supermarket': 0.85,    # 15% below average
            'Mid-range Store': 1.00,       # Average price
            'Premium Store': 1.25,         # 25% above average
            'Local Shop': 1.35,            # 35% above average
        }
        
        comparisons = []
        for store, factor in store_variations.items():
            estimated_price = base_estimate.estimated_price * factor
            comparisons.append({
                'store': store,
                'estimated_price': round(estimated_price, 2),
                'confidence': base_estimate.confidence,
                'note': 'Estimated based on typical store pricing patterns'
            })
        
        return comparisons

# Create global instance
safe_price_service = SafePriceEstimationService()

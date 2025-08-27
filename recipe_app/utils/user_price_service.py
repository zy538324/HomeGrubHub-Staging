"""
User Price Submission Service
Handles user-contributed price data with validation and sanitization
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, or_

from recipe_app.db import db
from recipe_app.models.user_price_models import (
    UserContributedPrice, PriceVerification, ShopLocation, PriceDataSanitizer
)
from recipe_app.utils.postcode_service import postcode_service

logger = logging.getLogger(__name__)

class UserPriceService:
    """
    Service for managing user-contributed price data
    Provides validation, sanitization, and querying capabilities
    """
    
    def submit_price(self, user_id: int, price_data: Dict) -> Tuple[bool, str, Optional[int]]:
        """
        Submit a new price entry from a user
        Returns (success, message, price_id)
        """
        try:
            # Validate required fields
            required_fields = ['shop_name', 'item_name', 'price', 'shop_location']
            for field in required_fields:
                if not price_data.get(field):
                    return False, f"Missing required field: {field}", None
            
            # Sanitize and validate data
            try:
                sanitized_data = self._sanitize_price_data(price_data)
            except ValueError as e:
                return False, f"Invalid data: {e}", None
            
            # Look up postcode information
            postcode_data = None
            if sanitized_data.get('postcode'):
                postcode_data = postcode_service.lookup_postcode(sanitized_data['postcode'])
                if not postcode_data:
                    logger.warning(f"Could not verify postcode: {sanitized_data['postcode']}")
            
            # Create new price entry
            new_price = UserContributedPrice(
                shop_name=sanitized_data['shop_name'],
                normalized_shop_name=sanitized_data['normalized_shop_name'],
                brand_name=sanitized_data.get('brand_name'),
                item_name=sanitized_data['item_name'],
                normalized_item_name=sanitized_data['normalized_item_name'],
                size=sanitized_data.get('size'),
                price=sanitized_data['price'],
                price_per_unit=sanitized_data.get('price_per_unit'),
                shop_location=sanitized_data['shop_location'],
                postcode=postcode_data['postcode'] if postcode_data else sanitized_data.get('postcode'),
                postcode_area=postcode_data['postcode_area'] if postcode_data else PriceDataSanitizer.extract_postcode_area(sanitized_data.get('postcode', '')),
                submitted_by=user_id,
                submitted_at=datetime.utcnow()
            )
            
            db.session.add(new_price)
            db.session.commit()
            
            # Create or update shop location record
            if postcode_data:
                self._create_or_update_shop_location(sanitized_data, postcode_data)
            
            return True, "Price submitted successfully", new_price.id
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error submitting price: {e}")
            return False, "An error occurred while submitting the price", None
    
    def _sanitize_price_data(self, price_data: Dict) -> Dict:
        """Sanitize and validate user-submitted price data"""
        sanitized = {}
        
        # Shop name
        shop_name = price_data.get('shop_name', '').strip()
        if not shop_name:
            raise ValueError("Shop name is required")
        if len(shop_name) > 100:
            raise ValueError("Shop name too long")
        
        sanitized['shop_name'] = shop_name
        sanitized['normalized_shop_name'] = PriceDataSanitizer.normalize_shop_name(shop_name)
        
        # Item name
        item_name = price_data.get('item_name', '').strip()
        if not item_name:
            raise ValueError("Item name is required")
        if len(item_name) > 200:
            raise ValueError("Item name too long")
        
        sanitized['item_name'] = item_name
        sanitized['normalized_item_name'] = PriceDataSanitizer.normalize_item_name(item_name)
        
        # Brand name (optional)
        brand_name = price_data.get('brand_name', '').strip()
        if brand_name and len(brand_name) > 100:
            raise ValueError("Brand name too long")
        sanitized['brand_name'] = brand_name if brand_name else None
        
        # Size (optional)
        size = price_data.get('size', '').strip()
        if size and len(size) > 50:
            raise ValueError("Size description too long")
        sanitized['size'] = size if size else None
        
        # Price (required)
        price = PriceDataSanitizer.validate_price(str(price_data.get('price', '')))
        sanitized['price'] = price
        
        # Calculate price per unit if size is provided
        if size:
            price_per_unit = PriceDataSanitizer.calculate_price_per_unit(price, size)
            sanitized['price_per_unit'] = price_per_unit
        
        # Shop location
        shop_location = price_data.get('shop_location', '').strip()
        if not shop_location:
            raise ValueError("Shop location is required")
        if len(shop_location) > 200:
            raise ValueError("Shop location too long")
        sanitized['shop_location'] = shop_location
        
        # Try to extract postcode from location
        postcode = self._extract_postcode_from_location(shop_location)
        if postcode and postcode_service.validate_postcode(postcode):
            sanitized['postcode'] = postcode_service.normalize_postcode(postcode)
        
        return sanitized
    
    def _extract_postcode_from_location(self, location: str) -> Optional[str]:
        """Try to extract postcode from location string"""
        import re
        
        # UK postcode pattern
        pattern = r'([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})'
        matches = re.findall(pattern, location.upper())
        
        if matches:
            return matches[-1]  # Return the last match (most likely to be the postcode)
        
        return None
    
    def _create_or_update_shop_location(self, sanitized_data: Dict, postcode_data: Dict):
        """Create or update shop location record"""
        try:
            # Check if location already exists
            existing = ShopLocation.query.filter_by(
                normalized_shop_name=sanitized_data['normalized_shop_name'],
                postcode=postcode_data['postcode']
            ).first()
            
            if not existing:
                shop_location = ShopLocation(
                    shop_name=sanitized_data['shop_name'],
                    normalized_shop_name=sanitized_data['normalized_shop_name'],
                    address_line=sanitized_data['shop_location'],
                    postcode=postcode_data['postcode'],
                    postcode_area=postcode_data['postcode_area'],
                    latitude=postcode_data.get('latitude'),
                    longitude=postcode_data.get('longitude'),
                    town=postcode_data.get('town'),
                    county=postcode_data.get('county'),
                    region=postcode_data.get('region'),
                    verified=True,  # Since it came from official API
                    created_at=datetime.utcnow()
                )
                
                db.session.add(shop_location)
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Error creating shop location: {e}")
    
    def get_prices_for_item(self, item_name: str, user_postcode: str = None, radius_km: int = 10) -> List[Dict]:
        """
        Get user-contributed prices for an item
        Optionally filter by location proximity
        """
        normalized_item = PriceDataSanitizer.normalize_item_name(item_name)
        
        # Base query
        query = UserContributedPrice.query.filter(
            UserContributedPrice.normalized_item_name.like(f'%{normalized_item}%')
        )
        
        # Filter by location if postcode provided
        if user_postcode:
            user_postcode_area = PriceDataSanitizer.extract_postcode_area(user_postcode)
            if user_postcode_area:
                # Prioritize same postcode area, but include others
                query = query.filter(
                    or_(
                        UserContributedPrice.postcode_area == user_postcode_area,
                        UserContributedPrice.postcode_area.is_(None)  # Include entries without postcode
                    )
                )
        
        # Order by recency and verification status
        prices = query.order_by(
            UserContributedPrice.is_verified.desc(),
            UserContributedPrice.verification_count.desc(),
            UserContributedPrice.submitted_at.desc()
        ).limit(20).all()
        
        results = []
        for price in prices:
            results.append({
                'id': price.id,
                'shop_name': price.shop_name,
                'brand_name': price.brand_name,
                'item_name': price.item_name,
                'size': price.size,
                'price': float(price.price),
                'price_per_unit': float(price.price_per_unit) if price.price_per_unit else None,
                'shop_location': price.shop_location,
                'postcode': price.postcode,
                'submitted_at': price.submitted_at.isoformat(),
                'is_verified': price.is_verified,
                'verification_count': price.verification_count,
                'days_old': (datetime.utcnow() - price.submitted_at).days
            })
        
        return results
    
    def verify_price(self, user_id: int, price_id: int, is_accurate: bool, comment: str = None) -> Tuple[bool, str]:
        """
        Allow users to verify the accuracy of submitted prices
        """
        try:
            # Check if user has already verified this price
            existing = PriceVerification.query.filter_by(
                price_id=price_id,
                verified_by=user_id
            ).first()
            
            if existing:
                return False, "You have already verified this price"
            
            # Check if price exists
            price = UserContributedPrice.query.get(price_id)
            if not price:
                return False, "Price not found"
            
            # Don't allow users to verify their own submissions
            if price.submitted_by == user_id:
                return False, "You cannot verify your own price submission"
            
            # Create verification
            verification = PriceVerification(
                price_id=price_id,
                verified_by=user_id,
                is_accurate=is_accurate,
                comment=comment[:200] if comment else None,  # Limit comment length
                verified_at=datetime.utcnow()
            )
            
            db.session.add(verification)
            
            # Update price verification count
            if is_accurate:
                price.verification_count += 1
                
                # Mark as verified if enough positive verifications
                if price.verification_count >= 3 and not price.is_verified:
                    price.is_verified = True
            
            db.session.commit()
            
            return True, "Price verification recorded successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error verifying price: {e}")
            return False, "An error occurred while verifying the price"
    
    def get_best_price_for_item(self, item_name: str, user_postcode: str = None) -> Optional[Dict]:
        """
        Get the best (lowest verified) price for an item
        """
        prices = self.get_prices_for_item(item_name, user_postcode)
        
        if not prices:
            return None
        
        # Filter verified prices first, fall back to unverified if none
        verified_prices = [p for p in prices if p['is_verified']]
        if verified_prices:
            best_price = min(verified_prices, key=lambda x: x['price'])
        else:
            # Use most verified prices if no fully verified ones
            best_price = max(prices, key=lambda x: x['verification_count'])
        
        return best_price
    
    def get_recent_submissions(self, days: int = 7) -> List[Dict]:
        """Get recent price submissions for admin monitoring"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        prices = UserContributedPrice.query.filter(
            UserContributedPrice.submitted_at >= cutoff_date
        ).order_by(UserContributedPrice.submitted_at.desc()).limit(100).all()
        
        results = []
        for price in prices:
            results.append({
                'id': price.id,
                'item_name': price.item_name,
                'shop_name': price.shop_name,
                'price': float(price.price),
                'shop_location': price.shop_location,
                'submitted_at': price.submitted_at.isoformat(),
                'submitted_by': price.submitted_by,
                'is_verified': price.is_verified,
                'verification_count': price.verification_count,
                'is_flagged': price.is_flagged
            })
        
        return results

# Create global instance
user_price_service = UserPriceService()
